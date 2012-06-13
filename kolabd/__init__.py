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

"""
    The Kolab daemon.
"""

import grp
import os
import pwd
import shutil
import sys
import time
import traceback

import pykolab

from pykolab.auth import Auth
from pykolab import constants
from pykolab import utils
from pykolab.translate import _

from process import KolabdProcess as Process

log = pykolab.getLogger('pykolab.daemon')
conf = pykolab.getConf()

class KolabDaemon(object):
    def __init__(self):
        """
            The main Kolab Groupware daemon process.
        """

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
                default = "/var/run/kolabd/kolabd.pid",
                help    = _("Path to the PID file to use.")
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

    def run(self):
        """Run Forest, RUN!"""

        exitcode = 0

        utils.ensure_directory(
                os.path.dirname(conf.pidfile),
                conf.process_username,
                conf.process_groupname
            )

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
                pid = os.fork()

            if pid == 0:
                log.remove_stdout_handler()
                self.write_pid()
                self.set_signal_handlers()
                self.do_sync()
            elif not conf.fork_mode:
                self.do_sync()

        except SystemExit, errcode:
            exitcode = errcode

        except KeyboardInterrupt:
            exitcode = 1
            log.info(_("Interrupted by user"))

        except AttributeError, errmsg:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a " + \
                "bug at http://bugzilla.kolabsys.com")

        except TypeError, errmsg:
            exitcode = 1
            traceback.print_exc()
            log.error(_("Type Error: %s") % errmsg)

        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a " + \
                "bug at http://bugzilla.kolabsys.com")

        sys.exit(exitcode)

    def do_sync(self):
        domain_auth = {}

        pid = os.getpid()

        primary_domain = conf.get('kolab', 'primary_domain')

        while 1:
            primary_auth = Auth(primary_domain)

            log.debug(_("Listing domains..."), level=5)

            start = time.time()

            try:
                domains = primary_auth.list_domains()
            except:
                time.sleep(60)
                continue

            # domains now is a list of tuples, we want the primary_domains
            primary_domains = []
            for primary_domain, secondary_domains in domains:
                primary_domains.append(primary_domain)

            # Now we can check if any changes happened.
            added_domains = []
            removed_domains = []

            all_domains = set(primary_domains + domain_auth.keys())

            for domain in all_domains:
                if domain in domain_auth.keys() and domain in primary_domains:
                    continue
                elif domain in domain_auth.keys():
                    removed_domains.append(domain)
                else:
                    added_domains.append(domain)

            if len(removed_domains) == 0 and len(added_domains) == 0:
                time.sleep(600)

            log.debug(
                    _("added domains: %r, removed domains: %r") % (
                            added_domains,
                            removed_domains
                        ),
                    level=8
                )

            for domain in added_domains:
                domain_auth[domain] = Process(domain)
                domain_auth[domain].start()

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
