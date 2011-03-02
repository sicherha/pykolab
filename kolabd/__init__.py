# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 only
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

from optparse import OptionParser
from ConfigParser import SafeConfigParser

import os
import shutil
import time
import traceback

from pykolab.auth import Auth
from pykolab.conf import Conf
from pykolab.imap import IMAP
from pykolab.constants import *
from pykolab.translate import _

class KolabDaemon(object):
    def __init__(self):
        """
            self.args == Arguments passed on the CLI
            self.cli_options == Parser results (again, CLI)
            self.parser == The actual Parser (from OptionParser)
            self.plugins == Our Kolab Plugins
        """

        self.conf = Conf()

        daemon_group = self.conf.parser.add_option_group(_("Daemon Options"))

        daemon_group.add_option(  "--fork",
                                dest    = "fork_mode",
                                action  = "store_true",
                                default = False,
                                help    = _("Fork to the background."))

        self.conf.finalize_conf()

        self.log = self.conf.log

        self.thread_count = 0

    def run(self):
        """Run Forest, RUN!"""

        exitcode = 0

        try:
            if self.conf.fork_mode:
                self.thread_count += 1
                pid = os.fork()
            else:
                self.do_sync()

            if pid == 0:
                self.log.remove_stdout_handler()
                self.do_sync()

        except SystemExit, e:
            exitcode = e
        except KeyboardInterrupt:
            exitcode = 1
            self.log.info(_("Interrupted by user"))
        except AttributeError, e:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://issues.kolab.org")
        except TypeError, e:
            exitcode = 1
            traceback.print_exc()
            self.log.error(_("Type Error: %s") % e)
        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://issues.kolab.org")
        sys.exit(exitcode)

    def do_sync(self):
        while 1:
            self.log.debug(_("Sleeping for 10 seconds..."), 5)
            time.sleep(10)
            auth = Auth(self.conf)
            users = auth.users()
            imap = IMAP(self.conf)
            imap.synchronize(users)

