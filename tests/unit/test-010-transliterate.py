# -*- coding: utf-8 -*-

import unittest

class TestTransliteration(unittest.TestCase):
    def test_001_raw_fr_FR(self):
        """
            The special thing about this case is that the givenname starts with
            a special character.
        """
        from pykolab import utils
        givenname = r'Étienne-Nicolas'
        surname = r'Méhul'

        preferredlanguage = 'fr_FR'

        self.assertEqual('Etienne-Nicolas', utils.translate(givenname, preferredlanguage))
        self.assertEqual('Mehul', utils.translate(surname, preferredlanguage))

    def test_002_unicode_fr_FR(self):
        """
            The special thing about this case is that the givenname starts with
            a special character.
        """
        from pykolab import utils
        givenname = 'Étienne-Nicolas'
        surname = 'Méhul'

        preferredlanguage = 'fr_FR'

        self.assertEqual('Etienne-Nicolas', utils.translate(givenname, preferredlanguage))
        self.assertEqual('Mehul', utils.translate(surname, preferredlanguage))

    def test_003_raw_es_ES(self):
        """
            The special thing about this case is that the givenname starts with
            a special character.
        """
        from pykolab import utils
        givenname = r'Álvaro'
        surname = r'Fuentes'

        preferredlanguage = 'es_ES'

        self.assertEqual('Alvaro', utils.translate(givenname, preferredlanguage))
        self.assertEqual('Fuentes', utils.translate(surname, preferredlanguage))

    def test_004_unicode_es_ES(self):
        """
            The special thing about this case is that the givenname starts with
            a special character.
        """
        from pykolab import utils
        givenname = 'Álvaro'
        surname = 'Fuentes'

        preferredlanguage = 'es_ES'

        self.assertEqual('Alvaro', utils.translate(givenname, preferredlanguage))
        self.assertEqual('Fuentes', utils.translate(surname, preferredlanguage))


if __name__ == '__main__':
    unittest.main()
