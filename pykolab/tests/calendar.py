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

import calendar
import datetime
import os
import random
import time

from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.tests.constants import *
from pykolab.translate import _

class CalendarItem(object):
    def __init__(self, item_num=0, total_num=1, start=0, end=0, folder=None, user=None):
        """
            A calendar item is created from a template.

            The attributes that can be modified are set to defaults first.
        """

        if user == None:
            user = TEST_USERS[random.randint(0,(len(TEST_USERS)-1))]

        # Used for some randomization
        self.item_num = item_num
        self.total_num = total_num
        self.event_boundary_start = int(start)
        self.event_boundary_end = int(end)

        # Initial event data
        self.event_location = "one or the other meeting room"
        self.event_recurrence = ""
        self.event_summary = "Test Event %d" %(item_num)

        from_user = TEST_USERS[random.randint(0,(len(TEST_USERS)-1))]
        self.from_name_str = "%s %s" %(from_user['givenname'].capitalize(),from_user['sn'].capitalize())
        self.from_email_str = "%(givenname)s@%(domain)s" %(from_user)
        self.kolab_event_date_creation = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.kolab_event_date_start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.kolab_event_date_end = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.rfc_2822_sent_date = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        self.to_name_str = "%s %s" %(user['givenname'].capitalize(),user['sn'].capitalize())
        self.to_email_str = "%(givenname)s@%(domain)s" %(user)

        self.uid = "%s.%s" %(str(random.randint(1000000000,9999999999)),str(random.randint(0,999)).zfill(3))

        if folder:
            self.mailbox = folder
        else:
            self.mailbox = "INBOX/Calendar"

        # Status information
        self.dates_randomized = False

        self.randomize_recurrence()
        self.randomize_dates()

    def randomize_dates(self):
        """
            Randomize all dates in the event but make sure they
            do make sense.

            Ergo, the start date is before the end date, and such.

            Also, take into account the total number of calendar items, so that
            we do not clutter.
        """

        if self.dates_randomized:
            return

        # The ratio is 1/2 goes to the past, 1/8 goes to this month, 3/8 goes to the future months.
        # Over 10.000 items, that is 5000 in the past -> 250 days a year, 4 appointments a day, 5 year
        #                           125 this month
        #                           4875 to future

        # We have two integers (epoch values), a start and an end
        mystart = random.randint(self.event_boundary_start,self.event_boundary_end)
        myend = mystart + (1800 * random.randint(1,4))

        self.kolab_event_date_start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mystart))
        self.kolab_event_date_end = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(myend))

        # Calculate the timespan we're serving assuming 4-6 appointments a day;
        self.dates_randomized = True

    def randomize_recurrence(self):
        """
            Randomize the recurrence of this event.

            One every so many events has recurrence.
        """
        return

        if not random.randint(1,15) == 1:
            return

        # The recurrence day (of the week)
        recur_day = random.randint(0,6)

#        # Seek a day somewhere in the past with this day_number
#        for days_in_week in calendar.itermonthdates():
#            # day_of_week is a list of weeks, where 0 is outside the month
#            # described in the call to calendar.itermonthdays(), and so
#            # we are able now to find the first day for this recurrence.
#            for day_date in days_in_week:
#                print day_date

        self.dates_randomized = True

    def __str__(self):
        for tpl_file_location in [ '/usr/share/kolab/tests/kcal-event.tpl', './share/tests/kcal-event.tpl' ]:
            if os.path.isfile(tpl_file_location):
                tpl_file = open(tpl_file_location, 'r')
                tpl_orig = tpl_file.read()
                tpl_file.close()
                break
        return tpl_orig % self.__dict__

def create_items(conf, num=None, folder=None):
    for item in TEST_ITEMS:
        if item['name'] == 'calendar':
            info = item

    if num:
        info['number'] = int(num)

    conf.log.debug(_("Creating %d Events") %(info['number']), level=3)

    alloc_uids = []

    if os.path.isfile('./share/tests/kcal-event.tpl'):
        tpl_file = open('./share/tests/kcal-event.tpl', 'r')
        tpl_orig = tpl_file.read()
        tpl_file.close()

    (start_boundary,end_boundary) = set_bounds(num=num)

    imap = True

    for user in conf.testing_users:
        if conf.use_mail:
            pass
        elif conf.use_lmtp:
            pass
        elif conf.use_imap:
            import imaplib
            if imap:
                del imap
            imap = imaplib.IMAP4(conf.testing_server)
            imap.login("%(givenname)s@%(domain)s" %(user), user['password'])
        else:
            pass

        #print "Running for user %(givenname)s@%(domain)s" %(user)
        item_num = 0

        while item_num < int(info['number']):
            conf.log.debug(_("Creating Calendar item number %d") %(item_num+1), level=5)

            item = CalendarItem(item_num=(item_num+1), total_num=num, start=start_boundary, end=end_boundary, folder=folder, user=user)

            if not item.uid in alloc_uids:
                alloc_uids.append(item.uid)
            else:
                continue

            msg = str(item)

            if conf.use_mail:
                conf.log.debug(_("Sending UID message %s through SMTP targeting user %s@%s") %(item.uid,user['givenname'],user['domain']), level=9)

            elif conf.use_lmtp:
                conf.log.debug(_("Sending UID message %s through LMTP targeting user %s@%s") %(item.uid,user['givenname'],user['domain']), level=9)

            elif conf.use_imap:
                conf.log.debug(_("Saving UID message %s to IMAP (user %s, folder %s)") %(item.uid,user['givenname'],item.mailbox), level=9)
                imap.append(item.mailbox, '', imaplib.Time2Internaldate(time.time()), msg)
            else:
                conf.log.debug(_("Somehow ended up NOT sending these messages"), level=9)

            item_num +=1

def set_bounds(num=0):
    """
        Set the lower and upper boundaries for this event, using the
        total number of events and a reasonable but random average number
        of appointments.

        returns a tuple epoch (start, end)
    """

    # Pretend anywhere between 0 and 5 events per workday,
    # Multiply by the number of workdays a week,
    # Divide that by 7 for a nice, float average.
    events_per_week_avg = float(random.randint(10,25))
    events_per_day_avg = events_per_week_avg / 7

    ratio = [ 6, 4 ]

    # Given the total number of events to be created, and the average number
    # of events per day, we can now look at what the lower boundary would be,
    # compared to today.
    days_to_go_back = (((num / events_per_day_avg) / 10 ) * ratio[0])
    days_to_go_forward = (((num / events_per_day_avg) / 10 ) * ratio[1])

    now = time.time()
    start_of_day = now - (now % (24 * 60 * 60))

    boundary_start = start_of_day - (days_to_go_back * 24 * 60 * 60)
    boundary_end = start_of_day + (days_to_go_forward * 24 * 60 * 60)

    return (boundary_start,boundary_end)
