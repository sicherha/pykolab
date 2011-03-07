# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
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

        # Create the options
        self.create_options()

    def finalize_conf(self):
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

        # But, they should be available in our class as well
        for option in self.defaults.__dict__.keys():
            self.log.debug(_("Setting %s to %r (from defaults)") %(option, self.defaults.__dict__[option]), level=9)
            setattr(self,option,self.defaults.__dict__[option])

        # This is where we check our parser for the defaults being set there.
        self.set_defaults_from_cli_options()

        # There is also a number of runtime specific variables
        self.runtime = Runtime(self.plugins, self.defaults)

        # Which should also be available here
        for option in self.runtime.__dict__.keys():
            self.log.debug(_("Setting %s to %r (from runtime)") %(option, self.runtime.__dict__[option]), level=9)
            setattr(self,option,self.runtime.__dict__[option])

        self.options_set_from_config()

        # Also set the cli options
        for option in self.cli_options.__dict__.keys():
            if hasattr(self, "check_setting_%s" %(option)):
                exec("retval = self.check_setting_%s(%r)" % (option, self.cli_options.__dict__[option]))

                # The warning, error or confirmation dialog is in the check_setting_%s() function
                if not retval:
                    continue

                self.log.debug(_("Setting %s to %r (from CLI, verified)") %(option, self.cli_options.__dict__[option]), level=9)
                setattr(self,option,self.cli_options.__dict__[option])
            else:
                self.log.debug(_("Setting %s to %r (from CLI, not checked)") %(option, self.cli_options.__dict__[option]), level=9)
                setattr(self,option,self.cli_options.__dict__[option])

    def load_config(self, config):
        """
            Given a SafeConfigParser instance, loads a configuration
            file and checks, then sets everything it can find.
        """

        for section in self.defaults.__dict__.keys():
            if section == 'testing':
                continue

            #print "section: %s" %(section)
            if not config.has_section(section):
                #print "no section for section %s, continuing" %(section)
                continue

            for key in self.defaults.__dict__[section].keys():
                #print "key: %s" %(key)
                if not config.has_option(section, key):
                    #print "no key for option %s in section %s, continuing" %(key,section)
                    continue

                if isinstance(self.defaults.__dict__[section][key], int):
                    value = config.getint(section,key)
                elif isinstance(self.defaults.__dict__[section][key], bool):
                    value = config.getboolean(section,key)
                elif isinstance(self.defaults.__dict__[section][key], str):
                    value = config.get(section,key)
                elif isinstance(self.defaults.__dict__[section][key], list):
                    value = eval(config.get(section,key))
                elif isinstance(self.defaults.__dict__[section][key], dict):
                    value = eval(config.get(section,key))

                if hasattr(self,"check_setting_%s_%s" %(section,key)):
                    exec("retval = self.check_setting_%s_%s(%r)" %(section,key,value))
                    if not retval:
                        # We just don't set it, check_setting_%s should have
                        # taken care of the error messages
                        continue

                if not self.defaults.__dict__[section][key] == value:
                    setattr(self,"%s_%s" %(section,key),value)
                    if key.count('password') >= 1:
                        self.log.debug(_("Setting %s_%s to '****' (from configuration file)") %(section,key), level=9)
                    else:
                        self.log.debug(_("Setting %s_%s to %r (from configuration file)") %(section,key,value), level=9)

    def options_set_from_config(self):
        """
            Sets the default configuration options from a
            configuration file. Configuration file may be
            customized using the --config CLI option
        """

        self.log.debug(_("Setting options from configuration file"), level=4)

        # Check from which configuration file we should get the defaults
        # Other then default?
        if not self.cli_options.config_file == self.defaults.config_file:
            self.config_file = self.cli_options.config_file
        else:
            self.config_file = self.defaults.config_file

        config = self.check_config()
        self.load_config(config)

    def set_options_from_testing_section(self):
        """
            Go through the options in the [testing] section if it exists.
        """
        config = self.check_config()

        if not config.has_section('testing'):
            return

        for key in config.options('testing'):

            if isinstance(self.defaults.__dict__['testing'][key], int):
                value = config.getint('testing',key)
            elif isinstance(self.defaults.__dict__['testing'][key], bool):
                value = config.getboolean('testing',key)
            elif isinstance(self.defaults.__dict__['testing'][key], str):
                value = config.get('testing',key)
            elif isinstance(self.defaults.__dict__['testing'][key], list):
                value = eval(config.get('testing',key))
            elif isinstance(self.defaults.__dict__['testing'][key], dict):
                value = eval(config.get('testing',key))

            if hasattr(self,"check_setting_%s_%s" %('testing',key)):
                exec("retval = self.check_setting_%s(%r)" % ('testing',key,value))
                if not retval:
                    # We just don't set it, check_setting_%s should have
                    # taken care of the error messages
                    continue

            setattr(self,"%s_%s" %('testing',key),value)
            if key.count('password') >= 1:
                self.log.debug(_("Setting %s_%s to '****' (from configuration file)") %('testing',key), level=9)
            else:
                self.log.debug(_("Setting %s_%s to %r (from configuration file)") %('testing',key,value), level=9)

    def check_config(self, val=None):
        """
            Checks self.config_file or the filename passed using 'val'
            and returns a SafeConfigParser instance if everything is OK.
        """

        if not val == None:
            config_file = val
        else:
            config_file = self.config_file

        if not os.access(config_file, os.R_OK):
            self.log.error(_("Configuration file %s not readable") % config_file, recoverable=False)

        config = SafeConfigParser()
        self.log.debug(_("Reading configuration file %s") % config_file, level=9)
        try:
            config.read(config_file)
        except:
            self.log.error(_("Invalid configuration file %s") % config_file, recoverable=False)

        if not config.has_section("kolab"):
            self.log.warning(_("No master configuration section [revisor] in configuration file %s") % config_file)

        return config

    def create_options(self, load_plugins=True):
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

        runtime_group.add_option(   "-q", "--quiet",
                                    dest    = "quiet",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Be quiet."))

        runtime_group.add_option(   "-y", "--yes",
                                    dest    = "answer_yes",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Answer yes to all questions."))

        ##
        ## Get options from plugins
        ##
        if load_plugins:
            self.plugins = pykolab.plugins.KolabPlugins(init=True, conf=self)
            self.plugins.add_options(self.parser)

    def parse_options(self):
        """
            Parse options passed to our call.
        """

        (self.cli_options, self.args) = self.parser.parse_args()

    def run(self):
        """
            Run Forest, RUN!
        """

        exitcode = 0

        if self.args:
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
                print "WARNING: No configuration section %s for item %s" %(mode,item)
                continue

            keys = self.cfg_parser.options(mode)
            keys.sort()

            if self.cfg_parser.has_option(mode, 'leave_this_one_to_me'):
                print "Ignoring section %s" %(mode,)
                continue

            for key in keys:
                print "%s_%s = %s" %(mode, key ,self.cfg_parser.get(mode,key))

    def read_config(self, value=None):
        """
            Reads the configuration file, sets a self.cfg_parser.
        """

        if not value:
            value = self.cli_options.config_file

        self.cfg_parser = SafeConfigParser()
        self.cfg_parser.read(value)

    def command_get(self, *args, **kw):
        """
            Get a configuration option.

            Pass me a section and key please.
        """

        exec("args = %r" % args)

        print "%s/%s: %r" %(args[0],args[1],self.get(args[0], args[1]))

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
        """
            Create a logger instance using cli_options.debuglevel
        """

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

        # But, they should be available in our class as well
        for option in self.parser.values.__dict__.keys():
            self.log.debug(_("Setting %s to %r (from the default values for CLI options)") %(option, self.parser._long_opt[long_opt].default), level=9)
            setattr(self,option,self.parser._long_opt[long_opt].default)

    def has_section(self, section):
        return self.cfg_parser.has_section(section)

    def has_option(self, section, option):
        return self.cfg_parser.has_option(section, option)

    def get_raw(self, section, key):
        if not self.cfg_parser:
            self.read_config()

        if self.cfg_parser.has_option(section, key):
            return self.cfg_parser.get(section,key, 1)

    def get(self, section, key, quiet=False):
        if not self.cfg_parser:
            self.read_config()

        if self.cfg_parser.has_option(section, key):
            return self.cfg_parser.get(section,key)
        else:
            if quiet:
                return ""
            else:
                self.log.warning(_("Option %s/%s does not exist in config file %s, pulling from defaults") %(section, key, self.config_file))
                if hasattr(self.defaults, "%s_%s" %(section,key)):
                    return getattr(self.defaults, "%s_%s" %(section,key))
                elif hasattr(self.defaults, "%s" %(section)):
                    if key in getattr(self.defaults, "%s" %(section)):
                        _dict = getattr(self.defaults, "%s" %(section))
                        return _dict[key]
                    else:
                        self.log.warning(_("Option does not exist in defaults."))
                        return _("Not available")
                else:
                    self.log.warning(_("Option does not exist in defaults."))
                    return _("Not available")

    def check_setting_config_file(self, value):
        if os.path.isfile(value):
            if os.access(value, os.R_OK):
                self.read_config(value=value)
                self.config_file = value
                return True
            else:
                self.log.error(_("Configuration file %s not readable.") %(value), recoverable=False)
                return False
        else:
            self.log.error(_("Configuration file %s does not exist.") %(value), recoverable=False)
            return False

    def check_setting_debuglevel(self, value):
        if value < 0:
            self.log.info(_("WARNING: A negative debug level value does not make this program be any more silent."))
        elif value == 0:
            return True
        elif value <= 9:
            return True
        else:
            self.log.info(_("WARNING: This program has 9 levels of verbosity. Using the maximum of 9."))
            return True

    def check_setting_saslauth_mode(self, value):
        if value:
            # TODO: I suppose this is platform specific
            if os.path.isfile("/var/run/saslauthd/mux"):
                if os.path.isfile("/var/run/saslauthd/saslauthd.pid"):
                    self.log.error(_("Cannot start SASL authentication daemon"))
                    return False
                else:
                    try:
                        os.remove("/var/run/saslauthd/mux")
                    except IOError, e:
                        self.log.error(_("Cannot start SASL authentication daemon"))
                        return False
        return True

    def check_setting_use_imap(self, value):
        if value:
            try:
                import imaplib
                setattr(self,"use_imap",value)
                return True
            except ImportError, e:
                self.log.error(_("No imaplib library found."))
                return False

    def check_setting_use_lmtp(self, value):
        if value:
            try:
                from smtplib import LMTP
                setattr(self,"use_lmtp",value)
                return True
            except ImportError, e:
                self.log.error(_("No LMTP class found in the smtplib library."))
                return False

    def check_setting_use_mail(self, value):
        if value:
            try:
                from smtplib import SMTP
                setattr(self,"use_mail",value)
                return True
            except ImportError, e:
                self.log.error(_("No SMTP class found in the smtplib library."))
                return False

    def check_setting_test_suites(self, value):
        # Attempt to load the suite,
        # Get the suite's options,
        # Set them here.
        if "zpush" in value:
            selectively = False
            for item in [ 'calendar', 'contacts', 'mail' ]:
                if self.cli_options.__dict__[item]:
                    self.log.debug(_("Found you specified a specific set of items to test: %s") %(item), level=9)
                    selectively = item

            if not selectively:
                self.calendar = True
                self.contacts = True
                self.mail = True
            else:
                self.log.debug(_("Selectively selecting: %s") %(selectively), level=9)
                setattr(self, selectively, True)

            self.test_suites.append('zpush')

    def check_setting_calendar(self, value):
        if self.parser._long_opt['--calendar'].default == value:
            return False
        else:
            return True

    def check_setting_contacts(self, value):
        if self.parser._long_opt['--contacts'].default == value:
            return False
        else:
            return True

    def check_setting_mail(self, value):
        if self.parser._long_opt['--mail'].default == value:
            return False
        else:
            return True
