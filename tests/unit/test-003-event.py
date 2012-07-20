import datetime
import pytz
import sys
import unittest

from pykolab.xml import Attendee
from pykolab.xml import Event
from pykolab.xml import EventIntegrityError
from pykolab.xml import InvalidAttendeeParticipantStatusError
from pykolab.xml import InvalidEventDateError

class TestEventXML(unittest.TestCase):
    event = Event()

    def assertIsInstance(self, _value, _type):
        if hasattr(unittest.TestCase, 'assertIsInstance'):
            return unittest.TestCase.assertIsInstance(self, _value, _type)
        else:
            if (type(_value)) == _type:
                return True
            else:
                raise AssertionError, "%s != %s" % (type(_value), _type)

    def test_000_no_start_date(self):
        self.assertRaises(EventIntegrityError, self.event.__str__)

    def test_001_minimal(self):
        self.event.set_start(datetime.datetime.now(pytz.timezone("Europe/London")))
        self.assertIsInstance(self.event.get_start(), datetime.datetime)
        self.assertIsInstance(self.event.__str__(), str)

    def test_002_attendees_list(self):
        self.assertIsInstance(self.event.get_attendees(), list)

    def test_003_attendees_no_default(self):
        self.assertEqual(len(self.event.get_attendees()), 0)

    def test_004_attendee_add(self):
        self.event.add_attendee("john@doe.org")
        self.assertIsInstance(self.event.get_attendees(), list)
        self.assertEqual(len(self.event.get_attendees()), 1)

    def test_005_attendee_add_name(self):
        self.event.add_attendee("jane@doe.org", "Doe, Jane")
        self.assertIsInstance(self.event.get_attendees(), list)
        self.assertEqual(len(self.event.get_attendees()), 2)

    def test_006_get_attendees(self):
        self.assertEqual([x.get_email() for x in self.event.get_attendees()], ["john@doe.org", "jane@doe.org"])

    def test_007_get_attendee_by_email(self):
        self.assertIsInstance(self.event.get_attendee_by_email("jane@doe.org"), Attendee)
        self.assertIsInstance(self.event.get_attendee("jane@doe.org"), Attendee)

    def test_007_get_nonexistent_attendee_by_email(self):
        self.assertRaises(ValueError, self.event.get_attendee_by_email, "nosuchattendee@invalid.domain")
        self.assertRaises(ValueError, self.event.get_attendee, "nosuchattendee@invalid.domain")

    def test_008_get_attendee_by_name(self):
        self.assertIsInstance(self.event.get_attendee_by_name("Doe, Jane"), Attendee)
        self.assertIsInstance(self.event.get_attendee("Doe, Jane"), Attendee)

    def test_008_get_nonexistent_attendee_by_name(self):
        self.assertRaises(ValueError, self.event.get_attendee_by_name, "Houdini, Harry")
        self.assertRaises(ValueError, self.event.get_attendee, "Houdini, Harry")

    def test_009_invalid_participant_status(self):
        self.assertRaises(InvalidAttendeeParticipantStatusError, self.event.set_attendee_participant_status, "jane@doe.org", "INVALID")

    def test_010_datetime_from_string(self):
        self.assertRaises(InvalidEventDateError, self.event.set_start, "2012-05-23 11:58:00")

    def test_011_attendee_equality(self):
        self.assertEqual(self.event.get_attendee("jane@doe.org").get_email(), "jane@doe.org")

    def test_012_delegate_new_attendee(self):
        self.event.delegate("jane@doe.org", "max@imum.com")

    def test_013_delegatee_is_now_attendee(self):
        self.assertIsInstance(self.event.get_attendee("max@imum.com"), Attendee)

    def test_014_delegate_attendee_adds(self):
        self.assertEqual(len(self.event.get_attendee("jane@doe.org").get_delegated_to()), 1)
        self.event.delegate("jane@doe.org", "john@doe.org")
        self.assertEqual(len(self.event.get_attendee("jane@doe.org").get_delegated_to()), 2)

    def test_015_timezone(self):
        _tz = self.event.get_start()
        self.assertIsInstance(_tz.tzinfo, datetime.tzinfo)

    def test_016_start_with_timezone(self):
        _start = datetime.datetime(2012, 05, 23, 11, 58, 00, tzinfo=pytz.timezone("Europe/Zurich"))
        _start_utc = _start.astimezone(pytz.utc)
        self.assertEqual(_start.__str__(), "2012-05-23 11:58:00+01:00")
        self.assertEqual(_start_utc.__str__(), "2012-05-23 10:58:00+00:00")
        self.event.set_start(_start)
        self.assertIsInstance(_start.tzinfo, datetime.tzinfo)
        self.assertEqual(_start.tzinfo, pytz.timezone("Europe/Zurich"))

    def test_017_allday_without_timezone(self):
        _start = datetime.date(2012, 05, 23)
        self.assertEqual(_start.__str__(), "2012-05-23")
        self.event.set_start(_start)
        self.assertEqual(hasattr(_start,'tzinfo'), False)
        self.assertEqual(self.event.get_start().__str__(), "2012-05-23")

if __name__ == '__main__':
    unittest.main()
