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
import binascii
import grp
import multiprocessing
import os
import pwd
from smtpd import SMTPChannel
import socket
import struct
import sys
import tempfile
import time
import traceback

import pykolab
from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

max_threads = 24

def pickup_message(filepath, *args, **kw):
    wallace_modules = args[0]
    if kw.has_key('module'):

        # Cause the previous modules to be skipped
        wallace_modules = wallace_modules[(wallace_modules.index(kw['module'])+1):]

        # Execute the module
        if kw.has_key('stage'):
            modules.execute(kw['module'], filepath, stage=kw['stage'])
        else:
            modules.execute(kw['module'], filepath)

    for module in wallace_modules:
        modules.execute(module, filepath)

def worker_process(*args, **kw):
    log.debug(_("Worker process %s initializing") % (multiprocessing.current_process().name), level=1)

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

        self.modules = conf.get_list('wallace', 'modules')
        if self.modules == None:
            self.modules = ['resources']
        elif not 'resources' in self.modules:
            self.modules.append('resources')

    def do_wallace(self):
        self.pool = multiprocessing.Pool(max_threads, worker_process, (), 1)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        bound = False
        shutdown = False
        while not bound:
            try:
                if shutdown:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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

                while not shutdown:
                    try:
                        s.shutdown(socket.SHUT_RDWR)
                        shutdown = True
                    except Exception, e:
                        log.warning(_("Could not shut down socket"))
                        time.sleep(1)

                s.close()

                time.sleep(1)

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

                    self.pool.apply_async(pickup_message, (filepath, (self.modules), {'module': module, 'stage': stage}))

                    continue

                self.pool.apply_async(pickup_message, (filepath, (self.modules)))

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

    def process_message(self, peer, mailfrom, rcpttos, data):
        """
            We have retrieved the message. This should be as fast as possible,
            and not ever block.
        """
        inheaders = 1

        (fp, filename) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/")
        os.write(fp, data)
        os.close(fp)

        self.pool.apply_async(pickup_message, (filename, (self.modules)))

        return

    def reload_config(self, *args, **kw):
        pass

    def remove_pid(self, *args, **kw):
        if os.access(conf.pidfile, os.R_OK):
            os.remove(conf.pidfile)
        raise SystemExit

    def run(self):
        """
            Run the Wallace daemon.
        """

        exitcode = 0

        try:
            try:
                (ruid, euid, suid) = os.getresuid()
                (rgid, egid, sgid) = os.getresgid()
            except AttributeError, errmsg:
                ruid = os.getuid()
                rgid = os.getgid()

            if ruid == 0:
                # Means we can setreuid() / setregid() / setgroups()
                if rgid == 0:
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
                    if not group_gid == rgid:
                        log.debug(
                                _("Switching real and effective group id to %d") % (
                                        group_gid
                                    ),
                                level=8
                            )

                        os.setregid(group_gid, group_gid)

                if ruid == 0:
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
                    if not user_uid == ruid:
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

    def set_signal_handlers(self):
        import signal
        signal.signal(signal.SIGHUP, self.reload_config)
        signal.signal(signal.SIGTERM, self.remove_pid)

    def write_pid(self):
        pid = os.getpid()
        fp = open(conf.pidfile,'w')
        fp.write("%d\n" % (pid))
        fp.close()
