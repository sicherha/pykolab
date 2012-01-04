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

    TODO: Write a pid file, check the pid file has a valid pid, and
    consider providing an option to specify the pid file path.
"""

from optparse import OptionParser
from ConfigParser import SafeConfigParser

import os
import shutil
import time
import traceback

import pykolab

from pykolab.auth import Auth
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('kolabd')
conf = pykolab.getConf()

class KolabDaemon(object):
    def __init__(self):
        """
            self.args == Arguments passed on the CLI
            self.cli_options == Parser results (again, CLI)
            self.parser == The actual Parser (from OptionParser)
            self.plugins == Our Kolab Plugins
        """

        daemon_group = conf.add_cli_parser_option_group(_("Daemon Options"))

        daemon_group.add_option(  "--fork",
                                dest    = "fork_mode",
                                action  = "store_true",
                                default = False,
                                help    = _("Fork to the background."))

        daemon_group.add_option( "-p", "--pid-file",
                                dest    = "pidfile",
                                action  = "store",
                                default = "/var/run/kolabd/kolabd.pid",
                                help    = _("Path to the PID file to use."))

        conf.finalize_conf()

        self.thread_count = 0

    def run(self):
        """Run Forest, RUN!"""

        exitcode = 0

        # TODO: Add a nosync option
        try:
            pid = 1
            if conf.fork_mode:
                self.thread_count += 1
                pid = os.fork()

            if pid == 0:
                log.remove_stdout_handler()
                self.write_pid()
                self.set_signal_handlers()
                self.do_sync()
            elif not conf.fork_mode:
                self.do_sync()

        except SystemExit, e:
            exitcode = e
        except KeyboardInterrupt:
            exitcode = 1
            log.info(_("Interrupted by user"))
        except AttributeError, e:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://bugzilla.kolabsys.com")
        except TypeError, e:
            exitcode = 1
            traceback.print_exc()
            log.error(_("Type Error: %s") % e)
        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://bugzilla.kolabsys.com")
        sys.exit(exitcode)

    def do_sync(self):
        domain_auth = {}

        pid = os.getpid()

        while 1:
            primary_auth = Auth()

            log.debug(_("Listing domains..."), level=5)

            start = time.time()
            domains = primary_auth.list_domains()
            if len(domains) == len(domain_auth.keys()):
                time.sleep(600)
            end = time.time()

            log.debug(_("Found %d domains in %d seconds") %(len(domains),(end-start)), level=8)

            for primary_domain,secondary_domains in domains:
                log.debug(_("Running for domain %s") %(primary_domain), level=5)

                if not pid == 0 and not domain_auth.has_key(primary_domain):
                    log.debug(_("Domain %s did not have a key yet") %(primary_domain), level=5)
                    domain_auth[primary_domain] = Auth()
                    pid = os.fork()
                    if pid == 0:
                        domain_auth[primary_domain].connect(primary_domain)
                        start_time = time.time()
                        domain_auth[primary_domain].synchronize(primary_domain, secondary_domains)
                        end_time = time.time()

                        log.info(_("Synchronizing users for %s took %d seconds")
                                %(primary_domain, (end_time-start_time))
                            )
                        domain_auth[primary_domain].synchronize(primary_domain, secondary_domains)

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
        fp.write("%d\n" %(pid))
        fp.close()
