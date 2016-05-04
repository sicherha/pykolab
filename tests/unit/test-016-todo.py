import datetime
import pytz
import sys
import unittest
import kolabformat
import icalendar

from pykolab.xml import Attendee
from pykolab.xml import Todo
from pykolab.xml import TodoIntegrityError
from pykolab.xml import InvalidEventStatusError
from pykolab.xml import todo_from_ical
from pykolab.xml import todo_from_string
from pykolab.xml import todo_from_message

ical_todo = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1-git//Sabre//Sabre VObject
 2.1.3//EN
CALSCALE:GREGORIAN
BEGIN:VTODO
UID:18C2EBBD8B31D99F7AA578EDFDFB1AC0-FCBB6C4091F28CA0
DTSTAMP;VALUE=DATE-TIME:20140820T101333Z
CREATED;VALUE=DATE-TIME:20140731T100704Z
LAST-MODIFIED;VALUE=DATE-TIME:20140820T101333Z
DTSTART;VALUE=DATE-TIME;TZID=Europe/London:20140818T180000
DUE;VALUE=DATE-TIME;TZID=Europe/London:20140822T133000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=10;BYDAY=2MO,-1WE;UNTIL=20150220T180000Z
SUMMARY:Sample Task assignment
DESCRIPTION:Summary: Sample Task assignment\\nDue Date: 08/11/14\\nDue Time:
 \\n13:30 AM
SEQUENCE:3
CATEGORIES:iTip
PRIORITY:1
STATUS:IN-PROCESS
PERCENT-COMPLETE:20
ATTENDEE;CN="Doe, John";PARTSTAT=NEEDS-ACTION;ROLE=REQ-PARTICIPANT;CUTYPE=
 INDIVIDUAL;RSVP=TRUE:mailto:john.doe@example.org
ORGANIZER;CN=Thomas:mailto:thomas.bruederli@example.org
END:VTODO
END:VCALENDAR
"""

ical_todo_attachment = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1-git//Sabre//Sabre VObject
 2.1.3//EN
CALSCALE:GREGORIAN
BEGIN:VTODO
UID:18C2EBBD8B31D99F7AA578EDFDFB1AC0-FCBB6C4091F28CA0
DTSTAMP;VALUE=DATE-TIME:20140820T101333Z
CREATED;VALUE=DATE-TIME:20140731T100704Z
LAST-MODIFIED;VALUE=DATE-TIME:20140820T101333Z
DUE;VALUE=DATE-TIME;TZID=Europe/London:20150228T133000
SUMMARY:Task with attachment
SEQUENCE:3
PRIORITY:1
STATUS:IN-PROCESS
ORGANIZER;CN=Thomas:mailto:thomas.bruederli@example.org
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
END:VTODO
END:VCALENDAR
"""

xml_todo = """
<icalendar xmlns="urn:ietf:params:xml:ns:icalendar-2.0">
  <vcalendar>
    <properties>
      <prodid>
        <text>Roundcube-libkolab-1.1 Libkolabxml-1.1</text>
      </prodid>
      <version>
        <text>2.0</text>
      </version>
      <x-kolab-version>
        <text>3.1.0</text>
      </x-kolab-version>
    </properties>
    <components>
      <vtodo>
        <properties>
          <uid>
            <text>18C2EBBD8B31D99F7AA578EDFDFB1AC0-FCBB6C4091F28CA0</text>
          </uid>
          <created>
            <date-time>2014-07-31T10:07:04Z</date-time>
          </created>
          <dtstamp>
            <date-time>2014-08-20T10:13:33Z</date-time>
          </dtstamp>
          <sequence>
            <integer>3</integer>
          </sequence>
          <class>
            <text>PUBLIC</text>
          </class>
          <categories>
            <text>iTip</text>
          </categories>
          <related-to>
            <text>9F3E68BED4A94DA2A51EE589F7FDC6C8-A4BF5BBB9FEAA271</text>
          </related-to>
          <dtstart>
            <parameters>
              <tzid><text>/kolab.org/Europe/Berlin</text></tzid>
            </parameters>
            <date-time>2014-08-18T18:00:00</date-time>
          </dtstart>
          <due>
            <parameters>
              <tzid><text>/kolab.org/Europe/Berlin</text></tzid>
            </parameters>
            <date-time>2014-08-22T13:30:00</date-time>
          </due>
          <summary>
            <text>Sample Task assignment</text>
          </summary>
          <description>
            <text>Summary: Sample Task assignment
Due Date: 08/11/14
Due Time: 13:30 AM</text>
          </description>
          <priority>
            <integer>1</integer>
          </priority>
          <status>
            <text>IN-PROCESS</text>
          </status>
          <percent-complete>
            <integer>20</integer>
          </percent-complete>
          <organizer>
            <parameters>
              <cn><text>Thomas</text></cn>
            </parameters>
            <cal-address>mailto:%3Cthomas%40example.org%3E</cal-address>
          </organizer>
          <attendee>
            <parameters>
              <cn><text>Doe, John</text></cn>
              <partstat><text>NEEDS-ACTION</text></partstat>
              <role><text>REQ-PARTICIPANT</text></role>
              <rsvp><boolean>true</boolean></rsvp>
            </parameters>
            <cal-address>mailto:%3Cjohn%40example.org%3E</cal-address>
          </attendee>
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
        </components>
      </vtodo>
    </components>
  </vcalendar>
</icalendar>
"""


class TestTodoXML(unittest.TestCase):
    todo = Todo()

    def assertIsInstance(self, _value, _type):
        if hasattr(unittest.TestCase, 'assertIsInstance'):
            return unittest.TestCase.assertIsInstance(self, _value, _type)
        else:
            if (type(_value)) == _type:
                return True
            else:
                raise AssertionError("%s != %s" % (type(_value), _type))

    def test_001_minimal(self):
        self.todo.set_summary("test")
        self.assertEqual("test", self.todo.get_summary())
        self.assertIsInstance(self.todo.__str__(), str)

    def test_002_full(self):
        self.todo.set_summary("test full")
        status = self.todo.get_status()
        self.assertEqual(status, kolabformat.StatusUndefined)
        self.assertRaises(InvalidEventStatusError, self.todo.set_status, (-1))
        self.todo.set_status(status)
        # TODO: add more setters and getter tests here

    def test_010_load_from_xml(self):
        todo = todo_from_string(xml_todo)
        self.assertEqual(todo.uid, '18C2EBBD8B31D99F7AA578EDFDFB1AC0-FCBB6C4091F28CA0')
        self.assertEqual(todo.get_sequence(), 3)
        self.assertIsInstance(todo.get_due(), datetime.datetime)
        self.assertEqual(str(todo.get_due()), "2014-08-22 13:30:00+02:00")
        self.assertEqual(str(todo.get_start()), "2014-08-18 18:00:00+02:00")
        self.assertEqual(todo.get_categories(), ['iTip'])
        self.assertEqual(todo.get_attendee_by_email("john@example.org").get_participant_status(), kolabformat.PartNeedsAction)
        self.assertIsInstance(todo.get_organizer(), kolabformat.ContactReference)
        self.assertEqual(todo.get_organizer().name(), "Thomas")
        self.assertEqual(todo.get_status(True), "IN-PROCESS")
        self.assertEqual(todo.get_related_to(), "9F3E68BED4A94DA2A51EE589F7FDC6C8-A4BF5BBB9FEAA271")

    def test_020_load_from_ical(self):
        ical_str = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1.0//Sabre//Sabre VObject
  2.1.3//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
        """ + ical_todo + "END:VCALENDAR"

        ical = icalendar.Calendar.from_ical(ical_str)
        vtodo = ical.walk('VTODO')[0]
        # print vtodo
        todo = todo_from_ical(ical.walk('VTODO')[0].to_ical())
        self.assertEqual(todo.get_summary(), "Sample Task assignment")
        self.assertIsInstance(todo.get_start(), datetime.datetime)
        self.assertEqual(todo.get_percentcomplete(), 20)
        # print str(todo)

        data = todo.to_dict()
        self.assertIsInstance(data['rrule'], dict)
        self.assertEqual(data['rrule']['freq'], 'MONTHLY')
        self.assertEqual(data['rrule']['interval'], 2)
        self.assertEqual(data['rrule']['byday'], '2MO,-1WE')
        self.assertIsInstance(data['rrule']['until'], datetime.datetime)

    def test_021_as_string_itip(self):
        self.todo.set_summary("test")
        self.todo.set_start(datetime.datetime(2014, 9, 20, 11, 00, 00, tzinfo=pytz.timezone("Europe/London")))
        self.todo.set_due(datetime.datetime(2014, 9, 23, 12, 30, 00, tzinfo=pytz.timezone("Europe/London")))
        self.todo.set_sequence(3)
        self.todo.add_custom_property('X-Custom', 'check')

        # render iCal and parse again using the icalendar lib
        ical = icalendar.Calendar.from_ical(self.todo.as_string_itip())
        vtodo = ical.walk('VTODO')[0]

        self.assertEqual(vtodo['uid'], self.todo.get_uid())
        self.assertEqual(vtodo['summary'], "test")
        self.assertEqual(vtodo['sequence'], 3)
        self.assertEqual(vtodo['X-CUSTOM'], "check")
        self.assertIsInstance(vtodo['due'].dt, datetime.datetime)
        self.assertIsInstance(vtodo['dtstamp'].dt, datetime.datetime)

    def test_022_ical_with_attachment(self):
        todo = todo_from_ical(ical_todo_attachment)

        vattachment = todo.get_attachments()
        self.assertEqual(len(vattachment), 1)

        attachment = vattachment[0]
        self.assertEqual(attachment.mimetype(), 'image/png')
        self.assertEqual(attachment.label(), 'silhouette.png')

    def test_030_to_dict(self):
        data = todo_from_string(xml_todo).to_dict()

        self.assertIsInstance(data, dict)
        self.assertIsInstance(data['start'], datetime.datetime)
        self.assertIsInstance(data['due'], datetime.datetime)
        self.assertEqual(data['uid'], '18C2EBBD8B31D99F7AA578EDFDFB1AC0-FCBB6C4091F28CA0')
        self.assertEqual(data['summary'], 'Sample Task assignment')
        self.assertEqual(data['description'], "Summary: Sample Task assignment\nDue Date: 08/11/14\nDue Time: 13:30 AM")
        self.assertEqual(data['priority'], 1)
        self.assertEqual(data['sequence'], 3)
        self.assertEqual(data['status'], 'IN-PROCESS')

        self.assertIsInstance(data['alarm'], list)
        self.assertEqual(len(data['alarm']), 1)
        self.assertEqual(data['alarm'][0]['action'], 'DISPLAY')

if __name__ == '__main__':
    unittest.main()
