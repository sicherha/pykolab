#!/usr/bin/python -tt
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

import logging
import os
import sys

# For development purposes
sys.path.extend(['.', '..'])

from pykolab.translate import _
from pykolab import constants
from pykolab import utils

try:
    import pykolab.logger
except ImportError, e:
    print >> sys.stderr, _("Cannot load pykolab/logger.py:")
    print >> sys.stderr, "%s" % e
    sys.exit(1)

def load_setup(component):
    """
        Load a setup component.

        Accepts one of the components listed in constants.COMPONENTS.
    """

    try:
        exec("from pykolab.setup import %s_setup" % component)
        try:
            exec("%s_setup()" % component)
        except NameError, e:
            print >> sys.stderr, _("Cannot find %s_setup().") % component
    except ImportError, e:
        print >> sys.stderr, _("Cannot load setup for %s.") % component

if __name__ == "__main__":
    # Means we get to ask some questions.
    print _("Please select the components to set up:")

    component_index = 1
    for component in constants.COMPONENTS:
        print "%d) %s" %(component_index,component)
        component_index += 1

    _input_selected_components = raw_input(_("Selection") + ": ")
    selected_components = utils.parse_input(_input_selected_components, [ ' ', ',' ])

    # Using the components in the selection dialog, we now go ahead with the real
    # work:
    component_index = 1
    for component in constants.COMPONENTS:
        if selected_components.count("%s" %(component_index)):
            load_setup(component)
        component_index += 1
