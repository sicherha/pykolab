#!/usr/bin/python
#
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function

import os
import sys

# For development purposes
if os.path.isdir(os.path.join(os.path.dirname(__file__), '.git')):
    sys.path.insert(0, '.')

from pykolab.translate import _


try:
    from pykolab.constants import *
except ImportError as errmsg:
    print(_("Cannot load pykolab/constants.py:"), file=sys.stderr)
    print("%s" % (errmsg), file=sys.stderr)
    sys.exit(1)

import kolabd

if __name__ == "__main__":
    kolabd = kolabd.KolabDaemon()
    kolabd.run()
