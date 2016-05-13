# -*- coding: utf-8 -*-

import unittest

from pykolab import utils


class TestTranslate(unittest.TestCase):

    def test_001_normalize(self):
        attr = {"test1": " trim ", "test2": [" trim1 ", " trim2 "]}
        result = utils.normalize(attr)

        self.assertEqual(result['test1'], "trim")
        self.assertEqual(result['test2'][0], "trim1")
        self.assertEqual(result['test2'][1], "trim2")


if __name__ == '__main__':
    unittest.main()
