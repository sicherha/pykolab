# -*- coding: utf-8 -*-
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

from pykolab.conf import Defaults, Runtime
import pykolab.conf

class PyKolabBase(object):

    def __init__(self, pykolab):
        """
            Initializes the a PyKolab class with the options specified from the command line.
            Launches our plugin detection.
            Creates a logger instance
            Creates a configuration store
            Detects whether we are in CLI or GUI mode
            Sets the logger configuration
            Sets up the final configuration store
        """

        # Get the options parser, it's valuable ;-)
        self.parser = revisor.parser

        # The options it has defined are valuable too
        self.cli_options = revisor.cli_options
        self.plugins = revisor.plugins
        self.plugins.base = self

        # At this point, 'self' isn't much yet, so:
        # first create a simple logger instance that won't do much,
        # then create a configuration store with that logger,
        # then start detecting the mode that we are in (GUI / CLI),
        # then let the logger know about the configuration store,
        # then /really/ set up the configuration store (now that it has a
        #     valid logger that knows about the configuration store),
        #
        # Create logger
        self.create_logger()

        # Create ConfigStore (it needs the logger to be created!)
        self.create_configstore()

        # Detect our mode (options or try/except)
        self.detect_mode()

        # Let the logger know about cfg (it needs a ConfigStore instance!)
        self.log.set_config(self.cfg)

        # Then really setup the ConfigStore (because that needs a logger!)
        self.cfg.setup_cfg()

        misc.check_selinux(log=self.log)


