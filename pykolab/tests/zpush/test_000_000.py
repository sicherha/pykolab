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

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.tests.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.tests.zpush')
conf = pykolab.getConf()

class Test_000_000(object):
    """
        Preparations for the Test 000 series.
    """

    def __init__(self, conf=None):
        self.suite_num = "000"
        self.suite_test_num = "000"

        log.info("About to execute preperation task #000 in Test Suite #000");
        log.info("We will assume the start situation has been configured");
        log.info("such as is described in the documentation.");

        utils.ask_confirmation("Continue?")

        # Delete all mailboxes
        #imap.connect()
        #for folder in imap.lm("user/%"):
            #imap.dm(folder)

        for user in auth.list_users(domain):
            for mailbox in imap.lm("user%s%s" %(imap.SEP,"%(givenname)s@%(domain)s" %(user))):
                log.debug(_("Deleting mailbox: %s") %(mailbox), level=3)
                try:
                    imap.dm(mailbox)
                except cyruslib.CYRUSError, e:
                    pass

        # Recreate the user top-level mailboxes
        for user in conf.testing_users:
            mailbox = "user%s%s" %(imap.SEP,"%(givenname)s@%(domain)s" %(user))
            log.debug(_("Creating mailbox: %s") %(mailbox), level=3)
            imap.cm(mailbox)

        imap.logout()

        del imap

        # Have the user themselves:
        # - create the standard folders
        # - set the standard annotations
        # - subscribe
        for user in conf.testing_users:
            imap = cyruslib.CYRUS("imap://%s:143" %(conf.testing_server))
            try:
                imap.login("%(givenname)s@%(domain)s" %(user), user['password'])
            except:
                log.error(_("Authentication failure for %s") %("%(givenname)s@%(domain)s" %(user)), recoverable=True)
                continue

            if conf.debuglevel > 3:
                imap.VERBOSE = True

            imap.subscribe("INBOX")

            for mailbox in TEST_FOLDERS.keys():
                imap.cm("INBOX/%s" %(mailbox))
                for annotation in TEST_FOLDERS[mailbox]['annotations'].keys():
                    imap.setannotation("INBOX/%s" %(mailbox),annotation,TEST_FOLDERS[mailbox]['annotations'][annotation])

            imap.subscribe("INBOX/%s" %(mailbox))

            imap.logout()
            del imap