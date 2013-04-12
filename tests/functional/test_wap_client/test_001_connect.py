import unittest

import pykolab
from pykolab import wap_client

class TestConnect(unittest.TestCase):
    @classmethod
    def setup_class(self, *args, **kw):
        conf = pykolab.getConf()
        conf.finalize_conf(fatal=False)

        self.login = conf.get('ldap', 'bind_dn')
        self.password = conf.get('ldap', 'bind_pw')
        self.domain = conf.get('kolab', 'primary_domain')

    def test_001_authenticate(self):
        result = wap_client.authenticate(self.login, self.password, self.domain)

    def test_002_response_ok(self):
        result = wap_client.request_raw('POST', 'domains.list')
        self.assertTrue(result.has_key('status'))
        self.assertTrue(result.has_key('result'))
        self.assertEqual(result['status'], "OK")

    def test_003_response_fail(self):
        result = wap_client.request_raw('POST', 'service.method')
        self.assertTrue(result.has_key('status'))
        self.assertTrue(result.has_key('reason'))
        self.assertTrue(result.has_key('code'))
        self.assertEqual(result['status'], "ERROR")
        self.assertEqual(result['reason'], "Unknown service")
        self.assertEqual(result['code'], 400)

    def test_004_domains_list(self):
        result = wap_client.domains_list()
        self.assertTrue(result.has_key('count'))
        self.assertTrue(result.has_key('list'))
        self.assertEqual(result['count'], len(result['list']))

    def test_005_get_domain(self):
        result = wap_client.request_raw('GET', 'system.get_domain')
        self.assertEqual(result, {u'status': u'OK', u'result': {u'domain': u'example.org'}})
