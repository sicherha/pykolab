# -*- coding: utf-8 -*-

import os
import pykolab
import tempfile
import unittest

conf = pykolab.getConf()
conf.finalize_conf(fatal=False)


class TestConfRaw(unittest.TestCase):
    config_file = None

    @classmethod
    def setup_class(self, *args, **kw):
        (fp, self.config_file) = tempfile.mkstemp()
        os.write(fp, '[kolab]\n')
        os.close(fp)
        conf.read_config(self.config_file)

    @classmethod
    def teardown_class(self, *args, **kw):
        os.remove(self.config_file)

    def test_001_set(self):
        password = '$%something'
        conf.command_set('kolab', 'test_password', password)

    def test_002_get(self):
        password = conf.get('kolab', 'test_password')
        self.assertEqual('$%something', password)

    def test_003_get_raw(self):
        password = conf.get_raw('kolab', 'test_password')
        self.assertNotEqual('$%something', password)

if __name__ == '__main__':
    unittest.main()
