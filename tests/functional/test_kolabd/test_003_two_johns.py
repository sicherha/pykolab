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

    @classmethod
    def teardown_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

    def test_001_two_johns(self):
        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        user_add("John", "Doe")

        time.sleep(3)

        auth = Auth()
        auth.connect()

        max_tries = 20
        while max_tries > 0:
            recipient1 = auth.find_recipient('john.doe@example.org')
            recipient2 = auth.find_recipient('john.doe2@example.org')

            if not recipient1 or not recipient2:
                time.sleep(1)
                max_tries -= 1
            else:
                break

        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/john.doe@example.org')
        self.assertEqual(len(folders), 1, "No INBOX found for first John")

        folders = imap.lm('user/john.doe2@example.org')
        self.assertEqual(len(folders), 1, "No INBOX found for second John")
