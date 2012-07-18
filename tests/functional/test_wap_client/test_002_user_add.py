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

        self.user_details = {
                'givenname': "John",
                'sn': "Doe",
                'preferredlanguage': 'en_US',
                'ou': 'ou=People,dc=example,dc=org',
                'userpassword': 'Welcome2KolabSystems'
            }

        self.user = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

    def test_001_user_add(self):
        user_type_id = 0

        result = wap_client.authenticate(self.login, self.password, self.domain)

        user_types = wap_client.user_types_list()

        for key in user_types['list'].keys():
            if user_types['list'][key]['key'] == 'kolab':
                user_type_id = key

        self.assertTrue(user_type_id > 0, "No 'kolab' user type found")

        user_type_info = user_types['list'][user_type_id]['attributes']

        params = {
                'user_type_id': user_type_id,
            }

        for attribute in user_type_info['form_fields'].keys():
            attr_details = user_type_info['form_fields'][attribute]

            if isinstance(attr_details, dict):
                if not attr_details.has_key('optional') or attr_details['optional'] == False:
                    self.assertTrue(self.user_details.has_key(attribute), "No attribute %r in user details" % (attribute))
                    params[attribute] = self.user_details[attribute]
            elif isinstance(attr_details, list):
                self.assertTrue(self.user_details.has_key(attribute), "No attribute %r in user details" % (attribute))
                params[attribute] = self.user_details[attribute]
                
        fvg_params = params
        fvg_params['object_type'] = 'user'
        fvg_params['type_id'] = user_type_id
        fvg_params['attributes'] = [attr for attr in user_type_info['auto_form_fields'].keys() if not attr in params.keys()]

        exec("retval = wap_client.form_value_generate(%r)" % (params))

        for attribute in user_type_info['auto_form_fields'].keys():
            params[attribute] = retval[attribute]

        result = wap_client.user_add(params)

    def test_003_inbox_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/%(local)s@%(domain)s' % (self.user))
        self.assertEqual(len(folders), 1)

    def test_004_autocreate_folders_created(self):
        time.sleep(2)
        imap = IMAP()
        imap.connect()

        exec("ac_folders = %s" % (conf.get_raw(conf.get('kolab', 'primary_domain'), 'autocreate_folders')))

        folders = imap.lm('user/%(local)s/*@%(domain)s' % (self.user))

        print folders
        print ac_folders.keys()

        self.assertEqual(len(folders), len(ac_folders.keys()))

    def test_005_folder_types_set(self):
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

