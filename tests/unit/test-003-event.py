import re
import datetime
import pytz
import sys
import unittest
import kolabformat
import icalendar

from pykolab.xml import Attendee
from pykolab.xml import Event
from pykolab.xml import EventIntegrityError
from pykolab.xml import InvalidAttendeeParticipantStatusError
from pykolab.xml import InvalidEventDateError
from pykolab.xml import event_from_ical
from pykolab.xml import event_from_string
from pykolab.xml import event_from_message

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
ATTENDEE;CUTYPE=RESOURCE;PARTSTAT=NEEDS-ACTION;ROLE=OPT-PARTICIPANT;RSVP=FA
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
            <date-time>2014-07-07T01:28:23Z</date-time>
          </created>
          <dtstamp>
            <date-time>2014-07-07T01:28:23Z</date-time>
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
            <date-time>2014-08-13T10:00:00</date-time>
          </dtstart>
          <dtend>
            <parameters>
              <tzid><text>/kolab.org/Europe/London</text></tzid>
            </parameters>
            <date-time>2014-08-13T14:00:00</date-time>
          </dtend>
          <rrule>
            <recur>
              <freq>DAILY</freq>
              <until>
                <date>2014-07-25</date>
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
            </parameters>
            <cal-address>mailto:%3Cjane%40example.org%3E</cal-address>
          </attendee>
          <attendee>
            <parameters>
              <partstat><text>TENTATIVE</text></partstat>
              <role><text>OPT-PARTICIPANT</text></role>
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
                  <cal-address>mailto:%3Cjohn.die%40example.org%3E</cal-address>
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
    </components>
  </vcalendar>
</icalendar>
"""

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

    def test_018_load_from_ical(self):
        ical_str = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1-git//Sabre//Sabre VObject
  2.1.3//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
        """ + ical_event + "END:VCALENDAR"

        ical = icalendar.Calendar.from_ical(ical_str)
        event = event_from_ical(ical.walk('VEVENT')[0].to_ical())

        self.assertEqual(event.get_location(), "Location")
        self.assertEqual(str(event.get_lastmodified()), "2014-04-07 12:23:11+00:00")
        self.assertEqual(event.get_description(), "Description\n2 lines")
        self.assertEqual(event.get_url(), "http://somelink.com/foo")
        self.assertEqual(event.get_transparency(), False)
        self.assertEqual(event.get_categories(), ["Personal"])
        self.assertEqual(event.get_priority(), '2')
        self.assertEqual(event.get_classification(), kolabformat.ClassPublic)
        self.assertEqual(event.get_attendee_by_email("max@imum.com").get_cutype(), kolabformat.CutypeResource)
        self.assertEqual(event.get_sequence(), 2)
        self.assertTrue(event.is_recurring())
        self.assertIsInstance(event.get_duration(), datetime.timedelta)
        self.assertIsInstance(event.get_end(), datetime.datetime)
        self.assertEqual(str(event.get_end()), "2014-05-23 12:30:00+01:00")
        self.assertEqual(len(event.get_exception_dates()), 2)
        self.assertIsInstance(event.get_exception_dates()[0], datetime.datetime)
        self.assertEqual(len(event.get_alarms()), 1)
        self.assertEqual(len(event.get_attachments()), 2)

    def test_018_ical_to_message(self):
        event = event_from_ical(ical_event)
        message = event.to_message()

        self.assertTrue(message.is_multipart())
        self.assertEqual(message['Subject'], event.uid)
        self.assertEqual(message['X-Kolab-Type'], 'application/x-vnd.kolab.event')

        parts = [p for p in message.walk()]
        attachments = event.get_attachments();

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
        self.event.add_custom_property('X-Custom', 'check')

        ical = icalendar.Calendar.from_ical(self.event.as_string_itip())
        event = ical.walk('VEVENT')[0]

        self.assertEqual(event['uid'], self.event.get_uid())
        self.assertEqual(event['summary'], "test")
        self.assertEqual(event['sequence'], 3)
        self.assertEqual(event['X-CUSTOM'], "check")
        self.assertIsInstance(event['dtstamp'].dt, datetime.datetime)

    def test_020_calendaring_recurrence(self):
        rrule = kolabformat.RecurrenceRule()
        rrule.setFrequency(kolabformat.RecurrenceRule.Monthly)
        rrule.setCount(10)

        self.event = Event()
        self.event.set_recurrence(rrule);

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
        self.event.set_recurrence(rrule);

        self.assertEqual(self.event.get_last_occurrence(), None)
        self.assertIsInstance(self.event.get_last_occurrence(force=True), datetime.datetime)

        # check get_next_instance() which returns a clone of the base event
        next_instance = self.event.get_next_instance(next_date)
        self.assertIsInstance(next_instance, Event)
        self.assertEqual(self.event.get_summary(), next_instance.get_summary())
        self.assertEqual(next_instance.get_start().month, 7)
        self.assertFalse(next_instance.is_recurring())

    def test_021_calendaring_no_recurrence(self):
        _start = datetime.datetime(2014, 2, 1, 14, 30, 00, tzinfo=pytz.timezone("Europe/London"))
        self.event = Event()
        self.event.set_start(_start)
        self.event.set_end(_start + datetime.timedelta(hours=2))

        self.assertEqual(self.event.get_next_occurence(_start), None)
        self.assertEqual(self.event.get_last_occurrence(), None)

    def test_022_load_from_xml(self):
        event = event_from_string(xml_event)
        self.assertEqual(event.uid, '75c740bb-b3c6-442c-8021-ecbaeb0a025e')
        self.assertEqual(event.get_attendee_by_email("jane@example.org").get_participant_status(), kolabformat.PartAccepted)
        self.assertEqual(event.get_sequence(), 1)
        self.assertIsInstance(event.get_start(), datetime.datetime)
        self.assertEqual(str(event.get_start()), "2014-08-13 10:00:00+00:00")

    def test_023_load_from_message(self):
        event = event_from_message(event_from_ical(ical_event).to_message())
        event.set_sequence(3)

        message = event.to_message()
        self.assertTrue(message.is_multipart())

        # check attachment MIME parts are kept
        parts = [p for p in message.walk()]
        attachments = event.get_attachments();

        self.assertEqual(len(parts), 5)
        self.assertEqual(parts[3].get_content_type(), 'image/png')
        self.assertEqual(parts[3]['Content-ID'].strip('<>'), attachments[0].uri()[4:])
        self.assertEqual(parts[4].get_content_type(), 'text/plain')
        self.assertEqual(parts[4]['Content-ID'].strip('<>'), attachments[1].uri()[4:])
        self.assertEqual(event.get_attachment_data(1), 'This is a text file')

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
        self.assertEqual(data['rrule']['frequency'], 'DAILY')
        self.assertEqual(data['rrule']['interval'], 1)
        self.assertEqual(data['rrule']['wkst'], 'MO')
        self.assertIsInstance(data['rrule']['until'], datetime.date)

        self.assertIsInstance(data['alarm'], list)
        self.assertEqual(len(data['alarm']), 2)
        self.assertEqual(data['alarm'][0]['action'], 'DISPLAY')
        self.assertEqual(data['alarm'][1]['action'], 'EMAIL')
        self.assertEqual(data['alarm'][1]['trigger']['value'], '-P1D')
        self.assertEqual(len(data['alarm'][1]['attendee']), 1)


if __name__ == '__main__':
    unittest.main()
