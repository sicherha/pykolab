#!/usr/bin/python
#
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

import os
import rfc822
import socket
import sys
import time

from optparse import OptionParser
from ConfigParser import SafeConfigParser

import sqlalchemy
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text

from sqlalchemy import create_engine
from sqlalchemy.orm import mapper

try:
    from sqlalchemy.orm import relationship
except:
    from sqlalchemy.orm import relation as relationship

try:
    from sqlalchemy.orm import sessionmaker
except:
    from sqlalchemy.orm import create_session

from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint

sys.path.append('..')
sys.path.append('../..')

import pykolab

from pykolab.auth import Auth
from pykolab.constants import KOLAB_LIB_PATH
from pykolab import telemetry
from pykolab.translate import _

# TODO: Figure out how to make our logger do some syslogging as well.
log = pykolab.getLogger('pykolab.parse_telemetry')

# TODO: Removing the stdout handler would mean one can no longer test by
# means of manual execution in debug mode.
#log.remove_stdout_handler()

conf = pykolab.getConf()
conf.finalize_conf()

auth = Auth()

db = telemetry.init_db()

while True:
    try:
        log_file = conf.cli_args.pop(0)
    except:
        # TODO: More verbose failing or parse all in /var/lib/imap/log/ or
        # options?
        break

    telemetry_log = telemetry.TelemetryLog(log_file)

telemetry.expire_sessions()
