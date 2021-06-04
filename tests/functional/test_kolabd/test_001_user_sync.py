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

    @classmethod
    def teardown_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

    def test_001_user_recipient_policy(self):
        auth = Auth()
        auth.connect()
        recipient = auth.find_recipient("%(local)s@%(domain)s" % (self.user))
        if hasattr(self, 'assertIsInstance'):
            self.assertIsInstance(recipient, str)

        self.assertEqual(recipient, "uid=doe,ou=People,dc=example,dc=org")

        result = wap_client.user_info(recipient)

        self.assertEqual(result['mail'], 'john.doe@example.org')
        self.assertEqual(result['alias'], ['doe@example.org', 'j.doe@example.org'])

    def test_002_user_recipient_policy_duplicate(self):
        from tests.functional.user_add import user_add
        user = {
                'local': 'jane.doe',
                'domain': 'example.org'
            }
        user_add("Jane", "Doe")

        time.sleep(3)

        auth = Auth()
        auth.connect()
        recipient = auth.find_recipient("%(local)s@%(domain)s" % (user))
        if hasattr(self, 'assertIsInstance'):
            self.assertIsInstance(recipient, str)

        self.assertEqual(recipient, "uid=doe2,ou=People,dc=example,dc=org")

        result = wap_client.user_info(recipient)

        if 'mailhost' not in result:
            from tests.functional.synchronize import synchronize_once
            synchronize_once()

        result = wap_client.user_info(recipient)

        self.assertEqual(result['mail'], 'jane.doe@example.org')
        self.assertEqual(result['alias'], ['doe2@example.org', 'j.doe2@example.org'])

    def test_003_user_mailbox_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/%(local)s@%(domain)s' % (self.user))
        self.assertEqual(len(folders), 1)

    def test_004_user_additional_folders_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        ac_folders = conf.get_raw('kolab', 'autocreate_folders')
        exec("ac_folders = %s" % (ac_folders))

        folders = imap.lm('user/%(local)s/*@%(domain)s' % (self.user))

        self.assertEqual(len(folders), len(ac_folders.keys()))

    def test_005_user_folders_metadata_set(self):
        imap = IMAP()
        imap.connect()

        ac_folders = conf.get_raw('kolab', 'autocreate_folders')
        exec("ac_folders = %s" % (ac_folders))

        folders = []
        folders.extend(imap.lm('user/%(local)s@%(domain)s' % (self.user)))
        folders.extend(imap.lm('user/%(local)s/*@%(domain)s' % (self.user)))

        for folder in folders:
            metadata = imap.get_metadata(folder)
            print(metadata)

            folder_name = '/'.join(folder.split('/')[2:]).split('@')[0]
            if folder_name in ac_folders:
                if 'annotations' in ac_folders[folder_name]:
                    for _annotation in ac_folders[folder_name]['annotations'].keys():
                        if _annotation.startswith('/private'):
                            continue

                        _annotation_value = ac_folders[folder_name]['annotations'][_annotation]
                        self.assertTrue(_annotation in metadata[metadata.keys().pop()])
                        self.assertEqual(_annotation_value, metadata[metadata.keys().pop()][_annotation])

    def test_006_user_subscriptions(self):
        imap = IMAP()
        imap.connect(login=False)
        login = conf.get('cyrus-imap', 'admin_login')
        password = conf.get('cyrus-imap', 'admin_password')
        imap.login_plain(login, password, 'john.doe@example.org')

        folders = imap.lm()
        self.assertTrue("INBOX" in folders)

        folders = imap.imap.lsub()
        self.assertTrue("Calendar" in folders)

    def test_011_resource_add(self):
        pass

    def test_012_resource_mailbox_created(self):
        pass

    def test_013_resource_mailbox_annotation(self):
        pass
