#!/usr/bin/python
#
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

# For development purposes
sys.path.extend(['.', '..'])

from pykolab.translate import _

try:
    import pykolab.logger
except ImportError, e:
    print >> sys.stderr, _("Cannot load pykolab/logger.py:")
    print >> sys.stderr, "%s" % e
    sys.exit(1)

import kolabd

if __name__ == "__main__":
    kolabd = kolabd.KolabDaemon()
    kolabd.run()

