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

"""

    pyKolab, the interface to Kolab Groupware Solution management in Python.

"""

import logging
import shutil
import sys
import threading
import traceback

from pykolab.logger import Logger
logging.setLoggerClass(Logger)

def getLogger(name):
    """
        Return the correct logger class.
    """
    logging.setLoggerClass(Logger)
    log = logging.getLogger(name=name)
    return log

from pykolab.conf import Conf

conf = Conf()

def getConf():
    _data = threading.local()
    if hasattr(_data, 'conf'):
        log.debug(_("Returning thread local configuration"))
        return _data.conf

    return conf

import base
