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

from pykolab.conf import Defaults, Runtime
import pykolab.conf

class Tests(object):
    def __init__(self):
        print "yeah i'm here"

    def run(self):
        print "and now i start running"

        # Create 3 users, john, joe and max
        # Create the default groupware folders for each user
        # Mark each of them as groupware folders (annotations, in python, how?)
        # Generate a lot of content for each folder

        event_tpl_file = open('./pykolab/tests/kcal-event.tpl', 'r')
        event_tpl_orig = event_tpl_file.read()
        event_tpl_file.close()

        users = [ 'john', 'joe', 'max' ]
        domains = [ 'doe.org', 'sixpack.com', 'imum.net' ]

        mydate = datetime.date(1111, 11, 11).today()

        this_month = mydate.month

        uids_alloc = []

        for user in users:
            # Each of the users gets 500 events
            num = 1
            while num < 501:
                uid = "%s.%s" %(str(random.randint(1000000000,9999999999)),str(random.randint(0,999)).zfill(3))
                if not uid in uids_alloc:
                    uids_alloc.append(uid)
                else:
                    continue

                success = False
                while not success:
                    try:
                        myday = mydate.replace(day=random.randint(1,31))
                        success = True
                    except:
                        success = False

                event_tpl = event_tpl_orig

                domain = domains[random.randint(0,2)]

                time_start = random.randint(0,21)
                time_end = time_start + 2

                time_start = str(time_start).zfill(2)
                time_end = str(time_end).zfill(2)

                event = {
                    'uid': uid,
                    'user': user,
                    'user_email': "%s@%s" %(user,domain),
                    'date_start': "2010-%s-%s" %(this_month,str(myday).zfill(2)),
                    'date_end': "2010-%s-%s" %(this_month,str(myday).zfill(2)),
                    'time_start': time_start,
                    'time_end': time_end
                }

                if num % 100 == 0:
                    print "User %s calendaring events %s done" %(user,num)
                    event['recurrence'] = """<recurrence cycle="weekly">
  <interval>1</interval>
  <day>thursday</day>
  <range type="none"></range>
 </recurrence>"""
                else:
                    event['recurrence'] = ""

                directory = "/kolab/var/imapd/spool/domains/t/test90.kolabsys.com/%s/user/%s/Calendar" %(user[0],user)
                if not os.path.isdir(directory):
                    directory = "./kolab/var/imapd/spool/domains/t/test90.kolabsys.com/%s/user/%s/Calendar" %(user[0],user)
                    if not os.path.isdir(directory):
                        os.makedirs(directory)

                out = open("%s/%d." %(directory,num), 'w')

                for key in event.keys():
                    event_tpl = event_tpl.replace("@@%s@@" % key, '%s' % event[key])

                out.write(event_tpl)
                out.close()
                try:
                    os.chown("%s/%d." %(directory,num), 19415, 19415)
                except:
                    pass
                num += 1
