import time
import unittest

import pykolab
from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP

conf = pykolab.getConf()


class TestUserAdd(unittest.TestCase):

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

    def test_002_autocreate_folders_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        exec("ac_folders = %s" % (conf.get_raw(conf.get('kolab', 'primary_domain'), 'autocreate_folders')))

        folders = imap.lm('user/%(local)s/*@%(domain)s' % (self.user))

        print folders
        print ac_folders.keys()

        self.assertEqual(len(folders), len(ac_folders.keys()))

    def test_003_folders_metadata_set(self):
        imap = IMAP()
        imap.connect()

        exec("ac_folders = %s" % (conf.get_raw(conf.get('kolab', 'primary_domain'), 'autocreate_folders')))

        folders = []
        folders.extend(imap.lm('user/%(local)s@%(domain)s' % (self.user)))
        folders.extend(imap.lm('user/%(local)s/*@%(domain)s' % (self.user)))

        for folder in folders:
            metadata = imap.get_metadata(folder)

            folder_name = '/'.join(folder.split('/')[2:]).split('@')[0]
            if folder_name in ac_folders:
                if 'annotations' in ac_folders[folder_name]:
                    for _annotation in ac_folders[folder_name]['annotations']:
                        if _annotation.startswith('/private/'):
                            continue

                        _annotation_value = ac_folders[folder_name]['annotations'][_annotation]
                        self.assertTrue(_annotation in metadata[metadata.keys().pop()])
                        self.assertEqual(_annotation_value, metadata[metadata.keys().pop()][_annotation])
