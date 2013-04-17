import time
import unittest

import pykolab
from pykolab import wap_client

conf = pykolab.getConf()

class TestFormValueListOptions(unittest.TestCase):

    def test_001_list_options_user_preferredlanguage(self):
        conf = pykolab.getConf()
        conf.finalize_conf(fatal=False)

        self.login = conf.get('ldap', 'bind_dn')
        self.password = conf.get('ldap', 'bind_pw')
        self.domain = conf.get('kolab', 'primary_domain')

        result = wap_client.authenticate(self.login, self.password, self.domain)

        attribute_values = wap_client.form_value_select_options(
                'user',
                1,
                'preferredlanguage'
            )

        self.assertTrue(attribute_values['preferredlanguage'].has_key('default'))
        self.assertTrue(attribute_values['preferredlanguage'].has_key('list'))
        self.assertTrue(len(attribute_values['preferredlanguage']['list']) > 1)
        self.assertTrue(attribute_values['preferredlanguage']['default'] in attribute_values['preferredlanguage']['list'])

