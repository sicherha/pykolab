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
        self.user = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

        from tests.functional.user_add import user_add
        user_add("John", "Doe")

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

    def test_002_user_mailbox_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/%(local)s@%(domain)s' % (self.user))
        self.assertEqual(len(folders), 1)

    def test_003_user_additional_folders_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        exec("ac_folders = %s" % (conf.get_raw(conf.get('kolab', 'primary_domain'), 'autocreate_folders')))

        folders = imap.lm('user/%(local)s/*@%(domain)s' % (self.user))

        self.assertEqual(len(folders), len(ac_folders.keys()))

    def test_004_user_folder_annotations_set(self):
        imap = IMAP()
        imap.connect()

        exec("ac_folders = %s" % (conf.get_raw(conf.get('kolab', 'primary_domain'), 'autocreate_folders')))

        folders = []
        folders.extend(imap.lm('user/%(local)s@%(domain)s' % (self.user)))
        folders.extend(imap.lm('user/%(local)s/*@%(domain)s' % (self.user)))

        for folder in folders:
            annotation = imap.getannotation(folder)
            print annotation

            folder_name = '/'.join(folder.split('/')[2:]).split('@')[0]
            if ac_folders.has_key(folder_name):
                if ac_folders[folder_name].has_key('annotations'):
                    for _annotation in ac_folders[folder_name]['annotations'].keys():
                        _annotation_value = ac_folders[folder_name]['annotations'][_annotation]
                        self.assertTrue(annotation[annotation.keys().pop()].has_key(_annotation))
                        self.assertEqual(_annotation_value, annotation[annotation.keys().pop()][_annotation])

    def test_005_user_subscriptions(self):
        imap = IMAP()
        imap.connect(login=False)
        login = conf.get('cyrus-imap', 'admin_login')
        password = conf.get('cyrus-imap', 'admin_password')
        imap.login_plain(login, password, 'john.doe@example.org')

        folders = imap.lm()
        self.assertTrue("INBOX" in folders)

        #folders = imap.imap.lsub()
        #self.assertTrue("Calendar" in folders)

    def test_011_resource_add(self):
        pass

    def test_012_resource_mailbox_created(self):
        pass

    def test_013_resource_mailbox_annotation(self):
        pass

