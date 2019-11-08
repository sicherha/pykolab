import unittest

from pykolab import utils


class TestParseLdapUri(unittest.TestCase):

    def test_001_ldap_uri(self):
        ldap_uri = "ldap://localhost"
        result = utils.parse_ldap_uri(ldap_uri)
        self.assertEqual(result, ("ldap", "localhost", "389", None, [None], None, None))

    def test_002_ldap_uri_port(self):
        ldap_uri = "ldap://localhost:389"
        result = utils.parse_ldap_uri(ldap_uri)
        self.assertEqual(result, ("ldap", "localhost", "389", None, [None], None, None))
