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
        translate.setUserLanguage('de_DE')
        self.assertEqual(_("Folder name"), "Ordnername", "German Translation found")
        translate.setUserLanguage('foo_bar')
        self.assertEqual(_("Folder name"), "Folder name", "Unknown language falls back to NullTranslations")

    def test_004_unicode(self):
        from pykolab.translate import _
        translate.setUserLanguage('de_DE')
        self.assertEqual(_("recipients: %r"), "Empfänger: %r")

if __name__ == '__main__':
    unittest.main()
