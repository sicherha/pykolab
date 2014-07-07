import unittest
import gettext
from pykolab import translate

class TestTranslate(unittest.TestCase):

    def setUp(self):
        translate.setUserLanguage('en')

    def test_001_default_langs(self):
        self.assertTrue(len(translate.getDefaultLangs()) > 0)

    def test_002_translate(self):
        from pykolab.translate import _
        self.assertEqual(_("Folder name"), "Folder name")

    def test_003_set_lang(self):
        from pykolab.translate import _
        self.assertFalse(translate.setUserLanguage('foo_bar'))
        self.assertEqual(_("Folder name"), "Folder name")
        self.assertTrue(translate.setUserLanguage('de_DE'))
        self.assertEqual(_("Folder name"), "Ordnername")

if __name__ == '__main__':
    unittest.main()
