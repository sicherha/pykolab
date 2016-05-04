import unittest


class TestLDAPPsearch(unittest.TestCase):

    def test_001_import_psearch(self):
        from ldap.controls import psearch

