# -*- coding: utf-8 -*-
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

import cyruslib
import datetime
import os
import random
import time

from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.tests.constants import *
from pykolab.translate import _

class Tests(object):
    def __init__(self):
        self.conf = Conf()

        test_group = self.conf.parser.add_option_group(_("Test Options"))

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

        delivery_group = self.conf.parser.add_option_group(_("Content Delivery Options"))

        delivery_group.add_option(  "--use-mail",
                                    dest    = "use_mail",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Send messages containing the items through mail (requires proper infrastructure)"))

        delivery_group.add_option(  "--use-imap",
                                    dest    = "use_imap",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Inject messages containing the items through IMAP (requires imaplib)"))

        delivery_group.add_option(  "--use-lmtp",
                                    dest    = "use_lmtp",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Deliver messages containing the items through LMTP (requires imaplib)"))

        self.conf.finalize_conf()

    def run(self):
        # Execute the suites first.
        for suite in self.conf.test_suites:
            try:
                exec("from pykolab.tests.%s import %sTest" %(suite,suite.capitalize()))
                exec("%stest = %sTest(self.conf)" %(suite,suite.capitalize()))
            except ImportError, e:
                self.conf.log.error(_("Tests for suite %s failed to load. Aborting.") %(suite.capitalize()), recoverable=False)
