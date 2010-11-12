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

import calendar
import datetime
import mailbox
import os
import random
import time

from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.tests.constants import *
from pykolab.translate import _

class MailItem(object):
    def __init__(self, item_num=0, total_num=1, folder=None, user=None):
        """
            A mail item is created from a template.

            The attributes that can be modified are set to defaults first.
        """

        if user == None:
            user = TEST_USERS[random.randint(0,(len(TEST_USERS)-1))]

        # Used for some randomization
        self.item_num = item_num
        self.total_num = total_num

        # Initial event data
        self.kolab_contact_given_name = "John"
        self.kolab_contact_last_name = "von Test"
        self.kolab_contact_email_str = "john@von.test"
        self.kolab_contact_mobile_number = "+31612345678"

        from_user = TEST_USERS[random.randint(0,(len(TEST_USERS)-1))]

        self.from_name_str = "%s %s" %(from_user['givenname'].capitalize(),from_user['sn'].capitalize())
        self.from_email_str = "%(givenname)s@%(domain)s" %(from_user)

        self.kolab_creation_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self.rfc_2822_sent_date = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())

        self.to_name_str = "%s %s" %(user['givenname'].capitalize(),user['sn'].capitalize())
        self.to_email_str = "%(givenname)s@%(domain)s" %(user)

        self.uid = "%s.%s" %(str(random.randint(1000000000,9999999999)),str(random.randint(0,999)).zfill(3))

        if folder:
            self.mailbox = folder
        else:
            self.mailbox = "INBOX"

        self.randomize_mail()

    def randomize_mail(self):
        """
            Randomize some of the contents of the mail.
        """

        pass

    def __str__(self):
        return ""

def create_items(conf, num=None, folder=None):
    for item in TEST_ITEMS:
        if item['name'] == 'mail':
            info = item

    if num:
        info['number'] = int(num)

    conf.log.debug(_("Creating %d Mails") %(info['number']), level=3)

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

        mb = mailbox.mbox('./share/tests/mail/lists.fedoraproject.org/devel/2010-September.txt')
        for key in mb.keys():

            msg = mb.get_string(key)

            if conf.use_mail:
                conf.log.debug(_("Sending message %s through SMTP targeting user %s@%s") %(key,user['givenname'],user['domain']), level=9)

            elif conf.use_lmtp:
                conf.log.debug(_("Sending message %s through LMTP targeting user %s@%s") %(key,user['givenname'],user['domain']), level=9)

            elif conf.use_imap:
                conf.log.debug(_("Saving message %s to IMAP (user %s, folder %s)") %(key,user['givenname'],"INBOX"), level=9)
                imap.append("INBOX", '', imaplib.Time2Internaldate(time.time()), msg)
            else:
                conf.log.debug(_("Somehow ended up NOT sending these messages"), level=9)
