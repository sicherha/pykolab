# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
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

from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.tests.constants import *
from pykolab.translate import _

class Test_000_001(object):
    """
        First, basic test.

        Populate the previously created and existing INBOX, Calendar and Contact
        folders with a limited amount of data.
    """

    def __init__(self, conf):
        self.suite_num = "000"
        self.suite_test_num = "001"

        if not conf:
            self.conf = Conf()
            self.conf.finalize_conf()
        else:
            self.conf = conf

        # Create some test calendar items
        for item in TEST_ITEMS:
            try:
                exec("from pykolab.tests.%s import %sItem, create_items as create_%s_items" %(item['name'],item['name'].capitalize(),item['name']))
            except ImportError, e:
                self.conf.log.warning(_("Could not load %sItem from %s, skipping the testing.") %(item['name'].capitalize(),item['name']))
                continue

            self.conf.log.debug("self.conf.%s = %r" %(item['name'], getattr(self.conf, "%s" %(item['name']))), level=9)

            if getattr(self.conf, "%s" %(item['name'])):
                exec("create_%s_items(self.conf, num=%d)" %(item['name'],item['number']))
            else:
                self.conf.log.info("not executing %s" %(item['name'].capitalize()))
