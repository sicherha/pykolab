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

import cyruslib
import datetime
import os
import random
import time

import pykolab

from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.tests')
conf = pykolab.getConf()

class Tests(object):
    def __init__(self):
        import tests
        tests.__init__()

        test_group = conf.add_cli_parser_option_group(_("Test Options"))

        test_group.add_option(  "--suite",
                                dest    = "test_suites",
                                action  = "append",
                                default = [],
                                help    = _("Run tests in suite SUITE. Implies a certain set of items being tested."),
                                metavar = "SUITE")

        conf.finalize_conf()

    def run(self):
        if len(conf.test_suites) > 0:
            for test_suite in conf.test_suites:
                print test_suite
        else:
            to_execute = []

            arg_num = 0
            for arg in sys.argv[1:]:
                print "arg", arg
                arg_num += 1
                if not arg.startswith('-') and len(sys.argv) >= arg_num:
                    if tests.tests.has_key(sys.argv[arg_num].replace('-','_')):
                        print "tests.tests.has_key", sys.argv[arg_num].replace('-','_')
                        to_execute.append(sys.argv[arg_num].replace('-','_'))

            print "to_execute", to_execute
            if len(to_execute) > 0:
                print "'_'.join(to_execute)", '_'.join(to_execute)
                tests.execute('_'.join(to_execute))
            else:
                tests.execute('help')

