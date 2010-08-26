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

import logging
import os
import sys

from optparse import OptionParser
from ConfigParser import SafeConfigParser

import pykolab
from pykolab.conf.defaults import Defaults
from pykolab.conf.runtime import Runtime
from pykolab.constants import *
from pykolab.translate import _

class Conf(object):
    def __init__(self):
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

        # The location where our configuration parser is going to end up
        self.cfg_parser = None

        # Create and parse the options
        self.parse_options()

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

        # Let the logger know about cfg (it needs a ConfigStore instance!)
        self.log.set_config(self)

        # The defaults can some from;
        # - a file we ship with the packages
        # - a customly supplied file (by customer)
        # - a file we write out
        # - this python class
        #
        # Look, we want defaults
        self.defaults = Defaults(self.plugins)

        # This is where we check our parser for the defaults being set there.
        self.set_defaults_from_cli_options()

        # But, they should be available in our class as well
        for option in self.defaults.__dict__.keys():
            setattr(self,option,self.defaults.__dict__[option])

        # There is also a number of runtime specific variables
        self.runtime = Runtime(self.plugins, self.defaults)

        # Which should also be available here
        for option in self.runtime.__dict__.keys():
            self.log.debug(_("Setting %s to %r") % (option, self.runtime.__dict__[option]), level=9)
            setattr(self,option,self.runtime.__dict__[option])

    def parse_options(self, load_plugins=True):
        """
            Create the OptionParser for the options passed to us from runtime
            Command Line Interface.
        """

        # Enterprise Linux 5 does not have an "epilog" parameter to OptionParser
        try:
            self.parser = OptionParser(epilog=epilog)
        except:
            self.parser = OptionParser()

        ##
        ## Runtime Options
        ##
        runtime_group = self.parser.add_option_group(_("Runtime Options"))
        runtime_group.add_option(   "-c", "--config",
                                    dest    = "config_file",
                                    action  = "store",
                                    default = "/etc/kolab/kolab.conf",
                                    help    = _("Configuration file to use"))

        runtime_group.add_option(   "-d", "--debug",
                                    dest    = "debuglevel",
                                    type    = 'int',
                                    default = 0,
                                    help    = _("Set the debugging verbosity. Maximum is 99"))

        runtime_group.add_option(   "--logfile",
                                    dest    = "logfile",
                                    action  = "store",
                                    default = "/var/log/kolabd/kolabd.log",
                                    help    = _("Log file to use"))

        runtime_group.add_option(   "-y", "--yes",
                                    dest    = "answer_yes",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Configuration file to use"))

        ##
        ## Get options from plugins
        ##
        if load_plugins:
            self.plugins = pykolab.plugins.KolabPlugins(init=True)
            self.plugins.add_options(self.parser)

        # Parse Options
        (self.cli_options, self.args) = self.parser.parse_args()

    def run(self):
        """
            Run Forest, RUN!
        """
        exitcode = 0

        if len(self.args) >= 1:
            if hasattr(self,"command_%s" % self.args[0].replace('-','_')):
                exec("self.command_%s(%r)" %  (self.args[0].replace('-','_'), self.args[1:]))
        else:
            print >> sys.stderr, _("No command supplied")


    def command_dump(self, *args, **kw):
        """
            Dumps applicable, valid configuration that is not defaults.
        """

        if not self.cfg_parser:
            self.read_config()

        if not self.cfg_parser.has_section('kolab'):
            print "No section found for kolab"
            sys.exit(1)

        # Get the sections, and then walk through the sections in a
        # sensible way.
        items = self.cfg_parser.options('kolab')

        items.sort()

        for item in items:
            mode = self.cfg_parser.get('kolab',item)
            print "%s = %s" %(item,mode)

            if not self.cfg_parser.has_section(mode):
                print "WARNING: No configuratino section for %s: %s" %(item,mode,)
                continue

            keys = self.cfg_parser.options(mode)
            keys.sort()

            if self.cfg_parser.has_option(mode, 'leave_this_one_to_me'):
                print "Ignoring section %s" %(mode,)
                continue

            for key in keys:
                print "%s_%s = %s" %(mode, key ,self.cfg_parser.get(mode,key))

    def read_config(self):
        """
            Reads the configuration file, sets a self.cfg_parser.
        """

        self.cfg_parser = SafeConfigParser()
        self.cfg_parser.read(self.cli_options.config_file)

    def command_get(self, *args, **kw):
        """
            Get a configuration option.

            Pass me a section and key please.
        """
        exec("args = %r" % args)

        if not self.cfg_parser:
            self.read_config()

        if len(args) == 1:
            self.log.error(_("Only one option supplied"), recoverable=False)

        if len(args) == 2:
            if self.cfg_parser.has_option(args[0], args[1]):
                print "%s/%s: %r" %(args[0],args[1],self.cfg_parser.get(args[0],args[1]))
            else:
                self.log.warning(_("Option does not exist in config file, pulling from defaults"))
                print "Something default"

#        if len(args) == 3:
#            # Return non-zero if no match
#            # Return zero if match
#            # Improvised "check" function

    def command_set(self, *args, **kw):
        """
            Set a configuration option.

            Pass me a section, key and value please. Note that the section should
            already exist.

            TODO: Add a strict parameter
            TODO: Add key value checking
        """
        exec("args = %r" % args)

        if not self.cfg_parser:
            self.read_config()

        if not len(args) == 3:
            self.log.error(_("Insufficient options. Need section, key and value -in that order."), recoverable=False)

        if not self.cfg_parser.has_section(args[0]):
            self.log.error(_("No section '%s' exists.") %(args[0]))

        self.cfg_parser.set(args[0], args[1], args[2])
        fp = open(self.cli_options.config_file, "w+")
        self.cfg_parser.write(fp)
        fp.close()

    def create_logger(self):
        """Create a logger instance using cli_options.debuglevel"""
        if not self.cli_options.debuglevel == None:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
            self.cli_options.debuglevel = 0

        # Initialize logger
        self.log = pykolab.logger.Logger(loglevel=loglevel, debuglevel=self.cli_options.debuglevel, logfile=self.cli_options.logfile)

    def set_defaults_from_cli_options(self):
        for long_opt in self.parser.__dict__['_long_opt'].keys():
            if long_opt == "--help":
                continue
            setattr(self.defaults,self.parser._long_opt[long_opt].dest,self.parser._long_opt[long_opt].default)

