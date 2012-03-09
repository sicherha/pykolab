# -*- coding: utf-8 -*-
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

import time
import traceback

from pykolab.tests import tests

import pykolab

from pykolab.translate import _
from pykolab import utils

log = pykolab.getLogger('pykolab.tests')
conf = pykolab.getConf()

auth = pykolab.auth
imap = pykolab.imap

def __init__():
    tests.register('login', execute, group='imap', description=description())

def description():
    return """Connect to IMAP and login."""

def execute(*args, **kw):
    try:
        log.debug(_("Connecting at %s") % (time.time()), level=8)
        imap.connect(login=False)
        log.debug(_("Connected at %s") % (time.time()), level=8)
    except:
        raise TestFailureException, __file__

    try:
        log.debug(_("Logging in at %s") % (time.time()), level=8)
        imap.login('doe', password='0cvRKSdluPU4ewN')
        log.debug(_("Logged in at %s") % (time.time()), level=8)
        #imap.login('doe', password='bla')
    except:
        raise TestFailureException(__file__)

class TestFailureException(BaseException):
    def __init__(self, test_file):
        log.error(_("Test failure in %s") % (test_file))
        utils.ask_confirmation('Would you like to log this as a bug?')