# -*- coding: utf-8 -*-

import time
import unittest

import pykolab
from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP

conf = pykolab.getConf()


class TestUserAddEsES(unittest.TestCase):

    @classmethod
    def setup_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

        self.user = {
                'local': 'alvaro.fuentes',
                'domain': 'example.org'
            }

        from tests.functional.user_add import user_add
        user_add("Álvaro", "Fuentes", 'es_ES')
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    @classmethod
    def teardown_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

    def test_001_inbox_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/%(local)s@%(domain)s' % (self.user))
        self.assertEqual(len(folders), 1)

    def test_002_fr_FR_user_recipient_policy(self):
        auth = Auth()
        auth.connect()
        recipient = auth.find_recipient("%(local)s@%(domain)s" % (self.user))
        if hasattr(self, 'assertIsInstance'):
            self.assertIsInstance(recipient, str)

        self.assertEqual(recipient, "uid=fuentes,ou=People,dc=example,dc=org")

        result = wap_client.user_info(recipient)

        self.assertEqual(result['mail'], 'alvaro.fuentes@example.org')
        self.assertEqual(sorted(result['alias']), ['a.fuentes@example.org', 'fuentes@example.org'])
