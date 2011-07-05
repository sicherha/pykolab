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

import cyruslib
import datetime
import os
import random
import time

import pykolab

from pykolab.constants import *
from pykolab.tests.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.tests')
conf = pykolab.getConf()

class Tests(object):
    def __init__(self):

        test_group = conf.add_cli_parser_option_group(_("Test Options"))

        for item in TEST_ITEMS:
            test_group.add_option(  "--%s" %(item['name']),
                                    dest    = "%s" %(item['name']),
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Submit a number of items to the %s") %(item['mailbox']))

        test_group.add_option(  "--suite",
                                dest    = "test_suites",
                                action  = "append",
                                default = [],
                                help    = _("Run tests in suite SUITE. Implies a certain set of items being tested."),
                                metavar = "SUITE")

        delivery_group = conf.add_cli_parser_option_group(_("Content Delivery Options"))

        delivery_group.add_option(  "--use-mail",
                                    dest    = "use_mail",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Send messages containing the items through mail (requires proper infrastructure)"))

        delivery_group.add_option(  "--use-imap",
                                    dest    = "use_imap",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Inject messages containing the items through IMAP"))

        delivery_group.add_option(  "--use-lmtp",
                                    dest    = "use_lmtp",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Deliver messages containing the items through LMTP"))

        conf.finalize_conf()

    def run(self):
        # Execute the suites first.
        for suite in conf.test_suites:
            try:
                exec("from pykolab.tests.%s import %sTest" %(suite,suite.capitalize()))
                exec("%stest = %sTest()" %(suite,suite.capitalize()))
            except ImportError, e:
                conf.log.error(_("Tests for suite %s failed to load. Aborting.") %(suite.capitalize()))
