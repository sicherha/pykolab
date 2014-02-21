import time
import pykolab

from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP
from wallace import module_resources
from twisted.trial import unittest

import tests.functional.resource_func as funcs

conf = pykolab.getConf()

class TestResourceAdd(unittest.TestCase):

    @classmethod
    def setUp(self):
        from tests.functional.purge_users import purge_users
        #purge_users()

        self.john = {
            'local': 'john.doe',
            'domain': 'example.org'
        }

        from tests.functional.user_add import user_add
        #user_add("John", "Doe")

        funcs.purge_resources()
        self.audi = funcs.resource_add("car", "Audi A4")
        self.passat = funcs.resource_add("car", "VW Passat")
        self.boxter = funcs.resource_add("car", "Porsche Boxter S")
        self.cars = funcs.resource_add("collection", "Company Cars", [ self.audi['dn'], self.passat['dn'], self.boxter['dn'] ])

        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    @classmethod
    def tearDown(self):
        from tests.functional.purge_users import purge_users
        #funcs.purge_resources()
        #purge_users()

    def test_001_resource_created(self):
        resource = module_resources.resource_record_from_email_address(self.audi['mail'])
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0], self.audi['dn'])

        collection = module_resources.resource_record_from_email_address(self.cars['mail'])
        self.assertEqual(len(collection), 1)
        self.assertEqual(collection[0], self.cars['dn'])

    def test_002_resource_collection(self):
        auth = Auth()
        auth.connect()
        attrs = auth.get_entry_attributes(None, self.cars['dn'], ['*'])
        self.assertIn('groupofuniquenames', attrs['objectclass'])
        self.assertEqual(len(attrs['uniquemember']), 3)
