# -*- coding: utf-8 -*-
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 or, at your option, any later version
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

import asyncore
import grp
import os
import pwd
from smtpd import SMTPChannel
import sys
import tempfile
import threading
import time
import traceback

import pykolab
from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

class WallaceDaemon(object):
    def __init__(self):
        daemon_group = conf.add_cli_parser_option_group(_("Daemon Options"))

        daemon_group.add_option(
                "--fork",
                dest    = "fork_mode",
                action  = "store_true",
                default = False,
                help    = _("Fork to the background.")
            )

        daemon_group.add_option(
                "-b", "--bind",
                dest    = "wallace_bind_address",
                action  = "store",
                default = "localhost",
                help    = _("Bind address for Wallace.")
            )

        daemon_group.add_option(
                "-g",
                "--group",
                dest    = "process_groupname",
                action  = "store",
                default = "kolab",
                help    = _("Run as group GROUPNAME"),
                metavar = "GROUPNAME"
            )

        daemon_group.add_option(
                "-p", "--pid-file",
                dest    = "pidfile",
                action  = "store",
                default = "/var/run/wallaced/wallaced.pid",
                help    = _("Path to the PID file to use.")
            )

        daemon_group.add_option(
                "--port",
                dest    = "wallace_port",
                action  = "store",
                default = 10026,
                help    = _("Port that Wallace is supposed to use.")
            )

        daemon_group.add_option(
                "-u",
                "--user",
                dest    = "process_username",
                action  = "store",
                default = "kolab",
                help    = _("Run as user USERNAME"),
                metavar = "USERNAME"
            )

        conf.finalize_conf()

        import modules
        modules.__init__()

    def process_message(self, peer, mailfrom, rcpttos, data):
        """
            We have retrieved the message.

            - Dispatch to virus-scanning and anti-spam filtering?
                Not for now. We use some sort of re-injection.

            - Apply access policies;
                - Maximum number of recipients,
                - kolabAllowSMTPSender,
                - kolabAllowSMTPRecipient,
                - Rule-based matching against white- and/or blacklist
                - ...

            - Accounting

            - Data Loss Prevention
        """
        inheaders = 1

        (fp, filename) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/")
        os.write(fp, data)
        os.close(fp)

        while threading.active_count() > 25:
            log.debug(
                    _("Number of threads currently running: %d") % (
                            threading.active_count()
                        ),
                    level=8
                )

            time.sleep(1)

        log.debug(
                _("Continuing with %d threads currently running") % (
                        threading.active_count()
                    ),
                level=8
            )

        # TODO: Apply throttling
        log.debug(_("Creating thread for message in %s") % (filename), level=8)

        thread = threading.Thread(target=self.thread_run, args=[ filename ])
        thread.start()

    def thread_run(self, filename, *args, **kw):
        while threading.active_count() > 25:
            log.debug(
                    _("Number of threads currently running: %d") % (
                            threading.active_count()
                        ),
                    level=8
                )

            time.sleep(10)

        log.debug(
                _("Continuing with %d threads currently running") % (
                        threading.active_count()
                    ),
                level=8
            )

        log.debug(
                _("Running thread %s for message file %s") % (
                        threading.current_thread().name,
                        filename
                    ),
                level=8
            )

        if kw.has_key('module'):
            log.debug(
                    _("This message was already in module %s, delegating " + \
                        "specifically to that module") % (
                            kw['module']
                        ),
                    level=8
                )

            if kw.has_key('stage'):
                log.debug(
                        _("It was also in a certain stage: %s, letting " + \
                            "module %s know that") % (
                                kw['stage'],
                                kw['module']
                            ),
                        level=8
                    )

                log.debug(_("Executing module %s") % (kw['module']), level=8)

                modules.execute(kw['module'], filename, stage=kw['stage'])

                return

            log.debug(_("Executing module %s") % (kw['module']), level=8)
            modules.execute(kw['module'], filename, stage=kw['stage'])

            return

        wallace_modules = conf.get_list('wallace', 'modules')
        if wallace_modules == None:
            wallace_modules = ['resources']
        elif not 'resources' in wallace_modules:
            wallace_modules.append('resources')

        for module in wallace_modules:
            log.debug(_("Executing module %s") % (module), level=8)
            modules.execute(module, filename)

    def run(self):
        """
            Run the SASL authentication daemon.
        """

        exitcode = 0

        try:
            (ruid, euid, suid) = os.getresuid()
            (rgid, egid, sgid) = os.getresgid()

            if ruid == 0:
                # Means we can setreuid() / setregid() / setgroups()
                if egid == 0:
                    # Get group entry details
                    try:
                        (
                                group_name,
                                group_password,
                                group_gid,
                                group_members
                            ) = grp.getgrnam(conf.process_groupname)

                    except KeyError:
                        print >> sys.stderr, _("Group %s does not exist") % (
                                conf.process_groupname
                            )

                        sys.exit(1)

                    # Set real and effective group if not the same as current.
                    if not group_gid == egid:
                        log.debug(
                                _("Switching real and effective group id to %d") % (
                                        group_gid
                                    ),
                                level=8
                            )

                        os.setregid(group_gid, group_gid)

                if euid == 0:
                    # Means we haven't switched yet.
                    try:
                        (
                                user_name,
                                user_password,
                                user_uid,
                                user_gid,
                                user_gecos,
                                user_homedir,
                                user_shell
                            ) = pwd.getpwnam(conf.process_username)

                    except KeyError:
                        print >> sys.stderr, _("User %s does not exist") % (
                                conf.process_username
                            )

                        sys.exit(1)


                    # Set real and effective user if not the same as current.
                    if not user_uid == euid:
                        log.debug(
                                _("Switching real and effective user id to %d") % (
                                        user_uid
                                    ),
                                level=8
                            )

                        os.setreuid(user_uid, user_uid)

        except:
            log.error(_("Could not change real and effective uid and/or gid"))

        try:
            pid = 1
            if conf.fork_mode:
                self.thread_count += 1
                self.write_pid()
                self.set_signal_handlers()
                pid = os.fork()

            if pid == 0:
                log.remove_stdout_handler()

            self.do_wallace()

        except SystemExit, e:
            exitcode = e
        except KeyboardInterrupt:
            exitcode = 1
            log.info(_("Interrupted by user"))
        except AttributeError, e:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a " + \
                "bug at http://bugzilla.kolabsys.com")

        except TypeError, e:
            exitcode = 1
            traceback.print_exc()
            log.error(_("Type Error: %s") % e)
        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a " + \
                "bug at http://bugzilla.kolabsys.com")

        sys.exit(exitcode)

    def pickup_defer(self):
        wallace_modules = conf.get_list('wallace', 'modules')

        if wallace_modules == None:
            wallace_modules = []

        base_path = '/var/spool/pykolab/wallace/'

        while 1:
            file_count = 0

            log.debug(_("Picking up deferred messages for wallace"), level=8)

            defer_path = os.path.join(base_path, 'DEFER')

            if os.path.isdir(defer_path):
                for root, directory, files in os.walk(defer_path):
                    for filename in files:
                        filepath = os.path.join(root, filename)

                        file_count += 1

                        for module in wallace_modules:
                            modules.execute(module, filepath)

                        time.sleep(1)

            time.sleep(1)

            for module in wallace_modules:
                log.debug(
                        _("Picking up deferred messages for module %s") % (
                                module
                            ),
                        level=8
                    )

                module_defer_path = os.path.join(base_path, module, 'DEFER')

                if os.path.isdir(module_defer_path):
                    for root, directory, files in os.walk(module_defer_path):
                        for filename in files:
                            filepath = os.path.join(root, filename)

                            file_count += 1

                            modules.execute(module, filepath)

                            time.sleep(1)

                time.sleep(1)

            # Sleep for 300 seconds before reprocessing the deferred queues.
            # TODO: Consider using queue_run_delay from Postfix, which is where
            # the default value of 300 seconds comes from.
            log.debug(_("Sleeping for 300 seconds"), level=8)
            time.sleep(300)

    def do_wallace(self):
        import binascii
        import socket
        import struct

        #s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ## TODO: The wallace socket path could be a setting.
        #try:
            #os.remove('/var/run/kolab/wallace')
        #except:
            ## TODO: Do the "could not remove, could not start dance"
            #pass

        bound = False
        while not bound:
            try:
                s.bind((conf.wallace_bind_address, conf.wallace_port))
                bound = True
            except Exception, e:
                log.warning(
                        _("Could not bind to socket on port %d on bind " + \
                            "address %s") % (
                                conf.wallace_port,
                                conf.wallace_bind_address
                            )
                    )

                try:
                    s.shutdown(1)
                except Exception, e:
                    log.warning(_("Could not shut down socket"))

                s.close()

                time.sleep(1)

        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #os.chmod('/var/run/kolab/wallace', 0777)
        #os.chgrp('/var/run/wallace/mux', 'kolab')
        #os.chown('/var/run/wallace/mux', 'kolab')

        s.listen(5)

        # Mind you to include the trailing slash
        pickup_path = '/var/spool/pykolab/wallace/'
        for root, directory, files in os.walk(pickup_path):
            for filename in files:
                filepath = os.path.join(root, filename)

                if not root == pickup_path:
                    module = os.path.dirname(root).replace(pickup_path, '')

                    # Compare uppercase status (specifically, DEFER) with
                    # lowercase (plugin names).
                    #
                    # The messages in DEFER are supposed to be picked up by
                    # another thread, whereas the messages in other directories
                    # are pending being handled by their respective plugins.
                    #
                    # TODO: Handle messages in spool directories for which a
                    # plugin had been enabled, but is not enabled any longer.
                    #

                    if module.lower() == "defer":
                        # Wallace was unable to deliver to re-injection smtpd.
                        # Skip it, another thread is picking up the deferred
                        # messages.
                        continue

                    stage = root.replace(pickup_path, '').split('/')
                    if len(stage) < 2:
                        stage = None
                    else:
                        stage = stage[1]

                    if stage.lower() == "hold":
                        continue

                    # Do not handle messages in a defer state.
                    if stage.lower() == "defer":
                        continue

                    log.debug(
                            _("Number of threads currently running: %d") % (
                                    threading.active_count()
                                ),
                            level=8
                        )

                    thread = threading.Thread(
                            target = self.thread_run,
                            args = [ filepath ],
                            kwargs = {
                                    "module": '%s' % (module),
                                    "stage": '%s' % (stage)
                                }
                        )

                    thread.start()
                    time.sleep(0.5)

                    continue

                log.debug(
                        _("Picking up spooled email file %s") % (
                                filepath
                            ),
                        level=8
                    )

                log.debug(
                        _("Number of threads currently running: %d") % (
                                threading.active_count()
                            ),
                        level=8
                    )

                thread = threading.Thread(
                        target=self.thread_run,
                        args=[ filepath ]
                    )

                thread.start()
                time.sleep(0.5)

        pid = os.fork()

        if pid == 0:
            self.pickup_defer()
        else:

            try:
                while 1:
                    pair = s.accept()
                    log.info(_("Accepted connection"))
                    if not pair == None:
                        connection, address = pair
                        #print "Accepted connection from %r" % (address)
                        channel = SMTPChannel(self, connection, address)
                        asyncore.loop()
            except Exception, errmsg:
                traceback.print_exc()
                s.shutdown(1)
                s.close()

    def reload_config(self, *args, **kw):
        pass

    def remove_pid(self, *args, **kw):
        if os.access(conf.pidfile, os.R_OK):
            os.remove(conf.pidfile)
        raise SystemExit

    def set_signal_handlers(self):
        import signal
        signal.signal(signal.SIGHUP, self.reload_config)
        signal.signal(signal.SIGTERM, self.remove_pid)

    def write_pid(self):
        pid = os.getpid()
        fp = open(conf.pidfile,'w')
        fp.write("%d\n" % (pid))
        fp.close()
