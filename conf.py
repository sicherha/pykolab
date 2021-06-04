#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
    Kolab configuration utility.
"""

from __future__ import print_function

import logging
import os
import sys

sys.path.append('.')

from pykolab.translate import _

try:
    import pykolab.logger
except ImportError, e:
    print(_("Cannot load pykolab/logger.py:"), file=sys.stderr)
    print("%s" % e, file=sys.stderr)
    sys.exit(1)

import pykolab

if __name__ == "__main__":
    pykolab = pykolab.Conf()
    pykolab.finalize_conf()
    pykolab.run()
