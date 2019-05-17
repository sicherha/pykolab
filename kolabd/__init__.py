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
            pid = os.getpid()

            if conf.fork_mode:
                pid = os.fork()

            if pid > 0 and not conf.fork_mode:
                self.do_sync()

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
                self.do_sync()

        except SystemExit, errcode:
            exitcode = errcode

        except KeyboardInterrupt:
            exitcode = 1
            log.info(_("Interrupted by user"))

        except AttributeError, errmsg:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a " +
                                   "bug at https://issues.kolab.org")

        except TypeError, errmsg:
            exitcode = 1
            traceback.print_exc()
            log.error(_("Type Error: %s") % errmsg)

        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a " +
                                   "bug at https://issues.kolab.org")

        sys.exit(exitcode)

    def do_sync(self):
        domain_auth = {}

        pid = os.getpid()

        primary_domain = conf.get('kolab', 'primary_domain')

        while 1:
            primary_auth = Auth(primary_domain)

            connected = False
            while not connected:
                try:
                    primary_auth.connect()
                    connected = True
                except Exception, errmsg:
                    connected = False
                    log.error(_("Could not connect to LDAP, is it running?"))
                    time.sleep(5)

            log.debug(_("Listing domains..."), level=5)

            start = time.time()

            try:
                domains = primary_auth.list_domains()
            except:
                time.sleep(60)
                continue

            if isinstance(domains, list) and len(domains) < 1:
                log.error(_("No domains. Not syncing"))
                time.sleep(5)
                continue

            # domains now is a list of key-valye pairs in the format of
            # {'secondary': 'primary'}, we want the primaries
            primaries = list(set(domains.values()))

            # Store the naming contexts for the domains as
            #
            #   {'domain': 'naming context'}
            #
            # and the domain root dns as
            #
            #   {'domain': 'domain root dn'}
            #
            domain_root_dns = {}
            naming_contexts = {}

            for primary in primaries:
                naming_context = primary_auth.domain_naming_context(primary)
                domain_root_dn = primary_auth._auth._kolab_domain_root_dn(primary)
                log.debug(
                        _("Domain %r naming context: %r, root dn: %r") % (
                                primary,
                                naming_context,
                                domain_root_dn
                            ),
                        level=8
                    )

                domain_root_dns[primary] = domain_root_dn
                naming_contexts[primary] = naming_context

            log.debug(
                    _("Naming contexts to synchronize: %r") % (
                            list(set(naming_contexts.values()))
                        ),
                    level=8
                )

            # Find however many naming contexts we have, and what the
            # corresponding domain name is for them.
            primary_domains = [x for x,y in naming_contexts.iteritems() if domain_root_dns[x] == y]

            # Now we can check if any changes happened.
            added_domains = []
            removed_domains = []

            # Combine the domains from LDAP with the domain processes
            # accounted for locally.
            all_domains = list(set(primary_domains + domain_auth.keys()))

            log.debug(_("Result set of domains: %r") % (all_domains), level=8)

            for domain in all_domains:
                log.debug(_("Checking for domain %s") % (domain), level=8)

                if domain in domain_auth.keys() and domain in primary_domains:
                    if not domain_auth[domain].is_alive():
                        log.debug(_("Domain %s isn't alive anymore.") % (domain), level=8)
                        domain_auth[domain].terminate()
                        added_domains.append(domain)
                    else:
                        log.debug(_("Domain %s already there and alive.") % (domain), level=8)
                        continue

                elif domain in domain_auth.keys():
                    log.debug(_("Domain %s should not exist any longer.") % (domain), level=8)
                    removed_domains.append(domain)
                else:
                    log.debug(_("Domain %s does not have a process yet.") % (domain), level=8)
                    added_domains.append(domain)

            if len(removed_domains) == 0 and len(added_domains) == 0:
                try:
                    sleep_between_domain_operations_in_seconds = (float)(conf.get('kolab', 'domain_sync_interval'))
                    time.sleep(sleep_between_domain_operations_in_seconds)
                except ValueError:
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

                # Pause or hammer your LDAP server to death
                if len(added_domains) >= 5:
                    time.sleep(10)

            for domain in removed_domains:
                domain_auth[domain].terminate()
                del domain_auth[domain]

    def reload_config(self, *args, **kw):
        pass

    def remove_pid(self, *args, **kw):
        """
            Remove our PID file.

            Note that multiple processes can attempt to do this very same thing
            at the same time, and therefore we need to test if the PID file
            exists, and only try/except removing it.
        """
        if os.access(conf.pidfile, os.R_OK):
            try:
                os.remove(conf.pidfile)
            except:
                pass

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
