# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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

import grp
import logging
import logging.handlers
import os
import pwd
import sys
import time

from pykolab.translate import _

class Logger(logging.Logger):
    """
        The PyKolab version of a logger.

        This class wraps the Python native logging library, adding to the
        loglevel capabilities, a debuglevel capability.
    """
    debuglevel = 0
    fork = False
    loglevel = logging.CRITICAL

    if hasattr(sys, 'argv'):
        for arg in sys.argv:
            if debuglevel == -1:
                try:
                    debuglevel = int(arg)
                except ValueError, errmsg:
                    continue

                loglevel = logging.DEBUG
                break

            if '-d' == arg:
                debuglevel = -1
                continue

            if '-l' == arg:
                loglevel = -1
                continue

            if '--fork' == arg:
                fork = True

            if loglevel == -1:
                if hasattr(logging,arg.upper()):
                    loglevel = getattr(logging,arg.upper())
                else:
                    loglevel = logging.DEBUG

    def __init__(self, *args, **kw):
        if kw.has_key('name'):
            name = kw['name']
        elif len(args) == 1:
            name = args[0]
        else:
            name = 'pykolab'

        logging.Logger.__init__(self, name)

        plaintextformatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

        if not self.fork:
            self.console_stdout = logging.StreamHandler(sys.stdout)
            self.console_stdout.setFormatter(plaintextformatter)

            self.addHandler(self.console_stdout)

        if kw.has_key('logfile'):
            self.logfile = kw['logfile']
        else:
            self.logfile = '/var/log/kolab/pykolab.log'

        # Make sure (read: attempt to change) the permissions
        try:
            (ruid, euid, suid) = os.getresuid()
            (rgid, egid, sgid) = os.getresgid()
        except AttributeError, errmsg:
            ruid = os.getuid()
            rgid = os.getgid()

        if ruid == 0 or rgid == 0:
            if os.path.isfile(self.logfile):
                try:
                    os.chown(
                            self.logfile,
                            pwd.getpwnam('kolab')[2],
                            grp.getgrnam('kolab-n')[2]
                        )
                    os.chmod(self.logfile, 0660)
                except:
                    pass

        # Make sure the log file exists
        try:
            fhandle = file(self.logfile, 'a')
            try:
                os.utime(self.logfile, None)
            finally:
                fhandle.close()

            try:
                filelog_handler = logging.FileHandler(filename=self.logfile)
                filelog_handler.setFormatter(plaintextformatter)
            except IOError, e:
                print >> sys.stderr, _("Cannot log to file %s: %s") % (self.logfile, e)

            if not len(self.handlers) > 1:
                try:
                    self.addHandler(filelog_handler)
                except:
                    pass

        except IOError, errmsg:
            pass

    def remove_stdout_handler(self):
        if not self.fork:
            self.console_stdout.close()
            self.removeHandler(self.console_stdout)

    def debug(self, msg, level=1):
        self.setLevel(self.loglevel)
        # Work around other applications not using various levels of debugging
        if not self.name.startswith('pykolab') and not self.debuglevel == 9:
            return

        if level <= self.debuglevel:
            # TODO: Not the way it's supposed to work!
            self.log(logging.DEBUG, '[%d]: %s' % (os.getpid(),msg))
 

logging.setLoggerClass(Logger)
