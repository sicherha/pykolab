#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
"""
    Kolab configuration utility.
"""


import logging
import os
import sys

sys.path.append('.')

from pykolab.translate import _

try:
    import pykolab.logger
except ImportError, e:
    print >> sys.stderr, _("Cannot load pykolab/logger.py:")
    print >> sys.stderr, "%s" % e
    sys.exit(1)

import pykolab

if __name__ == "__main__":
    pykolab = pykolab.Conf()
    pykolab.finalize_conf()
    pykolab.run()

