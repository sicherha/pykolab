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

import datetime
import os
import random
import time

TEST_ALPHABET = ""
for num in range(33,256):
    TEST_ALPHABET = "%s%s" %(TEST_ALPHABET,unichr(num))

TEST_ITEMS = [
        {
                'name': 'calendar',
                'mailbox': 'Calendar',
                'template': 'kcal-event.tpl',
                'number': 10000,
                # 6 years ago
                'calendar_start': "%d" %(time.time() - (60*60*24*365*6)),
                # 4 years forward
                'calendar_end': "%d" %(time.time() - (60*60*24*365*6)),
            },
        #{
                #'name': 'contacts',
                #'mailbox': 'Contacts',
                #'template': 'kaddress-contact.tpl',
                #'number': 1000,
            #},
    ]

TEST_USERS = [
        #{
                #'givenname': 'john',
                #'sn': 'doe',
                #'domain': 'doe.org'
            #},
        {
                'givenname': 'joe',
                'sn': 'sixpack',
                'domain': 'sixpack.com'
            },
        #{
                #'givenname': 'max',
                #'sn': 'sixpack',
                #'domain': 'sixpack.com'
            #},
        #{
                #'givenname': 'min',
                #'sn': 'sixpack',
                #'domain': 'sixpack.com'
            #},
        #{
                #'givenname': 'joe',
                #'sn': 'imum',
                #'domain': 'imum.net'
            #},
        {
                'givenname': 'max',
                'sn': 'imum',
                'domain': 'imum.net'
            },
        #{
                #'givenname': 'min',
                #'sn': 'imum',
                #'domain': 'imum.net'
            #},
    ]

