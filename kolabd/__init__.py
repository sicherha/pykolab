# Copyright 2010 Kolab Systems AG (http://www.kolabsys.com)
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

import traceback
import shutil

from pykolab.constants import *
from pykolab.translate import _

class KolabDaemon(object):
    def __init__(self, init_base=True):
        """
            self.args == Arguments passed on the CLI
            self.cli_options == Parser results (again, CLI)
            self.parser == The actual Parser (from OptionParser)
            self.plugins == Our Kolab Plugins
        """

        self.args = None
        self.cli_options = None
        self.parser = None
        self.plugins = None

        # Create and parse the options
        self.parse_options()

    def parse_options(self, load_plugins=True):
        """
            Create the OptionParser for the options passed to us from runtime
            Command Line Interface.
        """

        epilog = "The Kolab Daemon is part of the Kolab Groupware Solution. For" + \
                 "about Kolab or PyKolab, visit http://www.kolabsys.com"

        # Enterprise Linux 5 does not have an "epilog" parameter to OptionParser
        try:
            self.parser = OptionParser(epilog=epilog)
        except:
            self.parser = OptionParser()

        ##
        ## Runtime Options
        ##
        runtime_group = self.parser.add_option_group(_("Runtime Options"))
        runtime_group.add_option(   "-d", "--debug",
                                    dest    = "debuglevel",
                                    type    = 'int',
                                    default = 0,
                                    help    = _("Set the debugging verbosity. Maximum is 99"))

        ##
        ## Get options from plugins
        ##
        if load_plugins:
            self.plugins = pykolab.plugins.KolabPlugins(init=True)
            self.plugins.add_options(self.parser)

        # Parse Options
        (self.cli_options, self.args) = self.parser.parse_args()

    def run(self):
        """Run Forest, RUN!"""

        exitcode = 0

        try:
            self.base.run()
        except SystemExit, e:
            exitcode = e
        except KeyboardInterrupt:
            exitcode = 1
            self.base.log.info(_("Interrupted by user"))
        except AttributeError, e:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://issues.kolab.org")
        except TypeError, e:
            self.log.error(_("Type Error: %s") % e)
        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://issues.kolab.org")
        finally:
            if self.base.cfg.clean_up == 0:
                # Leave everything as it is
                pass
            if self.base.cfg.clean_up > 0:
                # Remove our directories in the working directory
                pass
            if self.base.cfg.clean_up > 1:
                # Remove everything
                pass
        sys.exit(exitcode)

