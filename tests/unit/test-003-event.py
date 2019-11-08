import re
import datetime
import pytz
import sys
import unittest
import kolabformat
import icalendar
import pykolab

from pykolab.xml import Attendee
from pykolab.xml import Event
from pykolab.xml import RecurrenceRule
from pykolab.xml import EventIntegrityError
from pykolab.xml import InvalidAttendeeParticipantStatusError
from pykolab.xml import InvalidEventDateError
from pykolab.xml import event_from_ical
from pykolab.xml import event_from_string
from pykolab.xml import event_from_message
from pykolab.xml import compute_diff
from pykolab.xml import property_to_string
from collections import OrderedDict

ical_event = """
BEGIN:VEVENT
UID:7a35527d-f783-4b58-b404-b1389bd2fc57
DTSTAMP;VALUE=DATE-TIME:20140407T122311Z
CREATED;VALUE=DATE-TIME:20140407T122245Z
LAST-MODIFIED;VALUE=DATE-TIME:20140407T122311Z
DTSTART;TZID=Europe/Zurich;VALUE=DATE-TIME:20140523T110000
DURATION:PT1H30M0S
RRULE:FREQ=WEEKLY;INTERVAL=1;COUNT=10
EXDATE;TZID=Europe/Zurich;VALUE=DATE-TIME:20140530T110000
EXDATE;TZID=Europe/Zurich;VALUE=DATE-TIME:20140620T110000
SUMMARY:Summary
LOCATION:Location
DESCRIPTION:Description\\n2 lines
CATEGORIES:Personal
TRANSP:OPAQUE
PRIORITY:2
SEQUENCE:2
CLASS:PUBLIC
ATTENDEE;CN="Manager, Jane";PARTSTAT=NEEDS-ACTION;ROLE=REQ-PARTICIPANT;CUTYP
 E=INDIVIDUAL;RSVP=TRUE:mailto:jane.manager@example.org
ATTENDEE;CUTYPE=ROOM;PARTSTAT=NEEDS-ACTION;ROLE=OPT-PARTICIPANT;RSVP=FA
 LSE:MAILTO:max@imum.com
ORGANIZER;CN=Doe\, John:mailto:john.doe@example.org
URL:http://somelink.com/foo
ATTACH;VALUE=BINARY;ENCODING=BASE64;FMTTYPE=image/png;X-LABEL=silhouette.pn
 g:iVBORw0KGgoAAAANSUhEUgAAAC4AAAAuCAIAAADY27xgAAAAGXRFWHRTb2Z0d2FyZQBBZG9i
 ZSBJbWFnZVJlYWR5ccllPAAAAsRJREFUeNrsmeluKjEMhTswrAWB4P3fECGx79CjsTDmOKRkpF
 xxpfoHSmchX7ybFrfb7eszpPH1MfKH8ofyH6KUtd/c7/en0wmfWBdF0Wq1Op1Ou91uNGoer6iX
 V1ar1Xa7xUJeB4qsr9frdyVlWWZH2VZyPp+xPXHIAoK70+m02+1m9JXj8bhcLi+Xi3J4xUCazS
 bUltdtd7ud7ldUIhC3u+iTwF0sFhlR4Kds4LtRZK1w4te5UM6V6JaqhqC3CQ28OAsKggJfbZ3U
 eozCqZ4koHIZCGmD9ivuos9YONFirmxrI0UNZG1kbZeUXdJQNJNa91RlqMn0ekYUMZDup6dXVV
 m+1OSZhqLx6bVCELJGSsyFQtFrF15JGYMZgoxubWGDSDVhvTipDKWhoBOIpFobxtlbJ0Gh0/tg
 lgXal4woUHi/36fQoBQncDAlupa8DeVwOPRe4lUyGAwQ+dl7W+xBXkJBhEUqR32UoJfYIKrR4d
 ZBgcdIRqfEqn+mekl9FNRbSTA249la3ev1/kXHD47ZbEYR5L9kMplkd9vNZqMFyIYxxfN8Pk8q
 QGlagT5QDtfrNYUMlWW9LiGNPPSmC/+OgpK2r4RO6dOatZd+4gAAemdIi6Fg9EKLD4vASWkzv3
 ew06NSCiA40CumAIoaIrhrcAwjF7aDo58gUchgNV+0n1BAcDgcoAZrXV9mI4qkhtK6FJFhi9Fo
 ZKPsgQI1ACJieH/Kd570t+xFoIzHYzl5Q40CFGrSqGuks3qmYIKJfIl0nPKLxAMFw7Dv1+2QYf
 vFSOBQubbOFDSc7ZcfWvHv6DzhOzT6IeOVPuz8Roex0f6EgsE/2IL4qdg7hIXz7/pBie7q1uWr
 tp66xrif0l1KwUE4P7Y9Gci/ZgtNRFX+Rw06Q2RigsjuDc3urwKHxuNITaaxyD9mT2WvSDAXn/
 Pvhh8BBgBjyfPSGbSYcwAAAABJRU5ErkJggg==
ATTACH;VALUE=BINARY;ENCODING=BASE64;FMTTYPE=text/plain;X-LABEL=text.txt:VGh
 pcyBpcyBhIHRleHQgZmlsZQo=
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT30M
END:VALARM
END:VEVENT
"""

ical_exception = """
BEGIN:VEVENT
UID:7a35527d-f783-4b58-b404-b1389bd2fc57
DTSTAMP;VALUE=DATE-TIME:20140407T122311Z
CREATED;VALUE=DATE-TIME:20140407T122245Z
LAST-MODIFIED;VALUE=DATE-TIME:20140407T122311Z
RECURRENCE-ID;TZID=Europe/Zurich;RANGE=THISANDFUTURE:20140606T110000
DTSTART;TZID=Europe/Zurich;VALUE=DATE-TIME:20140607T120000
DTEND;TZID=Europe/Zurich;VALUE=DATE-TIME:20140607T143000
SUMMARY:Exception
CATEGORIES:Personal
TRANSP:TRANSPARENT
PRIORITY:2
SEQUENCE:3
STATUS:CANCELLED
ORGANIZER;CN=Doe\, John:mailto:john.doe@example.org
END:VEVENT
"""

ical_event_rdate = """
BEGIN:VEVENT
UID:7a35527d-f783-4b58-b404-b1389bd2fc57
DTSTAMP;VALUE=DATE-TIME:20140407T122311Z
CREATED;VALUE=DATE-TIME:20140407T122245Z
LAST-MODIFIED;VALUE=DATE-TIME:20140407T122311Z
DTSTART;TZID=Europe/Zurich;VALUE=DATE-TIME:20140523T110000
DURATION:PT1H30M0S
RDATE;TZID=Europe/Zurich;VALUE=DATE-TIME:20140530T110000
RDATE;TZID=Europe/Zurich;VALUE=DATE-TIME:20140620T110000
SUMMARY:Summary
LOCATION:Location
DESCRIPTION:Description
SEQUENCE:2
CLASS:PUBLIC
ORGANIZER;CN=Doe\, John:mailto:john.doe@example.org
END:VEVENT
"""

xml_event = """
<icalendar xmlns="urn:ietf:params:xml:ns:icalendar-2.0">
  <vcalendar>
    <properties>
      <prodid>
        <text>Libkolabxml-1.1</text>
      </prodid>
      <version>
        <text>2.0</text>
      </version>
      <x-kolab-version>
        <text>3.1.0</text>
      </x-kolab-version>
    </properties>
    <components>
      <vevent>
        <properties>
          <uid>
            <text>75c740bb-b3c6-442c-8021-ecbaeb0a025e</text>
          </uid>
          <created>
            <date-time>2013-07-07T01:28:23Z</date-time>
          </created>
          <dtstamp>
            <date-time>2013-07-07T01:28:23Z</date-time>
          </dtstamp>
          <sequence>
            <integer>1</integer>
          </sequence>
          <class>
            <text>PUBLIC</text>
          </class>
          <dtstart>
            <parameters>
              <tzid>
                <text>/kolab.org/Europe/London</text>
              </tzid>
            </parameters>
            <date-time>2013-08-13T10:00:00</date-time>
          </dtstart>
          <dtend>
            <parameters>
              <tzid><text>/kolab.org/Europe/London</text></tzid>
            </parameters>
            <date-time>2013-08-13T14:00:00</date-time>
          </dtend>
          <rrule>
            <recur>
              <freq>DAILY</freq>
              <until>
                <date>2015-07-25</date>
              </until>
            </recur>
          </rrule>
          <exdate>
            <parameters>
              <tzid>
                <text>/kolab.org/Europe/Berlin</text>
              </tzid>
            </parameters>
            <date>2014-07-19</date>
            <date>2014-07-26</date>
            <date>2014-07-12</date>
            <date>2014-07-13</date>
            <date>2014-07-20</date>
            <date>2014-07-27</date>
            <date>2014-07-05</date>
            <date>2014-07-06</date>
          </exdate>
          <summary>
            <text>test</text>
          </summary>
          <description>
            <text>test</text>
          </description>
          <priority>
            <integer>5</integer>
          </priority>
          <status>
            <text>CANCELLED</text>
          </status>
          <location>
            <text>Room 101</text>
          </location>
          <organizer>
            <parameters>
              <cn><text>Doe, John</text></cn>
            </parameters>
            <cal-address>mailto:%3Cjohn%40example.org%3E</cal-address>
          </organizer>
          <attendee>
            <parameters>
              <partstat><text>ACCEPTED</text></partstat>
              <role><text>REQ-PARTICIPANT</text></role>
              <rsvp><boolean>true</boolean></rsvp>
              <delegated-from><cal-address>mailto:%3Csomebody%40else.com%3E</cal-address></delegated-from>
            </parameters>
            <cal-address>mailto:%3Cjane%40example.org%3E</cal-address>
          </attendee>
          <attendee>
            <parameters>
              <partstat><text>DELEGATED</text></partstat>
              <role><text>NON-PARTICIPANT</text></role>
              <delegated-to><cal-address>mailto:%3Cjane%40example.org%3E</cal-address></delegated-to>
            </parameters>
            <cal-address>mailto:%3Csomebody%40else.com%3E</cal-address>
          </attendee>
          <attach>
            <parameters>
              <fmttype>
                <text>text/html</text>
              </fmttype>
              <x-label>
                <text>noname.1395223627.5555</text>
              </x-label>
            </parameters>
            <uri>cid:noname.1395223627.5555</uri>
          </attach>
          <x-custom>
            <identifier>X-MOZ-RECEIVED-DTSTAMP</identifier>
            <value>20140224T155612Z</value>
          </x-custom>
          <x-custom>
            <identifier>X-GWSHOW-AS</identifier>
            <value>BUSY</value>
          </x-custom>
        </properties>
        <components>
          <valarm>
            <properties>
              <action>
                <text>DISPLAY</text>
              </action>
              <description>
                <text>alarm 1</text>
              </description>
              <trigger>
                <parameters>
                  <related>
                    <text>START</text>
                  </related>
                </parameters>
                <duration>-PT2H</duration>
              </trigger>
            </properties>
          </valarm>
          <valarm>
            <properties>
              <action>
                <text>EMAIL</text>
              </action>
              <summary>
                <text>test</text>
              </summary>
              <description>
                <text>alarm 2</text>
              </description>
              <attendee>
                  <cal-address>mailto:%3Cjohn.doe%40example.org%3E</cal-address>
              </attendee>
              <trigger>
                <parameters>
                  <related>
                    <text>START</text>
                  </related>
                </parameters>
                <duration>-P1D</duration>
              </trigger>
            </properties>
          </valarm>
        </components>
      </vevent>
      <vevent>
        <properties>
          <uid>
            <text>75c740bb-b3c6-442c-8021-ecbaeb0a025e</text>
          </uid>
          <created>
            <date-time>2014-07-07T01:28:23Z</date-time>
          </created>
          <dtstamp>
            <date-time>2014-07-07T01:28:23Z</date-time>
          </dtstamp>
          <sequence>
            <integer>2</integer>
          </sequence>
          <class>
            <text>PUBLIC</text>
          </class>
          <dtstart>
            <parameters>
              <tzid>
                <text>/kolab.org/Europe/London</text>
              </tzid>
            </parameters>
            <date-time>2014-08-16T13:00:00</date-time>
          </dtstart>
          <dtend>
            <parameters>
              <tzid><text>/kolab.org/Europe/London</text></tzid>
            </parameters>
            <date-time>2014-08-16T16:00:00</date-time>
          </dtend>
          <recurrence-id>
            <parameters>
              <tzid>
                <text>/kolab.org/Europe/London</text>
              </tzid>
              <range>
                <text>THISANDFUTURE</text>
              </range>
            </parameters>
            <date-time>2014-08-16T10:00:00</date-time>
          </recurrence-id>
          <summary>
            <text>exception</text>
          </summary>
          <description>
            <text>exception</text>
          </description>
          <location>
            <text>Room 101</text>
          </location>
          <organizer>
            <parameters>
              <cn><text>Doe, John</text></cn>
            </parameters>
            <cal-address>mailto:%3Cjohn%40example.org%3E</cal-address>
          </organizer>
          <attendee>
            <parameters>
              <partstat><text>DECLINED</text></partstat>
              <role><text>REQ-PARTICIPANT</text></role>
            </parameters>
            <cal-address>mailto:%3Cjane%40example.org%3E</cal-address>
          </attendee>
        </properties>
      </vevent>
    </components>
  </vcalendar>
</icalendar>
"""


class TestEventXML(unittest.TestCase):
    event = Event()

    @classmethod
    def setUp(self):
        """ Compatibility for twisted.trial.unittest
        """
        self.setup_class()

    @classmethod
    def setup_class(self, *args, **kw):
        # set language to default
        pykolab.translate.setUserLanguage('en_US')

    def assertIsInstance(self, _value, _type, _msg=None):
        if hasattr(unittest.TestCase, 'assertIsInstance'):
            return unittest.TestCase.assertIsInstance(self, _value, _type, _msg)
        else:
            if (type(_value)) == _type:
                return True
            else:
                if _msg is not None:
                    raise AssertionError("%s != %s: %r" % (type(_value), _type, _msg))
                else:
                    raise AssertionError("%s != %s" % (type(_value), _type))

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

    def test_005_attendee_add_name_and_props(self):
        self.event.add_attendee("jane@doe.org", "Doe, Jane", role="OPT-PARTICIPANT", cutype="RESOURCE")
        self.assertIsInstance(self.event.get_attendees(), list)
        self.assertEqual(len(self.event.get_attendees()), 2)

    def test_006_get_attendees(self):
        self.assertEqual([x.get_email() for x in self.event.get_attendees()], ["john@doe.org", "jane@doe.org"])

    def test_007_get_attendee_by_email(self):
        self.assertIsInstance(self.event.get_attendee_by_email("jane@doe.org"), Attendee)
        self.assertIsInstance(self.event.get_attendee("jane@doe.org"), Attendee)

    def test_007_get_attendee_props(self):
        self.assertEqual(self.event.get_attendee("jane@doe.org").get_cutype(), kolabformat.CutypeResource)
        self.assertEqual(self.event.get_attendee("jane@doe.org").get_role(), kolabformat.Optional)

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

    def test_009_update_attendees(self):
        jane = self.event.get_attendee("jane@doe.org")
        jane.set_name("Jane (GI) Doe")
        self.event.update_attendees([jane])
        self.assertEqual(len(self.event.get_attendees()), 2)
        self.assertEqual(self.event.get_attendee("jane@doe.org").get_name(), "Jane (GI) Doe")

    def test_010_datetime_from_string(self):
        self.assertRaises(InvalidEventDateError, self.event.set_start, "2012-05-23 11:58:00")

    def test_011_attendee_equality(self):
        self.assertEqual(self.event.get_attendee("jane@doe.org").get_email(), "jane@doe.org")

    def test_012_delegate_new_attendee(self):
        self.event.delegate("jane@doe.org", "max@imum.com")

    def test_013_delegatee_is_now_attendee(self):
        delegatee = self.event.get_attendee("max@imum.com")
        self.assertIsInstance(delegatee, Attendee)
        self.assertEqual(delegatee.get_role(), kolabformat.Optional)
        self.assertEqual(delegatee.get_cutype(), kolabformat.CutypeResource)

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
        # self.assertEqual(_start.__str__(), "2012-05-23 11:58:00+01:00")
        # self.assertEqual(_start_utc.__str__(), "2012-05-23 10:58:00+00:00")
        self.event.set_start(_start)
        self.assertIsInstance(_start.tzinfo, datetime.tzinfo)
        self.assertEqual(_start.tzinfo, pytz.timezone("Europe/Zurich"))

    def test_017_allday_without_timezone(self):
        _start = datetime.date(2012, 05, 23)
        self.assertEqual(_start.__str__(), "2012-05-23")
        self.event.set_start(_start)
        self.assertEqual(hasattr(_start, 'tzinfo'), False)
        self.assertEqual(self.event.get_start().__str__(), "2012-05-23")

    def test_018_load_from_ical(self):
        ical_str = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1-git//Sabre//Sabre VObject
  2.1.3//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
        """ + ical_event + ical_exception + "END:VCALENDAR"

        ical = icalendar.Calendar.from_ical(ical_str)
        event = event_from_ical(ical.walk('VEVENT')[0], ical_str)

        self.assertEqual(event.get_location(), "Location")
        self.assertEqual(str(event.get_lastmodified()), "2014-04-07 12:23:11+00:00")
        self.assertEqual(event.get_description(), "Description\n2 lines")
        self.assertEqual(event.get_url(), "http://somelink.com/foo")
        self.assertEqual(event.get_transparency(), False)
        self.assertEqual(event.get_categories(), ["Personal"])
        self.assertEqual(event.get_priority(), '2')
        self.assertEqual(event.get_classification(), kolabformat.ClassPublic)
        self.assertEqual(event.get_attendee_by_email("max@imum.com").get_cutype(), kolabformat.CutypeRoom)
        self.assertEqual(event.get_sequence(), 2)
        self.assertTrue(event.is_recurring())
        self.assertIsInstance(event.get_duration(), datetime.timedelta)
        self.assertIsInstance(event.get_end(), datetime.datetime)
        self.assertEqual(str(event.get_end()), "2014-05-23 12:30:00+02:00")
        self.assertEqual(len(event.get_exception_dates()), 2)
        self.assertIsInstance(event.get_exception_dates()[0], datetime.datetime)
        self.assertEqual(len(event.get_alarms()), 1)
        self.assertEqual(len(event.get_attachments()), 2)
        self.assertEqual(len(event.get_exceptions()), 1)

        exception = event.get_exceptions()[0]
        self.assertIsInstance(exception.get_recurrence_id(), datetime.datetime)
        # self.assertEqual(exception.thisandfuture, True)
        self.assertEqual(str(exception.get_start()), "2014-06-07 12:00:00+02:00")

    def test_018_ical_to_message(self):
        event = event_from_ical(ical_event)
        message = event.to_message()

        self.assertTrue(message.is_multipart())
        self.assertEqual(message['Subject'], event.uid)
        self.assertEqual(message['X-Kolab-Type'], 'application/x-vnd.kolab.event')

        parts = [p for p in message.walk()]
        attachments = event.get_attachments()

        self.assertEqual(len(parts), 5)
        self.assertEqual(parts[1].get_content_type(), 'text/plain')
        self.assertEqual(parts[2].get_content_type(), 'application/calendar+xml')
        self.assertEqual(parts[3].get_content_type(), 'image/png')
        self.assertEqual(parts[4].get_content_type(), 'text/plain')
        self.assertEqual(parts[2]['Content-ID'], None)
        self.assertEqual(parts[3]['Content-ID'].strip('<>'), attachments[0].uri()[4:])
        self.assertEqual(parts[4]['Content-ID'].strip('<>'), attachments[1].uri()[4:])

    def test_018_ical_allday_events(self):
        ical = """BEGIN:VEVENT
UID:ffffffff-f783-4b58-b404-b1389bd2ffff
DTSTAMP;VALUE=DATE-TIME:20140407T122311Z
CREATED;VALUE=DATE-TIME:20140407T122245Z
DTSTART;VALUE=DATE:20140823
DTEND;VALUE=DATE:20140824
SUMMARY:All day
DESCRIPTION:One single day
TRANSP:OPAQUE
CLASS:PUBLIC
END:VEVENT
"""
        event = event_from_ical(ical)
        self.assertEqual(str(event.get_start()), "2014-08-23")
        self.assertEqual(str(event.get_end()), "2014-08-23")
        self.assertEqual(str(event.get_ical_dtend()), "2014-08-24")
        self.assertTrue(re.match('.*<dtend>\s*<date>2014-08-23</date>', str(event), re.DOTALL))

    def test_019_as_string_itip(self):
        self.event.set_summary("test")
        self.event.set_start(datetime.datetime(2014, 05, 23, 11, 00, 00, tzinfo=pytz.timezone("Europe/London")))
        self.event.set_end(datetime.datetime(2014, 05, 23, 12, 30, 00, tzinfo=pytz.timezone("Europe/London")))
        self.event.set_sequence(3)
        self.event.set_classification('CONFIDENTIAL')
        self.event.add_custom_property('X-Custom', 'check')
        self.event.set_recurrence_id(datetime.datetime(2014, 05, 23, 11, 0, 0), True)

        rrule = RecurrenceRule()
        rrule.set_frequency(kolabformat.RecurrenceRule.Weekly)
        rrule.set_byday(['2WE', '-1SU'])
        rrule.setBymonth([2])
        rrule.set_count(10)
        rrule.set_until(datetime.datetime(2014, 7, 23, 11, 0, 0, tzinfo=pytz.timezone("Europe/London")))
        self.event.set_recurrence(rrule)

        ical = icalendar.Calendar.from_ical(self.event.as_string_itip())
        event = ical.walk('VEVENT')[0]

        self.assertEqual(event['uid'], self.event.get_uid())
        self.assertEqual(event['summary'], "test")
        self.assertEqual(event['sequence'], 3)
        self.assertEqual(event['X-CUSTOM'], "check")
        self.assertIsInstance(event['dtstamp'].dt, datetime.datetime)
        self.assertEqual(event['class'], "CONFIDENTIAL")
        self.assertIsInstance(event['recurrence-id'].dt, datetime.datetime)
        self.assertEqual(event['recurrence-id'].params.get('RANGE'), 'THISANDFUTURE')

        self.assertTrue('rrule' in event)
        self.assertEqual(event['rrule']['FREQ'][0], 'WEEKLY')
        self.assertEqual(event['rrule']['INTERVAL'][0], 1)
        self.assertEqual(event['rrule']['COUNT'][0], 10)
        self.assertEqual(event['rrule']['BYMONTH'][0], 2)
        self.assertEqual(event['rrule']['BYDAY'], ['2WE', '-1SU'])
        self.assertIsInstance(event['rrule']['UNTIL'][0], datetime.datetime)
        self.assertEquals(event['rrule']['UNTIL'][0].tzinfo, pytz.utc)

    def test_019_to_message_itip(self):
        self.event = Event()
        self.event.set_summary("test")
        self.event.set_start(datetime.datetime(2014, 05, 23, 11, 00, 00, tzinfo=pytz.timezone("Europe/London")))
        self.event.set_end(datetime.datetime(2014, 05, 23, 12, 30, 00, tzinfo=pytz.timezone("Europe/London")))
        self.event.set_organizer("me@kolab.org")
        self.event.add_attendee("john@doe.org")
        self.event.add_attendee("jane@doe.org")

        message = self.event.to_message_itip("john@doe.org", method="REPLY", participant_status="ACCEPTED")
        itip_event = None
        for part in message.walk():
            if part.get_content_type() == "text/calendar":
                ical = icalendar.Calendar.from_ical(part.get_payload(decode=True))
                itip_event = ical.walk('VEVENT')[0]
                break

        self.assertEqual(itip_event['uid'], self.event.get_uid())
        self.assertEqual(itip_event['attendee'].lower(), 'mailto:john@doe.org')

        # delegate jane => jack
        self.event.delegate("jane@doe.org", "jack@ripper.com", "Jack")

        message = self.event.to_message_itip("jane@doe.org", method="REPLY", participant_status="DELEGATED")
        itip_event = None
        for part in message.walk():
            if part.get_content_type() == "text/calendar":
                ical = icalendar.Calendar.from_ical(part.get_payload(decode=True))
                itip_event = ical.walk('VEVENT')[0]
                break

        self.assertEqual(len(itip_event['attendee']), 2)
        self.assertEqual(str(itip_event['attendee'][0]).lower(), 'mailto:jane@doe.org')
        self.assertEqual(str(itip_event['attendee'][1]).lower(), 'mailto:jack@ripper.com')
        self.assertEqual(itip_event['attendee'][0].params['delegated-to'], 'jack@ripper.com')
        self.assertEqual(itip_event['attendee'][1].params['delegated-from'], 'jane@doe.org')

    def test_020_calendaring_recurrence(self):
        rrule = kolabformat.RecurrenceRule()
        rrule.setFrequency(kolabformat.RecurrenceRule.Monthly)
        rrule.setCount(10)

        self.event = Event()
        self.event.set_recurrence(rrule)

        _start = datetime.datetime(2014, 5, 1, 11, 30, 00, tzinfo=pytz.timezone("Europe/London"))
        self.event.set_start(_start)
        self.event.set_end(_start + datetime.timedelta(hours=2))

        self.assertTrue(self.event.is_recurring())

        next_date = self.event.get_next_occurence(_start)
        self.assertIsInstance(next_date, datetime.datetime)
        self.assertEqual(next_date.month, 6)
        self.assertEqual(next_date.day, 1)

        end_date = self.event.get_occurence_end_date(next_date)
        self.assertIsInstance(end_date, datetime.datetime)
        self.assertEqual(end_date.month, 6)
        self.assertEqual(end_date.hour, 13)

        self.assertEqual(self.event.get_next_occurence(next_date).month, 7)

        last_date = self.event.get_last_occurrence()
        self.assertIsInstance(last_date, datetime.datetime)
        self.assertEqual(last_date.year, 2015)
        self.assertEqual(last_date.month, 2)

        self.assertEqual(self.event.get_next_occurence(last_date), None)

        # check infinite recurrence
        rrule = kolabformat.RecurrenceRule()
        rrule.setFrequency(kolabformat.RecurrenceRule.Monthly)
        self.event.set_recurrence(rrule)

        self.assertEqual(self.event.get_last_occurrence(), None)
        self.assertIsInstance(self.event.get_last_occurrence(force=True), datetime.datetime)

        # check get_next_instance() which returns a clone of the base event
        next_instance = self.event.get_next_instance(next_date)
        self.assertIsInstance(next_instance, Event)
        self.assertIsInstance(next_instance.get_recurrence_id(), datetime.datetime)
        self.assertEqual(self.event.get_summary(), next_instance.get_summary())
        self.assertEqual(next_instance.get_start().month, 7)
        self.assertFalse(next_instance.is_recurring())

        # check get_next_occurence() with an infinitely recurring all-day event
        rrule = kolabformat.RecurrenceRule()
        rrule.setFrequency(kolabformat.RecurrenceRule.Yearly)
        self.event.set_recurrence(rrule)

        self.event.set_start(datetime.date(2014, 5, 1))
        self.event.set_end(datetime.date(2014, 5, 1))
        next_date = self.event.get_next_occurence(datetime.date(2015, 1, 1))
        self.assertIsInstance(next_date, datetime.date)
        self.assertEqual(next_date.year, 2015)
        self.assertEqual(next_date.month, 5)

    def test_021_calendaring_no_recurrence(self):
        _start = datetime.datetime(2014, 2, 1, 14, 30, 00, tzinfo=pytz.timezone("Europe/London"))
        self.event = Event()
        self.event.set_start(_start)
        self.event.set_end(_start + datetime.timedelta(hours=2))

        self.assertEqual(self.event.get_next_occurence(_start), None)
        self.assertEqual(self.event.get_last_occurrence(), None)

    def test_021_add_exceptions(self):
        event = event_from_ical(ical_event)
        exception = event_from_ical(ical_exception)
        self.assertIsInstance(event, Event)
        self.assertIsInstance(exception, Event)

        event.add_exception(exception)
        self.assertEquals(len(event.get_exceptions()), 1)

        # second call shall replace the existing exception
        event.add_exception(exception)
        self.assertEquals(len(event.get_exceptions()), 1)

        # first real occurrence should be our exception
        occurrence = event.get_next_instance(event.get_start())
        self.assertEqual(occurrence.get_summary(), "Exception")

    def test_021_allday_recurrence(self):
        rrule = kolabformat.RecurrenceRule()
        rrule.setFrequency(kolabformat.RecurrenceRule.Daily)
        rrule.setCount(10)

        self.event = Event()
        self.event.set_summary('alldays')
        self.event.set_recurrence(rrule)

        _start = datetime.date(2015, 1, 1)
        self.event.set_start(_start)
        self.event.set_end(_start)

        exdate = datetime.date(2015, 1, 5)
        xmlexception = Event(from_string=str(self.event))
        xmlexception.set_start(exdate)
        xmlexception.set_end(exdate)
        xmlexception.set_recurrence_id(exdate, False)
        xmlexception.set_status('CANCELLED')
        self.event.add_exception(xmlexception)

        inst3 = self.event.get_instance(datetime.date(2015, 1, 3))
        self.assertEqual(inst3.get_start(), datetime.date(2015, 1, 3))

        inst5 = self.event.get_instance(exdate)
        self.assertEqual(inst5.get_status(True), 'CANCELLED')

    def test_021_ical_exceptions(self):
        self.event.set_summary("test")
        self.event.set_start(datetime.datetime(2014, 05, 23, 11, 00, 00, tzinfo=pytz.timezone("Europe/London")))
        self.event.set_end(datetime.datetime(2014, 05, 23, 12, 30, 00, tzinfo=pytz.timezone("Europe/London")))

        rrule = kolabformat.RecurrenceRule()
        rrule.setFrequency(kolabformat.RecurrenceRule.Weekly)
        self.event.set_recurrence(rrule)

        xmlexception = Event(from_string=str(self.event))
        xmlexception.set_start(datetime.datetime(2014, 05, 30, 14, 00, 00, tzinfo=pytz.timezone("Europe/London")))
        xmlexception.set_end(datetime.datetime(2014, 05, 30, 16, 00, 00, tzinfo=pytz.timezone("Europe/London")))
        xmlexception.set_recurrence_id(datetime.datetime(2014, 05, 30, 11, 0, 0), False)
        self.event.add_exception(xmlexception)

        ical = icalendar.Calendar.from_ical(self.event.as_string_itip())
        vevents = ical.walk('VEVENT')
        event = vevents[0]
        exception = vevents[1]

        self.assertEqual(event['uid'], self.event.get_uid())
        self.assertEqual(event['summary'], "test")

        self.assertEqual(exception['uid'], self.event.get_uid())
        self.assertIsInstance(exception['recurrence-id'].dt, datetime.datetime)
        self.assertEqual(exception['recurrence-id'].params.get('RANGE'), None)

    def test_021_single_instances(self):
        self.event = Event()
        self.event.set_summary('singles')

        _start = datetime.datetime(2015, 3, 1, 14, 0, 0, tzinfo=pytz.timezone("Europe/London"))
        self.event.set_start(_start)
        self.event.set_end(_start + datetime.timedelta(hours=1))
        self.event.set_recurrence_id(_start)

        _start2 = datetime.datetime(2015, 3, 5, 15, 0, 0, tzinfo=pytz.timezone("Europe/London"))
        xmlexception = Event(from_string=str(self.event))
        xmlexception.set_start(_start2)
        xmlexception.set_end(_start2 + datetime.timedelta(hours=1))
        xmlexception.set_summary('singles #2')
        xmlexception.set_recurrence_id(_start2)
        self.event.add_exception(xmlexception)

        self.assertEqual(self.event.has_exceptions(), True)

        first = self.event.get_instance(_start)
        self.assertIsInstance(first, Event)
        self.assertEqual(first.get_summary(), "singles")

        second = self.event.get_instance(_start2)
        self.assertIsInstance(second, Event)
        self.assertEqual(second.get_summary(), "singles #2")

        # update main instance
        first.set_status('CANCELLED')
        first.set_summary("singles #1")
        self.event.add_exception(first)

        event = event_from_string(str(self.event))
        self.assertEqual(self.event.has_exceptions(), True)
        self.assertEqual(event.get_status(True), 'CANCELLED')
        self.assertEqual(event.get_summary(), "singles #1")

    def test_022_load_from_xml(self):
        event = event_from_string(xml_event)
        self.assertEqual(event.uid, '75c740bb-b3c6-442c-8021-ecbaeb0a025e')
        self.assertEqual(event.get_attendee_by_email("jane@example.org").get_participant_status(), kolabformat.PartAccepted)
        self.assertEqual(len(event.get_attendee_by_email("jane@example.org").get_delegated_from()), 1)
        self.assertEqual(len(event.get_attendee_by_email("somebody@else.com").get_delegated_to()), 1)
        self.assertEqual(event.get_sequence(), 1)
        self.assertIsInstance(event.get_start(), datetime.datetime)
        self.assertEqual(str(event.get_start()), "2013-08-13 10:00:00+01:00")
        self.assertEqual(str(event.get_end()), "2013-08-13 14:00:00+01:00")
        self.assertTrue(event.is_recurring())

        exceptions = event.get_exceptions()
        self.assertEqual(len(exceptions), 1)

        exception = exceptions[0]
        self.assertIsInstance(exception.get_recurrence_id(), datetime.datetime)
        self.assertTrue(exception.thisandfuture)
        self.assertEqual(str(exception.get_start()), "2014-08-16 13:00:00+01:00")
        self.assertEqual(exception.get_attendee_by_email("jane@example.org").get_participant_status(), kolabformat.PartDeclined)
        self.assertRaises(ValueError, exception.get_attendee, "somebody@else.com")

        # get instances with exception data
        occurrence = event.get_next_instance(exception.get_start() - datetime.timedelta(days=1))
        self.assertEqual(occurrence.get_start(), exception.get_start())
        self.assertEqual(occurrence.get_summary(), "exception")

        # find instance directly by date
        _recurrence_id = datetime.datetime(2014, 8, 15, 10, 0, 0)
        occurrence = event.get_instance(_recurrence_id)
        self.assertIsInstance(occurrence, Event)
        self.assertEqual(str(occurrence.get_recurrence_id()), "2014-08-15 10:00:00+01:00")

        # set invalid date-only recurrence-id
        exception.set_recurrence_id(datetime.date(2014, 8, 16))
        event.add_exception(exception)

        inst = event.get_next_instance(_recurrence_id)
        self.assertIsInstance(inst, Event)
        self.assertIsInstance(inst.get_recurrence_id(), datetime.datetime)

    def test_023_load_from_message(self):
        event = event_from_message(event_from_ical(ical_event).to_message())
        event.set_sequence(3)

        message = event.to_message()
        self.assertTrue(message.is_multipart())

        # check attachment MIME parts are kept
        parts = [p for p in message.walk()]
        attachments = event.get_attachments()

        self.assertEqual(len(parts), 5)
        self.assertEqual(parts[3].get_content_type(), 'image/png')
        self.assertEqual(parts[3]['Content-ID'].strip('<>'), attachments[0].uri()[4:])
        self.assertEqual(parts[4].get_content_type(), 'text/plain')
        self.assertEqual(parts[4]['Content-ID'].strip('<>'), attachments[1].uri()[4:])
        self.assertEqual(event.get_attachment_data(1), 'This is a text file\n')

    def test_024_bogus_itip_data(self):
        # DTSTAMP contains an invalid date/time value
        vevent = """BEGIN:VEVENT
UID:626421779C777FBE9C9B85A80D04DDFA-A4BF5BBB9FEAA271
DTSTAMP:20120713T1254140
DTSTART;TZID=Europe/London:20120713T100000
DTEND;TZID=Europe/London:20120713T110000
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailt
 o:jane.doe@example.org
ATTENDEE;ROLE=OPT-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailt
 o:user.external@example.com
SEQUENCE:1
TRANSP:OPAQUE
END:VEVENT
"""
        event = event_from_ical(vevent)
        self.assertRaises(EventIntegrityError, event.to_message)

    def test_025_to_dict(self):
        data = event_from_string(xml_event).to_dict()

        self.assertIsInstance(data, dict)
        self.assertIsInstance(data['start'], datetime.datetime)
        self.assertIsInstance(data['end'], datetime.datetime)
        self.assertIsInstance(data['created'], datetime.datetime)
        self.assertIsInstance(data['lastmodified-date'], datetime.datetime)
        self.assertEqual(data['uid'], '75c740bb-b3c6-442c-8021-ecbaeb0a025e')
        self.assertEqual(data['summary'], 'test')
        self.assertEqual(data['location'], 'Room 101')
        self.assertEqual(data['description'], 'test')
        self.assertEqual(data['priority'], 5)
        self.assertEqual(data['status'], 'CANCELLED')
        self.assertEqual(data['sequence'], 1)
        self.assertEqual(data['transparency'], False)
        self.assertEqual(data['X-GWSHOW-AS'], 'BUSY')

        self.assertIsInstance(data['organizer'], dict)
        self.assertEqual(data['organizer']['email'], 'john@example.org')

        self.assertEqual(len(data['attendee']), 2)
        self.assertIsInstance(data['attendee'][0], dict)

        self.assertEqual(len(data['attach']), 1)
        self.assertIsInstance(data['attach'][0], dict)
        self.assertEqual(data['attach'][0]['fmttype'], 'text/html')

        self.assertIsInstance(data['rrule'], dict)
        self.assertEqual(data['rrule']['freq'], 'DAILY')
        self.assertEqual(data['rrule']['interval'], 1)
        self.assertEqual(data['rrule']['wkst'], 'MO')
        self.assertIsInstance(data['rrule']['until'], datetime.date)

        self.assertIsInstance(data['alarm'], list)
        self.assertEqual(len(data['alarm']), 2)
        self.assertEqual(data['alarm'][0]['action'], 'DISPLAY')
        self.assertEqual(data['alarm'][1]['action'], 'EMAIL')
        self.assertEqual(data['alarm'][1]['trigger']['value'], '-P1D')
        self.assertEqual(len(data['alarm'][1]['attendee']), 1)

    def test_026_compute_diff(self):
        e1 = event_from_string(xml_event)
        e2 = event_from_string(xml_event)

        e2.set_summary("test2")
        e2.set_end(e1.get_end() + datetime.timedelta(hours=3))
        e2.set_sequence(e1.get_sequence() + 1)
        e2.set_attendee_participant_status("jane@example.org", "DECLINED")
        e2.set_lastmodified()

        diff = compute_diff(e1.to_dict(), e2.to_dict(), True)
        self.assertEqual(len(diff), 5, "Diff: (length: %d):\r\n%r\r\n%r" % (len(diff), diff, e2.__str__()))

        ps = self._find_prop_in_list(diff, 'summary')
        self.assertIsInstance(ps, OrderedDict)
        self.assertEqual(ps['new'], "test2")

        pa = self._find_prop_in_list(diff, 'attendee')
        self.assertIsInstance(pa, OrderedDict)
        self.assertEqual(pa['index'], 0)
        self.assertEqual(pa['new'], dict(partstat='DECLINED'))

    def test_026_property_to_string(self):
        data = event_from_string(xml_event).to_dict()
        self.assertEqual(property_to_string('sequence', data['sequence']), "1")
        self.assertEqual(property_to_string('start', data['start']), "2013-08-13 10:00 (BST)")
        self.assertEqual(property_to_string('organizer', data['organizer']), "Doe, John")
        self.assertEqual(property_to_string('attendee', data['attendee'][0]), "jane@example.org, Accepted")
        self.assertEqual(property_to_string('rrule', data['rrule']), "Every 1 day(s) until 2015-07-25")
        self.assertEqual(property_to_string('exdate', data['exdate'][0]), "2014-07-19")
        self.assertEqual(property_to_string('alarm', data['alarm'][0]), "Display message 2 hour(s) before")
        self.assertEqual(property_to_string('attach', data['attach'][0]), "noname.1395223627.5555")

    def test_027_merge_attendee_data(self):
        event = event_from_string(xml_event)

        jane = event.get_attendee("jane@example.org")
        jane.set_participant_status('TENTATIVE')
        jack = Attendee("jack@example.org", name="Jack", role='OPT-PARTICIPANT')
        some = event.set_attendee_participant_status("somebody@else.com", 'ACCEPTED')

        # update jane + add jack
        event.update_attendees([jane, jack])
        self.assertEqual(len(event.get_attendees()), 3)
        self.assertEqual(event.get_attendee("jane@example.org").get_participant_status(), kolabformat.PartTentative)
        self.assertEqual(event.get_attendee("somebody@else.com").get_participant_status(), kolabformat.PartAccepted)

        # test write + read
        event = event_from_string(str(event))
        exception = event.get_exceptions()[0]
        self.assertEqual(len(exception.get_attendees()), 2)
        self.assertEqual(event.get_attendee("jane@example.org").get_participant_status(), kolabformat.PartTentative)
        self.assertEqual(event.get_attendee("jack@example.org").get_name(), "Jack")
        self.assertRaises(ValueError, exception.get_attendee, "somebody@else.com")  # not addded to exception

    def test_028_rdate(self):
        event = event_from_ical(ical_event_rdate)

        self.assertTrue(event.is_recurring())
        self.assertEqual(len(event.get_recurrence_dates()), 2)
        self.assertIsInstance(event.get_recurrence_dates()[0], datetime.datetime)

        rdates = event.get_recurrence_dates()
        self.assertEqual(str(rdates[0]), "2014-05-30 11:00:00+02:00")
        self.assertEqual(str(rdates[1]), "2014-06-20 11:00:00+02:00")

        dt = datetime.datetime(2014, 8, 15, 10, 0, 0, tzinfo=pytz.timezone("Europe/Zurich"))
        event.add_recurrence_date(dt)
        rdates = event.get_recurrence_dates()
        self.assertEqual(str(rdates[2]), "2014-08-15 10:00:00+02:00")

        itip = event.as_string_itip()
        rdates = []
        for line in itip.split("\n"):
            if re.match('^RDATE', line):
                rdates.append(line.strip().split(':')[1])
                self.assertEqual("TZID=Europe/Zurich", line.split(':')[0].split(';')[1])

        self.assertEqual(rdates, ["20140530T110000", "20140620T110000", "20140815T100000"])

    def test_029_dummy_datetime(self):
        ical = """
BEGIN:VEVENT
UID:8515D49BA15EFF7DB34F080877BE11F5-D1F2672D6F04F316
DTSTAMP:00000000T000000
DTSTART:20190514T060000
DTEND:20190514T073000
SUMMARY:Summary
SEQUENCE:1
CREATED:00000000T000000
LAST-MODIFIED:00000000T000000
ORGANIZER:MAILTO:tests@test.com
END:VEVENT
"""
        event = event_from_ical(ical)
        self.assertEqual(str(event.get_lastmodified()), "1970-01-01 00:00:00+00:00")


    def _find_prop_in_list(self, diff, name):
        for prop in diff:
            if prop['property'] == name:
                return prop
        return None


if __name__ == '__main__':
    unittest.main()
