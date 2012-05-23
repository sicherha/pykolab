import datetime
import unittest

from pykolab.xml import Attendee

class TestEventXML(unittest.TestCase):
    attendee = Attendee("jane@doe.org")

    def test_001_minimal(self):
        self.assertIsInstance(self.attendee.__str__(), basestring)

    def test_002_set_name(self):
        name = "Doe, Jane"
        self.attendee.set_name(name)
        self.assertEqual(self.attendee.get_name(), name)

if __name__ == '__main__':
    unittest.main()
