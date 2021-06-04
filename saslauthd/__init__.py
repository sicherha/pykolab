# Copyright 2010-2016 Kolab Systems AG (http://www.kolabsys.com)
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

"""
    SASL authentication daemon for multi-domain Kolab deployments.

    The SASL authentication daemon can use the domain name space or realm
    in the login credentials to determine the backend authentication
    database, and authenticate the credentials supplied against that
    backend.
"""

from __future__ import print_function
from optparse import OptionParser
from ConfigParser import SafeConfigParser

import grp
import os
import pwd
import shutil
import sys
import time
import traceback

import pykolab

from pykolab import utils
from pykolab.auth import Auth
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('saslauthd')
conf = pykolab.getConf()


class SASLAuthDaemon(object):
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
                "-p",
                "--pid-file",
                dest    = "pidfile",
                action  = "store",
                default = "/var/run/kolab-saslauthd/kolab-saslauthd.pid",
                help    = _("Path to the PID file to use.")
            )

        daemon_group.add_option(
                "-s",
                "--socket",
                dest    = "socketfile",
                action  = "store",
                default = "/var/run/saslauthd/mux",
                help    = _("Socket file to bind to.")
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

        daemon_group.add_option(
                "-g",
                "--group",
                dest    = "process_groupname",
                action  = "store",
                default = "kolab",
                help    = _("Run as group GROUPNAME"),
                metavar = "GROUPNAME"
            )

        conf.finalize_conf()

        try:
            utils.ensure_directory(
                    os.path.dirname(conf.pidfile),
                    conf.process_username,
                    conf.process_groupname
                )
        except Exception as errmsg:
            log.error(_("Could not create %r: %r") % (os.path.dirname(conf.pidfile), errmsg))
            sys.exit(1)

        self.thread_count = 0

    def run(self):
        """
            Run the SASL authentication daemon.
        """

        exitcode = 0

        self._ensure_socket_dir()

        self._drop_privileges()

        try:
            pid = os.getpid()

            if conf.fork_mode:
                pid = os.fork()

            if pid > 0 and not conf.fork_mode:
                self.do_saslauthd()

            elif pid > 0:
                sys.exit(0)

            else:
                # Give up the session, all control,
                # all open file descriptors, see #5151
                os.chdir("/")
                old_umask = os.umask(0)
                os.setsid()

                pid = os.fork()

                if pid > 0:
                    sys.exit(0)

                sys.stderr.flush()
                sys.stdout.flush()

                os.close(0)
                os.close(1)
                os.close(2)

                os.umask(old_umask)

                self.thread_count += 1
                log.remove_stdout_handler()
                self.set_signal_handlers()
                self.write_pid()
                self.do_saslauthd()

        except SystemExit as e:
            exitcode = e
        except KeyboardInterrupt:
            exitcode = 1
            log.info(_("Interrupted by user"))
        except AttributeError:
            exitcode = 1
            traceback.print_exc()
            print(_("Traceback occurred, please report a " +
                                   "bug at https://issues.kolab.org"),
                  file=sys.stderr)
        except TypeError as e:
            exitcode = 1
            traceback.print_exc()
            log.error(_("Type Error: %s") % e)
        except:
            exitcode = 2
            traceback.print_exc()
            print(_("Traceback occurred, please report a " +
                                   "bug at https://issues.kolab.org"),
                  file=sys.stderr)

        sys.exit(exitcode)

    def do_saslauthd(self):
        """
            Create the actual listener socket, and handle the authentication.

            The actual authentication handling is passed on to the appropriate
            backend authentication classes through the more generic Auth().
        """
        import binascii
        import socket
        import struct

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # TODO: The saslauthd socket path could be a setting.
        try:
            os.remove(conf.socketfile)
        except:
            # TODO: Do the "could not remove, could not start" dance
            pass

        s.bind(conf.socketfile)
        os.chmod(conf.socketfile, 0o777)

        s.listen(5)

        while 1:
            max_tries = 20
            cur_tries = 0
            bound = False
            while not bound:
                cur_tries += 1
                try:
                    (clientsocket, address) = s.accept()
                    bound = True
                except Exception as errmsg:
                    log.error(
                            _("kolab-saslauthd could not accept " +
                              "connections on socket: %r") % (errmsg)
                        )

                    if cur_tries >= max_tries:
                        log.fatal(_("Maximum tries exceeded, exiting"))
                        sys.exit(1)

                    time.sleep(1)

            received = clientsocket.recv(4096)

            login = []

            start = 0
            end = 2

            while end < len(received):
                (length,) = struct.unpack("!H", received[start:end])
                start += 2
                end += length
                (value,) = struct.unpack("!%ds" % (length), received[start:end])
                start += length
                end = start + 2
                login.append(value)

            if len(login) == 4:
                realm = login[3]
            elif len(login[0].split('@')) > 1:
                realm = login[0].split('@')[1]
            else:
                realm = conf.get('kolab', 'primary_domain')

            auth = Auth(domain=realm)
            auth.connect()

            success = False

            try:
                success = auth.authenticate(login)
            except:
                success = False

            if success:
                # #1170: Catch broken pipe error (incomplete authentication request)
                try:
                    clientsocket.send(struct.pack("!H2s", 2, "OK"))
                except:
                    pass
            else:
                # #1170: Catch broken pipe error (incomplete authentication request)
                try:
                    clientsocket.send(struct.pack("!H2s", 2, "NO"))
                except:
                    pass

            clientsocket.close()
            auth.disconnect()

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
        fp = open(conf.pidfile, 'w')
        fp.write("%d\n" % (pid))
        fp.close()

    def _ensure_socket_dir(self):
        utils.ensure_directory(
                os.path.dirname(conf.socketfile),
                conf.process_username,
                conf.process_groupname
            )

    def _drop_privileges(self):
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
                        print(_("Group %s does not exist") % (
                                conf.process_groupname
                            ), file=sys.stderr)

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
                        print(_("User %s does not exist") % (
                                conf.process_username
                            ), file=sys.stderr)

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
