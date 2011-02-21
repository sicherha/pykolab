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

import cyruslib

from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.tests.constants import *
from pykolab.translate import _

TEST_FOLDERS = {
        'Calendar': {
                'annotations': {
                        "/vendor/kolab/folder-test": "true",
                        "/vendor/kolab/folder-type": "event.default"
                    },
                'acls': [
                    ],
            },

        'Contacts': {
                'annotations': {
                        "/vendor/kolab/folder-type": "contact.default"
                    },
                'acls': [
                    ],
            },

        'Journal': {
                'annotations': {
                        "/vendor/kolab/folder-test": "true",
                        "/vendor/kolab/folder-type": "journal.default"
                    },
                'acls': [
                    ],
            },
        'Notes': {
                'annotations': {
                        "/vendor/kolab/folder-type": "note.default"
                    },
                'acls': [
                    ],
            },
        'Tasks': {
                'annotations': {
                        "/vendor/kolab/folder-type": "task.default"
                    },
                'acls': [
                    ],
            },
    }

class Test_000_000(object):
    """
        Preparations for the Test 000 series
    """

    def __init__(self, conf=None):
        self.suite_num = "000"
        self.suite_test_num = "000"

        self.log.info("About to execute preperation task #000 in Test Suite #000");
        self.log.info("We will assume the start situation has been configured");
        self.log.info("such as is described in the documentation");

        if not conf:
            self.conf = Conf()
            self.conf.finalize_conf()
        else:
            self.conf = conf

        # Remove all mailboxes
        # FIXME: Should come from configuration file and/or prompts
        imap = cyruslib.CYRUS("imap://%s:143" %(self.conf.testing_server))
        imap.login(self.conf.testing_admin_login,self.conf.testing_admin_password)

        # Delete all mailboxes
        for user in self.conf.testing_users:
            for mailbox in imap.lm("user%s%s" %(imap.SEP,"%(givenname)s@%(domain)s" %(user))):
                self.conf.log.debug(_("Deleting mailbox: %s") %(mailbox), level=3)
                try:
                    imap.dm(mailbox)
                except cyruslib.CYRUSError, e:
                    pass

        # Recreate the user top-level mailboxes
        for user in self.conf.testing_users:
            mailbox = "user%s%s" %(imap.SEP,"%(givenname)s@%(domain)s" %(user))
            self.conf.log.debug(_("Creating mailbox: %s") %(mailbox), level=3)
            imap.cm(mailbox)

        imap.logout()

        del imap

        # Have the user themselves:
        # - create the standard folders
        # - set the standard annotations
        # - subscribe
        for user in self.conf.testing_users:
            imap = cyruslib.CYRUS("imap://%s:143" %(self.conf.testing_server))
            try:
                imap.login("%(givenname)s@%(domain)s" %(user), user['password'])
            except:
                self.conf.log.error(_("Authentication failure for %s") %("%(givenname)s@%(domain)s" %(user)), recoverable=True)
                continue

            if self.conf.debuglevel > 3:
                imap.VERBOSE = True

            imap.subscribe("INBOX")

            for mailbox in TEST_FOLDERS.keys():
                imap.cm("INBOX/%s" %(mailbox))
                for annotation in TEST_FOLDERS[mailbox]['annotations'].keys():
                    imap.setannotation("INBOX/%s" %(mailbox),annotation,TEST_FOLDERS[mailbox]['annotations'][annotation])

            imap.subscribe("INBOX/%s" %(mailbox))

            imap.logout()
            del imap