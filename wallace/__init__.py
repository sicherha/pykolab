# -*- coding: utf-8 -*-
# Copyright 2010-2019 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function

import asyncore
from distutils import version
import grp
import multiprocessing
import os
import pwd
import traceback
import smtpd
import socket
import struct
import sys
import tempfile
from threading import _Timer
import time

import pykolab
from pykolab import utils
from pykolab.translate import _

from modules import cb_action_ACCEPT

# pylint: disable=invalid-name
log = pykolab.getLogger('pykolab.wallace')
sys.stderr = pykolab.logger.StderrToLogger(log)
conf = pykolab.getConf()


def pickup_message(filepath, *args, **kwargs):
    wallace_modules = args[0]

    if 'module' in kwargs:

        # Cause the previous modules to be skipped
        wallace_modules = wallace_modules[(wallace_modules.index(kwargs['module']) + 1):]

        log.debug(_("Wallace modules: %r") % (wallace_modules), level=8)

        # Execute the module
        if 'stage' in kwargs:
            modules.execute(kwargs['module'], filepath, stage=kwargs['stage'])
        else:
            modules.execute(kwargs['module'], filepath)

    # After all modules are executed, continue with a call to
    # accept the message and re-inject in to Postfix.
    continue_with_accept = True

    for module in wallace_modules:
        try:
            result_filepath = modules.execute(module, filepath)
        except Exception:
            log.error(
                "Module %s.execute() failed on message %r with error: %s" % (
                    module,
                    filepath,
                    traceback.format_exc()
                )
            )

            result_filepath = False

        if result_filepath is not None and result_filepath is not False:
            filepath = result_filepath
        else:
            # A module has returned False or None
            continue_with_accept = False
            # The message very likely has been consumed by the module that returned False
            if not os.path.isfile(filepath):
                break

    if continue_with_accept:
        cb_action_ACCEPT('wallace', filepath)


def modules_heartbeat(wallace_modules):
    lastrun = 0

    while not multiprocessing.current_process().finished.is_set():
        try:
            for module in wallace_modules:
                try:
                    modules.heartbeat(module, lastrun)
                except Exception:
                    log.error(
                        "Module %s.heartbeat() failed with error: %s" % (
                            module,
                            traceback.format_exc()
                        )
                    )

            lastrun = int(time.time())
            multiprocessing.current_process().finished.wait(60)

        except (SystemExit, KeyboardInterrupt) as errmsg:
            log.warning("Exiting %s, %s" % (multiprocessing.current_process().name, errmsg))
            break


def worker_process(*args, **kwargs):
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    log.debug("Worker process %s initializing" % (multiprocessing.current_process().name), level=1)


# pylint: disable=too-few-public-methods
class Timer(_Timer):
    def run(self):
        while True:
            while not self.finished.is_set():
                self.finished.wait(self.interval)
                log.debug(_("Timer looping function '%s' every %ss") % (
                    self.function.__name__,
                    self.interval
                ), level=8)
                self.function(*self.args, **self.kwargs)

            self.finished.set()
            log.debug(_("Timer loop %s") % ('still active','finished')[self.finished.is_set()], level=8)
            break

class WallaceDaemon:
    def __init__(self):
        self.current_connections = 0
        self.max_connections = 24
        self.parent_pid = None
        self.pool = None

        daemon_group = conf.add_cli_parser_option_group(_("Daemon Options"))

        daemon_group.add_option(
            "--fork",
            dest="fork_mode",
            action="store_true",
            default=False,
            help=_("Fork to the background.")
        )

        daemon_group.add_option(
            "-b", "--bind",
            dest="wallace_bind_address",
            action="store",
            default="localhost",
            help=_("Bind address for Wallace.")
        )

        daemon_group.add_option(
            "-g", "--group",
            dest="process_groupname",
            action="store",
            default="kolab",
            help=_("Run as group GROUPNAME"),
            metavar="GROUPNAME"
        )

        daemon_group.add_option(
            "--threads",
            dest="max_threads",
            action="store",
            default=4,
            type=int,
            help=_("Number of threads to use.")
        )

        daemon_group.add_option(
            "--max-tasks",
            dest    = "max_tasks",
            action  = "store",
            default = None,
            type    = int,
            help    = _("Number of tasks per process.")
        )

        daemon_group.add_option(
            "-p", "--pid-file",
            dest="pidfile",
            action="store",
            default="/var/run/wallaced/wallaced.pid",
            help=_("Path to the PID file to use.")
        )

        daemon_group.add_option(
            "--port",
            dest="wallace_port",
            action="store",
            default=10026,
            type=int,
            help=_("Port that Wallace is supposed to use.")
        )

        daemon_group.add_option(
            "-u", "--user",
            dest="process_username",
            action="store",
            default="kolab",
            help=_("Run as user USERNAME"),
            metavar="USERNAME"
        )

        conf.finalize_conf()

        utils.ensure_directory(
            os.path.dirname(conf.pidfile),
            conf.process_username,
            conf.process_groupname
        )

        if conf.debuglevel >= 9:
            mp_logger = multiprocessing.get_logger()
            mp_logger.setLevel(multiprocessing.SUBDEBUG)
            mp_logger.debug('Python multi-processing logger started')

        import modules
        modules.__init__()

        self.modules = conf.get_list('wallace', 'modules')
        if not self.modules:
            self.modules = []

    def do_wallace(self):
        self.parent_pid = os.getpid()

        if version.StrictVersion(sys.version[:3]) >= version.StrictVersion("2.7"):
            self.pool = multiprocessing.Pool(conf.max_threads, worker_process, (), conf.max_tasks)
        else:
            self.pool = multiprocessing.Pool(conf.max_threads, worker_process, ())

        self.pickup_spool_messages(sync=True)

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

            # pylint: disable=broad-except
            except Exception:
                log.warning(
                    _("Could not bind to socket on port %d on bind address %s") % (
                        conf.wallace_port,
                        conf.wallace_bind_address
                    )
                )

                while not shutdown:
                    try:
                        s.shutdown(socket.SHUT_RDWR)
                        shutdown = True

                    # pylint: disable=broad-except
                    except Exception:
                        log.warning(_("Could not shut down socket"))
                        time.sleep(1)

                s.close()

                time.sleep(1)

        s.listen(5)

        self.timer = Timer(180, self.pickup_spool_messages, args=[], kwargs={'sync': True})
        self.timer.daemon = True
        self.timer.start()

        # start background process to run periodic jobs in active modules
        try:
            self.heartbeat = multiprocessing.Process(
                target=modules_heartbeat,
                name='Wallace_Heartbeat',
                args=[self.modules]
            )

            self.heartbeat.finished = multiprocessing.Event()
            self.heartbeat.daemon = True
            self.heartbeat.start()
        except Exception as errmsg:
            log.error("Failed to start heartbeat daemon: %s" % (errmsg))
        finally:
            log.debug(
                "Wallace heartbeat is %s" % ('not alive', 'alive')[self.heartbeat.is_alive()],
                level=8
            )

        try:
            while 1:
                while self.current_connections >= self.max_connections:
                    log.debug(_("Reached limit of max connections of: %s. Sleeping for 0.5s") % self.max_connections, level=6)
                    time.sleep(0.5)

                pair = s.accept()
                log.debug(_("Accepted connection %r with address %r") % (pair if pair is not None else (None, None)), level=8)
                if pair is not None:
                    self.current_connections += 1
                    connection, address = pair

                    _smtpd = smtpd
                    # Set DEBUGSTREAM of smtpd to log to pykolab logger
                    if conf.debuglevel > 8:
                        _smtpd.DEBUGSTREAM = pykolab.logger.StderrToLogger(log)

                    log.debug(_("Creating SMTPChannel for accepted message"), level=8)
                    channel = _smtpd.SMTPChannel(self, connection, address)
                    asyncore.loop()
                else:
                    log.error(_("Socket accepted, but (conn, address) tuple is None."))

        # pylint: disable=broad-except
        except Exception:
            traceback.print_exc()
            s.shutdown(1)
            s.close()

        # shut down hearbeat process
        self.heartbeat.terminate()
        self.timer.cancel()
        self.timer.join()

    def data_header(self, mailfrom, rcpttos):
        COMMASPACE = ', '

        return "X-Kolab-From: " + mailfrom + "\r\n" + \
            "X-Kolab-To: " + COMMASPACE.join(rcpttos) + "\r\n"

    def pickup_spool_messages(self, sync=False):
        # Mind you to include the trailing slash
        pickup_path = '/var/spool/pykolab/wallace/'

        messages = []
        for root, directory, files in os.walk(pickup_path):
            for filename in files:
                messages.append((root, filename))

        for root, filename in messages:
            filepath = os.path.join(root, filename)

            try:
                # ignore calls on too young files
                if os.stat(filepath).st_mtime + 150 > time.time():
                    log.debug("File not more than 150s old. Skipping %s" % (filepath), level=8)
                    continue

                # ignore calls on lock files
                if '/locks/' in filepath:
                    log.debug("File is in locks directory. Skipping %s" % (filepath), level=8)
                    continue

            # pylint: disable=broad-except
            except Exception as errmsg:
                log.error("Error: %s. Skipping %s" % (errmsg, filepath))
                continue

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

                self.current_connections += 1

                if sync:
                    pickup_message(filepath, self.modules, module=module, stage=stage)
                else:
                    self.pool.apply_async(
                        pickup_message,
                        (
                            filepath,
                            (self.modules),
                            {'module': module, 'stage': stage}
                        )
                    )

                self.current_connections -= 1

                continue

            self.current_connections += 1

            if sync:
                pickup_message(filepath, self.modules)
            else:
                self.pool.apply_async(pickup_message, (filepath, (self.modules)))

            self.current_connections -= 1

    def process_message(self, peer, mailfrom, rcpttos, data):
        """
            We have retrieved the message. This should be as fast as possible,
            and not ever block.
        """

        header = self.data_header(mailfrom, rcpttos)

        (fp, filename) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/")

        # @TODO: and add line separator (\n or \r\n?)
        # we should make sure there's only one line separator between
        # kolab headers and the original message (data)
        os.write(fp, header)
        os.write(fp, data)
        os.close(fp)

        log.debug(_("Started processing accepted message %s") % filename, level=8)
        self.pool.apply_async(pickup_message, (filename, (self.modules)))

        self.current_connections -= 1

        return "250 OK Message %s queued" % (filename)

    def reload_config(self, *args, **kwargs):
        pass

    def remove_pid(self, *args, **kwargs):
        try:
            if os.getpid() == self.parent_pid:
                log.debug("Stopping process %s" % multiprocessing.current_process().name, level=8)

                log.debug(_("Terminating processes pool"), level=8)
                self.pool.close()

                if hasattr(self, 'timer'):
                    if not self.timer.finished.is_set():
                        log.debug("Canceling Wallace Timer", level=8)
                        self.timer.finished.set()
                        self.timer.cancel()

                log.debug(_("Terminating heartbeat process"), level=8)
                self.heartbeat.finished.set()
                self.heartbeat.terminate()

                self.pool.close()
                self.pool.join(5)
                self.timer.join(5)
                self.heartbeat.join(5)

                if os.access(conf.pidfile, os.R_OK):
                    log.warning(_("Removing PID file %s") % conf.pidfile)
                    os.remove(conf.pidfile)

                log.warning("Exiting!")
                sys.exit()

            else:
                sys.exit(0)

        except Exception as errmsg:
            log.debug(
                "Exception while trying to stop %s: %s" % (
                    multiprocessing.current_process().name, errmsg
                ),
                level=8
            )

            sys.exit(1)

        sys.exit(0)

    # pylint: disable=too-many-locals
    def run(self):  # noqa: C901
        """
            Run the Wallace daemon.
        """

        exitcode = 0

        try:
            try:
                (ruid, euid, suid) = os.getresuid()
                (rgid, egid, sgid) = os.getresgid()
            except AttributeError:
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
                        print(_("Group %s does not exist") % (conf.process_groupname))

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
                        print(_("User %s does not exist") % (conf.process_username))

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

        # pylint: disable=broad-except
        except Exception:
            log.error(_("Could not change real and effective uid and/or gid"))

        try:
            pid = os.getpid()

            if conf.fork_mode:
                pid = os.fork()

            if pid > 0 and not conf.fork_mode:
                self.do_wallace()

            elif pid > 0:
                sys.exit(0)

            else:
                # Give up the session, all control,
                # all open file descriptors, see #5151
                os.chdir("/")
                os.umask(0)
                os.setsid()

                pid = os.fork()

                if pid > 0:
                    sys.exit(0)

                sys.stderr.flush()
                sys.stdout.flush()

                os.close(0)
                os.close(1)
                os.close(2)

                os.open(os.devnull, os.O_RDONLY)
                os.open(os.devnull, os.O_WRONLY)
                os.open(os.devnull, os.O_WRONLY)

                log.remove_stdout_handler()
                self.set_signal_handlers()
                self.write_pid()
                self.do_wallace()

        except SystemExit as errmsg:
            exitcode = errmsg
        except KeyboardInterrupt:
            exitcode = 1
            log.info(_("Interrupted by user"))
        except AttributeError:
            exitcode = 1
            traceback.print_exc()
            print(_("Traceback occurred, please report a bug."))

        except TypeError as errmsg:
            exitcode = 1
            traceback.print_exc()
            log.error(_("Type Error: %s") % errmsg)
        except:
            exitcode = 2
            traceback.print_exc()
            print(_("Traceback occurred, please report a bug."))

        sys.exit(exitcode)

    def set_signal_handlers(self):
        import signal
        signal.signal(signal.SIGHUP, self.reload_config)
        signal.signal(signal.SIGTERM, self.remove_pid)

    def write_pid(self):
        pid = os.getpid()
        if os.access(os.path.dirname(conf.pidfile), os.W_OK):
            fp = open(conf.pidfile,'w')
            fp.write("%d\n" % (pid))
            fp.close()
        else:
            print(_("Could not write pid file %s") % (conf.pidfile))
