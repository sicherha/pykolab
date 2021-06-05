# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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

import logging
import os
import sys

from optparse import OptionParser
from ConfigParser import SafeConfigParser

import pykolab

from pykolab.conf.defaults import Defaults

from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.conf')


class Conf(object):
    def __init__(self):
        """
            self.cli_args == Arguments passed on the CLI
            self.cli_keywords == Parser results (again, CLI)
            self.cli_parser == The actual Parser (from OptionParser)
            self.plugins == Our Kolab Plugins
        """

        self.cli_parser = None
        self.cli_args = None
        self.cli_keywords = None

        self.entitlement = None

        self.changelog = {}

        try:
            from pykolab.conf.entitlement import Entitlement
            entitlements = True
        except Exception:
            entitlements = False
            pass

        if entitlements:
            self.entitlement = Entitlement().get()

        self.plugins = None

        # The location where our configuration parser is going to end up
        self.cfg_parser = None

        # Create the options
        self.create_options()

    def finalize_conf(self, fatal=True):

        self.create_options_from_plugins()
        self.parse_options(fatal=fatal)

        # The defaults can some from;
        # - a file we ship with the packages
        # - a customly supplied file (by customer)
        # - a file we write out
        # - this python class
        #
        # Look, we want defaults
        self.defaults = Defaults(self.plugins)

        # But, they should be available in our class as well
        for option in self.defaults.__dict__:
            log.debug(
                _("Setting %s to %r (from defaults)") % (
                    option,
                    self.defaults.__dict__[option]
                ),
                level=8
            )

            setattr(self, option, self.defaults.__dict__[option])

        # This is where we check our parser for the defaults being set there.
        self.set_defaults_from_cli_options()

        self.options_set_from_config()

        # Also set the cli options
        if hasattr(self, 'cli_keywords') and self.cli_keywords is not None:
            for option in self.cli_keywords.__dict__:
                retval = False
                if hasattr(self, "check_setting_%s" % (option)):
                    exec(
                        "retval = self.check_setting_%s(%r)" % (
                            option,
                            self.cli_keywords.__dict__[option]
                        )
                    )

                    # The warning, error or confirmation dialog is in the check_setting_%s()
                    # function
                    if not retval:
                        continue

                    log.debug(
                        _("Setting %s to %r (from CLI, verified)") % (
                            option,
                            self.cli_keywords.__dict__[option]
                        ),
                        level=8
                    )

                    setattr(self, option, self.cli_keywords.__dict__[option])
                else:
                    log.debug(
                        _("Setting %s to %r (from CLI, not checked)") % (
                            option,
                            self.cli_keywords.__dict__[option]
                        ),
                        level=8
                    )

                    setattr(self, option, self.cli_keywords.__dict__[option])

    def load_config(self, config):
        """
            Given a SafeConfigParser instance, loads a configuration
            file and checks, then sets everything it can find.
        """

        for section in self.defaults.__dict__:
            if section == 'testing':
                continue

            if not config.has_section(section):
                continue

            for key in self.defaults.__dict__[section]:
                retval = False
                if not config.has_option(section, key):
                    continue

                if isinstance(self.defaults.__dict__[section][key], int):
                    value = config.getint(section, key)
                elif isinstance(self.defaults.__dict__[section][key], bool):
                    value = config.getboolean(section, key)
                elif isinstance(self.defaults.__dict__[section][key], str):
                    value = config.get(section, key)
                elif isinstance(self.defaults.__dict__[section][key], list):
                    value = eval(config.get(section, key))
                elif isinstance(self.defaults.__dict__[section][key], dict):
                    value = eval(config.get(section, key))

                if hasattr(self, "check_setting_%s_%s" % (section, key)):
                    exec("retval = self.check_setting_%s_%s(%r)" % (section, key, value))
                    if not retval:
                        # We just don't set it, check_setting_%s should have
                        # taken care of the error messages
                        continue

                if not self.defaults.__dict__[section][key] == value:
                    if key.count('password') >= 1:
                        log.debug(
                            _("Setting %s_%s to '****' (from configuration file)") % (
                                section,
                                key
                            ),
                            level=8
                        )

                    else:
                        log.debug(
                            _("Setting %s_%s to %r (from configuration file)") % (
                                section,
                                key,
                                value
                            ),
                            level=8
                        )

                    setattr(self, "%s_%s" % (section, key), value)

    def options_set_from_config(self):
        """
            Sets the default configuration options from a
            configuration file. Configuration file may be
            customized using the --config CLI option
        """

        log.debug(_("Setting options from configuration file"), level=4)

        # Check from which configuration file we should get the defaults
        # Other then default?
        self.config_file = self.defaults.config_file

        if hasattr(self, 'cli_keywords') and self.cli_keywords is not None:
            if not self.cli_keywords.config_file == self.defaults.config_file:
                self.config_file = self.cli_keywords.config_file

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
            retval = False

            if isinstance(self.defaults.__dict__['testing'][key], int):
                value = config.getint('testing', key)
            elif isinstance(self.defaults.__dict__['testing'][key], bool):
                value = config.getboolean('testing', key)
            elif isinstance(self.defaults.__dict__['testing'][key], str):
                value = config.get('testing', key)
            elif isinstance(self.defaults.__dict__['testing'][key], list):
                value = eval(config.get('testing', key))
            elif isinstance(self.defaults.__dict__['testing'][key], dict):
                value = eval(config.get('testing', key))

            if hasattr(self, "check_setting_%s_%s" % ('testing', key)):
                exec("retval = self.check_setting_%s_%s(%r)" % ('testing', key, value))
                if not retval:
                    # We just don't set it, check_setting_%s should have
                    # taken care of the error messages
                    continue

            setattr(self, "%s_%s" % ('testing', key), value)
            if key.count('password') >= 1:
                log.debug(
                    _("Setting %s_%s to '****' (from configuration file)") % ('testing', key),
                    level=8
                )

            else:
                log.debug(
                    _("Setting %s_%s to %r (from configuration file)") % ('testing', key, value),
                    level=8
                )

    def check_config(self, val=None):
        """
            Checks self.config_file or the filename passed using 'val'
            and returns a SafeConfigParser instance if everything is OK.
        """

        if val is not None:
            config_file = val
        else:
            config_file = self.config_file

        if not os.access(config_file, os.R_OK):
            log.error(_("Configuration file %s not readable") % config_file)

        config = SafeConfigParser()
        log.debug(_("Reading configuration file %s") % config_file, level=8)
        try:
            config.read(config_file)
        except Exception:
            log.error(_("Invalid configuration file %s") % config_file)

        if not config.has_section("kolab"):
            log.warning(
                _("No master configuration section [kolab] in configuration file %s") % config_file
            )

        return config

    def add_cli_parser_option_group(self, name):
        return self.cli_parser.add_option_group(name)

    def create_options_from_plugins(self):
        """
            Create options from plugins.

            This function must be called separately from Conf.__init__(), or
            the configuration store is not yet done initializing when the
            plugins class and the plugins themselves go look for it.
        """
        import pykolab.plugins
        self.plugins = pykolab.plugins.KolabPlugins()
        self.plugins.add_options(self.cli_parser)

    def create_options(self, load_plugins=True):
        """
            Create the OptionParser for the options passed to us from runtime
            Command Line Interface.
        """

        # Enterprise Linux 5 does not have an "epilog" parameter to OptionParser
        try:
            self.cli_parser = OptionParser(epilog=epilog)
        except Exception:
            self.cli_parser = OptionParser()

        #
        # Runtime Options
        #
        runtime_group = self.cli_parser.add_option_group(_("Runtime Options"))
        runtime_group.add_option(
            "-c", "--config",
            dest="config_file",
            action="store",
            default="/etc/kolab/kolab.conf",
            help=_("Configuration file to use")
        )

        runtime_group.add_option(
            "-d", "--debug",
            dest="debuglevel",
            type='int',
            default=0,
            help=_(
                "Set the debugging verbosity. Maximum is 9, tracing protocols LDAP, SQL and IMAP."
            )
        )

        runtime_group.add_option(
            "-e", "--default",
            dest="answer_default",
            action="store_true",
            default=False,
            help=_("Use the default answer to all questions.")
        )

        runtime_group.add_option(
            "-l",
            dest="loglevel",
            type='str',
            default="CRITICAL",
            help=_("Set the logging level. One of info, warn, error, critical or debug")
        )

        runtime_group.add_option(
            "--logfile",
            dest="logfile",
            action="store",
            default="/var/log/kolab/pykolab.log",
            help=_("Log file to use")
        )

        runtime_group.add_option(
            "-q", "--quiet",
            dest="quiet",
            action="store_true",
            default=False,
            help=_("Be quiet.")
        )

        runtime_group.add_option(
            "-y", "--yes",
            dest="answer_yes",
            action="store_true",
            default=False,
            help=_("Answer yes to all questions.")
        )

    def parse_options(self, fatal=True):
        """
            Parse options passed to our call.
        """

        if fatal:
            (self.cli_keywords, self.cli_args) = self.cli_parser.parse_args()

    def run(self):
        """
            Run Forest, RUN!
        """
        if self.cli_args:
            if len(self.cli_args) >= 1:
                if hasattr(self, "command_%s" % self.cli_args[0].replace('-', '_')):
                    exec(
                        "self.command_%s(%r)" % (
                            self.cli_args[0].replace('-', '_'),
                            self.cli_args[1:]
                        )
                    )

            else:
                print(_("No command supplied"), file=sys.stderr)

    def command_dump(self, *args, **kw):
        """
            Dumps applicable, valid configuration that is not defaults.
        """

        if not self.cfg_parser:
            self.read_config()

        if not self.cfg_parser.has_section('kolab'):
            print("No section found for kolab", file=sys.stderr)
            sys.exit(1)

        # Get the sections, and then walk through the sections in a
        # sensible way.
        items = self.cfg_parser.options('kolab')

        items.sort()

        for item in items:
            mode = self.cfg_parser.get('kolab', item)
            print("%s = %s" % (item, mode))

            if not self.cfg_parser.has_section(mode):
                print("WARNING: No configuration section %s for item %s" % (mode, item))
                continue

            keys = self.cfg_parser.options(mode)
            keys.sort()

            if self.cfg_parser.has_option(mode, 'leave_this_one_to_me'):
                print("Ignoring section %s" % (mode))
                continue

            for key in keys:
                print("%s_%s = %s" % (mode, key, self.cfg_parser.get(mode, key)))

    def read_config(self, value=None):
        """
            Reads the configuration file, sets a self.cfg_parser.
        """

        if not value:
            value = self.defaults.config_file

            if hasattr(self, 'cli_keywords') and self.cli_keywords is not None:
                    value = self.cli_keywords.config_file

        self.cfg_parser = SafeConfigParser()
        self.cfg_parser.read(value)

        if hasattr(self, 'cli_keywords') and hasattr(self.cli_keywords, 'config_file'):
            self.cli_keywords.config_file = value
        self.defaults.config_file = value
        self.config_file = value

    def command_get(self, *args, **kw):
        """
            Get a configuration option.

            Pass me a section and key please.
        """

        exec("args = %r" % args)

        print("%s/%s: %r" % (args[0], args[1], self.get(args[0], args[1])))

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

        if not self.cfg_parser:
            self.read_config()

        if not len(args) == 3:
            log.error(_("Insufficient options. Need section, key and value -in that order."))

        if not self.cfg_parser.has_section(args[0]):
            log.error(_("No section '%s' exists.") % (args[0]))

        if '%' in args[2]:
            value = args[2].replace('%', '%%')
        else:
            value = args[2]

        self.cfg_parser.set(args[0], args[1], value)

        if hasattr(self, 'cli_keywords') and hasattr(self.cli_keywords, 'config_file'):
            fp = open(self.cli_keywords.config_file, "w+")
            self.cfg_parser.write(fp)
            fp.close()
        else:
            fp = open(self.config_file, "w+")
            self.cfg_parser.write(fp)
            fp.close()

    def create_logger(self):
        """
            Create a logger instance using cli_options.debuglevel
        """
        global log

        if self.cli_keywords.debuglevel is not None:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
            self.cli_keywords.debuglevel = 0

        self.debuglevel = self.cli_keywords.debuglevel

        # Initialize logger
        log = pykolab.logger.Logger(
            loglevel=loglevel,
            debuglevel=self.cli_keywords.debuglevel,
            logfile=self.cli_keywords.logfile
        )

    def set_defaults_from_cli_options(self):
        for long_opt in self.cli_parser.__dict__['_long_opt']:
            if long_opt == "--help":
                continue

            setattr(
                self.defaults,
                self.cli_parser._long_opt[long_opt].dest,
                self.cli_parser._long_opt[long_opt].default
            )

        # But, they should be available in our class as well
        for option in self.cli_parser.defaults:
            log.debug(
                _("Setting %s to %r (from the default values for CLI options)") % (
                    option,
                    self.cli_parser.defaults[option]
                ),
                level=8
            )

            setattr(self, option, self.cli_parser.defaults[option])

    def has_section(self, section):
        if not self.cfg_parser:
            self.read_config()

        return self.cfg_parser.has_section(section)

    def has_option(self, section, option):
        if not self.cfg_parser:
            self.read_config()

        return self.cfg_parser.has_option(section, option)

    def get_list(self, section, key, default=None):
        """
            Gets a comma and/or space separated list from the configuration file
            and returns a list.
        """
        values = []
        untrimmed_values = []

        setting = self.get_raw(section, key)

        if setting is None:
            return default if default else []

        raw_values = setting.split(',')

        if raw_values is None:
            return default if default else []

        for raw_value in raw_values:
            untrimmed_values.extend(raw_value.split(' '))

        for value in untrimmed_values:
            if not value.strip() == "":
                values.append(value.strip().lower())

        return values

    def get_raw(self, section, key, default=None):
        if not self.cfg_parser:
            self.read_config()

        if self.cfg_parser.has_option(section, key):
            return self.cfg_parser.get(section, key, 1)

        return default

    def get(self, section, key, default=None, quiet=False):
        """
            Get a configuration option from our store, the configuration file,
            or an external source if we have some sort of function for it.

            TODO: Include getting the value from plugins through a hook.
        """
        retval = False

        if not self.cfg_parser:
            self.read_config()

        # log.debug(_("Obtaining value for section %r, key %r") % (section, key), level=8)

        if self.cfg_parser.has_option(section, key):
            try:
                return self.cfg_parser.get(section, key)
            except Exception:
                self.read_config()
                return self.cfg_parser.get(section, key)

        if hasattr(self, "get_%s_%s" % (section, key)):
            try:
                exec("retval = self.get_%s_%s(quiet)" % (section, key))
            except Exception:
                log.error(
                    _("Could not execute configuration function: %s") % (
                        "get_%s_%s(quiet=%r)" % (
                            section,
                            key,
                            quiet
                        )
                    )
                )

                return default

            return retval

        if quiet:
            return ""
        else:
            log.warning(
                _("Option %s/%s does not exist in config file %s, pulling from defaults") % (
                    section,
                    key,
                    self.config_file
                )
            )

            if hasattr(self.defaults, "%s_%s" % (section, key)):
                return getattr(self.defaults, "%s_%s" % (section, key))
            elif hasattr(self.defaults, "%s" % (section)):
                if key in getattr(self.defaults, "%s" % (section)):
                    _dict = getattr(self.defaults, "%s" % (section))
                    return _dict[key]
                else:
                    log.warning(_("Option does not exist in defaults."))
                    return default
            else:
                log.warning(_("Option does not exist in defaults."))
                return default

    def check_setting_config_file(self, value):
        if os.path.isfile(value):
            if os.access(value, os.R_OK):
                self.read_config(value=value)
                self.config_file = value
                return True
            else:
                log.error(_("Configuration file %s not readable.") % (value))
                return False
        else:
            log.error(_("Configuration file %s does not exist.") % (value))
            return False

    def check_setting_debuglevel(self, value):
        if value < 0:
            log.info(
                _(
                    "WARNING: A negative debug level value does not "
                    + "make this program be any more silent."
                )
            )

        elif value == 0:
            return True
        elif value <= 9:
            return True
        else:
            log.warning(_("This program has 9 levels of verbosity. Using the maximum of 9."))
            return True

    def check_setting_saslauth_mode(self, value):
        if value:
            # TODO: I suppose this is platform specific
            if os.path.isfile("/var/run/saslauthd/mux"):
                if os.path.isfile("/var/run/saslauthd/saslauthd.pid"):
                    log.error(_("Cannot start SASL authentication daemon"))
                    return False
                else:
                    try:
                        os.remove("/var/run/saslauthd/mux")
                    except IOError:
                        log.error(_("Cannot start SASL authentication daemon"))
                        return False
            elif os.path.isfile("/var/run/sasl2/mux"):
                if os.path.isfile("/var/run/sasl2/saslauthd.pid"):
                    log.error(_("Cannot start SASL authentication daemon"))
                    return False
                else:
                    try:
                        os.remove("/var/run/sasl2/mux")
                    except IOError:
                        log.error(_("Cannot start SASL authentication daemon"))
                        return False
        return True

    def check_setting_use_imap(self, value):
        if value:
            try:
                import imaplib
                self.use_imap = value
                return True
            except ImportError:
                log.error(_("No imaplib library found."))
                return False

    def check_setting_use_lmtp(self, value):
        if value:
            try:
                from smtplib import LMTP
                self.use_lmtp = value
                return True
            except ImportError:
                log.error(_("No LMTP class found in the smtplib library."))
                return False

    def check_setting_use_mail(self, value):
        if value:
            try:
                from smtplib import SMTP
                self.use_mail = value
                return True
            except ImportError:
                log.error(_("No SMTP class found in the smtplib library."))
                return False

    def check_setting_test_suites(self, value):
        # Attempt to load the suite,
        # Get the suite's options,
        # Set them here.
        if not hasattr(self, 'test_suites'):
            self.test_suites = []

        if "zpush" in value:
            selectively = False
            for item in ['calendar', 'contacts', 'mail']:
                if self.cli_keywords.__dict__[item]:
                    log.debug(
                        _("Found you specified a specific set of items to test: %s") % (item),
                        level=8
                    )

                    selectively = item

            if not selectively:
                self.calendar = True
                self.contacts = True
                self.mail = True
            else:
                log.debug(_("Selectively selecting: %s") % (selectively), level=8)
                setattr(self, selectively, True)

            self.test_suites.append('zpush')

    def check_setting_calendar(self, value):
        if self.cli_parser._long_opt['--calendar'].default == value:
            return False
        else:
            return True

    def check_setting_contacts(self, value):
        if self.cli_parser._long_opt['--contacts'].default == value:
            return False
        else:
            return True

    def check_setting_mail(self, value):
        if self.cli_parser._long_opt['--mail'].default == value:
            return False
        else:
            return True
