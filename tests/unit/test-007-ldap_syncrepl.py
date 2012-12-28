import unittest

class TestLDAPSyncrepl(unittest.TestCase):

    def test_001_import_syncrepl(self):
        from ldap import syncrepl

