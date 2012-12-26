import time
import unittest

import pykolab
from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP

conf = pykolab.getConf()

class TestKolabDaemon(unittest.TestCase):
    @classmethod
    def setup_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

        self.user = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        time.sleep(5)

    @classmethod
    def teardown_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

    def test_001_user_rename(self):
        """
            Rename user "Doe, John" to "Sixpack, Joe" and verify the recipient
            policy is applied, and the IMAP INBOX folder for the user is
            renamed.
        """
        imap = IMAP()
        imap.connect()
        folders = imap.lm('user/john.doe@example.org')
        self.assertEqual(len(folders), 1)

        auth = Auth()
        auth.connect()
        recipient = auth.find_recipient("%(local)s@%(domain)s" % (self.user))

        user_info = wap_client.user_info(recipient)
        user_info['sn'] = 'Sixpack'
        user_info['givenname'] = 'Joe'
        user_info['uid'] = 'sixpack'
        user_edit = wap_client.user_edit(recipient, user_info)

        time.sleep(5)

        user_info = wap_client.user_info('uid=sixpack,ou=People,dc=example,dc=org')
        self.assertEqual(user_info['mail'], 'joe.sixpack@example.org')

        folders = imap.lm('user/john.doe@example.org')
        self.assertEqual(len(folders), 0)

        folders = imap.lm('user/joe.sixpack@example.org')
        self.assertEqual(len(folders), 1)

