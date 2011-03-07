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

import imp
import os
import sys

import pykolab.logger

from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.tests.constants import *

class ZpushTest(object):
    def __init__(self, conf=None):
        if conf:
            self.conf = conf
        else:
            self.conf = Conf()
            self.conf.finalize_conf()

        self.tests = []

        # Make sure we parse the [testing] section of the configuration file, if
        # available.
        self.conf.set_options_from_testing_section()

        # Attempt to create a list of modules
        for x in range(0,8):
            for y in range(0,8):
                test_num = "%s_%s" %(str(x).zfill(3),str(y).zfill(3))
                try:
                    exec("from test_%s import Test_%s" %(test_num,test_num))
                    self.tests.append("Test_%s" %(test_num))
                except ImportError, e:
                    pass

        for test in self.tests:
            exec("result = %s(self.conf)" %(test))

        #name = "from pykolab.tests.zpush.test_%s import Test_%s" %(test_num,test_num)
        #file, pathname, description = imp.find_module(name, sys.path)

        #try:
            #plugin = imp.load_module(mod_name, file, pathname, description)
        #finally:
            #file.close()
        #plugins[name] = plugin

#print plugins
