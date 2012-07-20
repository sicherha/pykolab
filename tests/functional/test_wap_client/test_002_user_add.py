import time
import unittest

import pykolab
from pykolab import wap_client
from pykolab.imap import IMAP

conf = pykolab.getConf()

class TestUserAdd(unittest.TestCase):
    @classmethod
    def setup_class(self, *args, **kw):
        conf.finalize_conf(fatal=False)

        self.login = conf.get('ldap', 'bind_dn')
        self.password = conf.get('ldap', 'bind_pw')
        self.domain = conf.get('kolab', 'primary_domain')

        self.user = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

        from tests.functional.user_add import user_add
        user_add("John", "Doe")

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

    def test_003_folder_types_set(self):
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

    @classmethod
    def teardown_class(self):
        time.sleep(2)

        res_attr = conf.get('cyrus-sasl', 'result_attribute')

        exec("ac_folders = %s" % (conf.get_raw(conf.get('kolab', 'primary_domain'), 'autocreate_folders')))
        expected_number_of_folders = len(ac_folders.keys()) + 1

        users = []

        result = wap_client.users_list()
        for user in result['list'].keys():
            user_info = wap_client.user_info(user)
            users.append(user_info)
            result = wap_client.user_delete({'user': user})

        imap = IMAP()
        imap.connect()

        for user in users:
            if len(user[res_attr].split('@')) > 1:
                localpart = user[res_attr].split('@')[0]
                domain = user[res_attr].split('@')[1]

            folders = []
            folders.extend(imap.lm('user/%s' % (user[res_attr])))
            folders.extend(imap.lm('user/%s/*@%s' % (localpart,domain)))

            # Expect folders length to be 0

