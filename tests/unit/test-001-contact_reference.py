import datetime
import unittest

from pykolab.xml import ContactReference


class TestEventXML(unittest.TestCase):
    contact_reference = ContactReference("jane@doe.org")

    def assertIsInstance(self, _value, _type):
        if hasattr(unittest.TestCase, 'assertIsInstance'):
            return unittest.TestCase.assertIsInstance(self, _value, _type)
        else:
            if (type(_value)) == _type:
                return True
            else:
                raise AssertionError("%s != %s" % (type(_value), _type))

    def test_001_minimal(self):
        self.assertIsInstance(self.contact_reference.__str__(), str)

    def test_002_empty_name(self):
        self.assertEqual(self.contact_reference.get_name(), "")

    def test_003_set_name(self):
        name = "Doe, Jane"
        self.contact_reference.set_name(name)
        self.assertEqual(self.contact_reference.get_name(), name)

if __name__ == '__main__':
    unittest.main()
