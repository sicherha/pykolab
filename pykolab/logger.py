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
import logging.handlers
import sys

# Translation
from pykolab.translate import _, N_

class Logger:
    def __init__(self, loglevel=logging.INFO, debuglevel=0, logfile="/var/log/kolab/kolabd.log"):

        self.loglevel = loglevel
        self.debuglevel = debuglevel

        plaintextformatter = logging.Formatter("%(message)s")

        self.console_stdout = logging.StreamHandler(sys.stdout)
        self.console_stdout.setFormatter(plaintextformatter)

        try:
            filelog_handler = logging.FileHandler(filename=logfile)
            filelog_handler.setFormatter(plaintextformatter)
        except IOError, e:
            print >> sys.stderr, _("Cannot log to file %s: %s") % (logfile, e)

        self.log = logging.getLogger('pykolab')

        if not len(self.log.handlers) > 1:
            self.log.addHandler(self.console_stdout)
            try:
                self.log.addHandler(filelog_handler)
            except:
                pass

            self.log.setLevel(self.loglevel)

    def remove_stdout_handler(self):
        self.log.removeHandler(self.console_stdout)

    def set_config(self, cfg):
        """Let the Logger instance know what our configuration is and she might
        be able to distinct between CLI and GUI mode, or even give more details
        about what goes wrong"""
        self.cfg = cfg

    def info(self, msg):
        if not self.cfg.quiet:
            self.log.info(msg)

    def debug(self, msg, level=1):
        # By default, level=1 so that debug messages are suppressed
        if level <= self.debuglevel:
            self.log.debug(msg)

    def error(self, msg, recoverable=True):
        self.log.error(msg)
        if recoverable:
            self.error_prompt(msg)
        else:
            sys.exit(1)

    def warning(self, msg):
        self.log.warning(msg)
        self.warning_prompt(msg)

    def error_prompt(self, text):
        """The error has already been logged to the console, try and catch some input"""
        if not self.cfg.answer_yes:
            sys.stderr.write(_("Do you want to continue? [Y/n]") + " ")
            answer = sys.stdin.readline()[:-1]
            if answer == "n":
                self.error(_("Abort! Abort! Abort!"), recoverable=False)
                sys.exit(1)

    def warning_prompt(self, text):
        """The error has already been logged to the console, try and catch some input"""
        if not self.cfg.answer_yes:
            sys.stdout.write(_("Do you want to continue? [Y/n]") + " ")
            answer = sys.stdin.readline()[:-1]
            if answer == "n":
                self.error(_("Abort! Abort! Abort!"), recoverable=False)
                sys.exit(1)
