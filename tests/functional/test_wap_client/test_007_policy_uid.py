from ConfigParser import RawConfigParser
import time
import unittest

import pykolab
from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP

conf = pykolab.getConf()

class TestPolicyUid(unittest.TestCase):

    def remove_option(self, section, option):
        self.config.remove_option(section, option)

        fp = open(conf.config_file, "w")
        self.config.write(fp)
        fp.close()

    def set(self, section, option, value):
        self.config.set(section, option, value)

        fp = open(conf.config_file, "w")
        self.config.write(fp)
        fp.close()

    @classmethod
    def setup_class(self, *args, **kw):
        self.config = RawConfigParser()
        self.config.read(conf.config_file)

        from tests.functional.purge_users import purge_users
        purge_users()

        self.user = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

        self.login = conf.get('ldap', 'bind_dn')
        self.password = conf.get('ldap', 'bind_pw')
        self.domain = conf.get('kolab', 'primary_domain')

        result = wap_client.authenticate(self.login, self.password, self.domain)

    @classmethod
    def teardown_class(self, *args, **kw):
        self.config.remove_option('example.org', 'policy_uid')

        fp = open(conf.config_file, "w")
        self.config.write(fp)
        fp.close()

        from tests.functional.purge_users import purge_users
        purge_users()

    def test_001_default(self):
        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        auth = Auth()
        auth.connect()

        user = auth.find_recipient('john.doe@example.org')

        user_info = wap_client.user_info(user)

        self.assertEqual(user_info['uid'], "doe")

        from tests.functional.purge_users import purge_users
        purge_users()

    def test_002_givenname_dot_surname(self):
        self.set('example.org', 'policy_uid', '%(givenname)s.%(surname)s')

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        auth = Auth()
        auth.connect()

        user = auth.find_recipient('john.doe@example.org')

        user_info = wap_client.user_info(user)

        self.assertEqual(user_info['uid'], "John.Doe")

        from tests.functional.purge_users import purge_users
        purge_users()

    def test_003_givenname_fc_dot_surname(self):
        self.set('example.org', 'policy_uid', "'%(givenname)s'[0:1].%(surname)s")

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        auth = Auth()
        auth.connect()

        user = auth.find_recipient('john.doe@example.org')

        user_info = wap_client.user_info(user)

        self.assertEqual(user_info['uid'], "J.Doe")

        from tests.functional.purge_users import purge_users
        purge_users()

    def test_004_givenname(self):
        self.set('example.org', 'policy_uid', '%(givenname)s')

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        auth = Auth()
        auth.connect()

        user = auth.find_recipient('john.doe@example.org')

        user_info = wap_client.user_info(user)

        self.assertEqual(user_info['uid'], "John")

        from tests.functional.purge_users import purge_users
        purge_users()

    def test_005_lowercase_givenname(self):
        self.set('example.org', 'policy_uid', '%(givenname)s.lower()')

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        auth = Auth()
        auth.connect()

        user = auth.find_recipient('john.doe@example.org')

        user_info = wap_client.user_info(user)

        self.assertEqual(user_info['uid'], "john")

        from tests.functional.purge_users import purge_users
        purge_users()

    def test_006_lowercase_givenname_surname(self):
        self.set('example.org', 'policy_uid', "%(givenname)s.lower().%(surname)s.lower()")

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        auth = Auth()
        auth.connect()

        user = auth.find_recipient('john.doe@example.org')

        user_info = wap_client.user_info(user)

        self.assertEqual(user_info['uid'], "john.doe")

        from tests.functional.purge_users import purge_users
        purge_users()


