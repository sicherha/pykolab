# -*- coding: utf-8 -*-

import unittest
import gettext
from pykolab import translate

class TestTranslate(unittest.TestCase):

    def test_001_default_langs(self):
        self.assertTrue(len(translate.getDefaultLangs()) > 0)

    def test_002_translate(self):
        from pykolab.translate import _
        self.assertEqual(_("Folder name"), "Folder name")

    def test_003_set_lang(self):
        from pykolab.translate import _
        self.assertEqual(_("Folder name"), "Folder name")

if __name__ == '__main__':
    unittest.main()
