import datetime
import pytz
import sys
import unittest
import kolabformat
import icalendar

from pykolab.xml import Attendee
from pykolab.xml import Todo
from pykolab.xml import TodoIntegrityError
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
                raise AssertionError, "%s != %s" % (type(_value), _type)

    def test_001_minimal(self):
        self.todo.set_summary("test")
        self.assertEqual("test", self.todo.get_summary())
        self.assertIsInstance(self.todo.__str__(), str)

    def test_002_full(self):
        pass

    def test_010_load_from_xml(self):
        todo = todo_from_string(xml_todo)
        self.assertEqual(todo.uid, '18C2EBBD8B31D99F7AA578EDFDFB1AC0-FCBB6C4091F28CA0')
        self.assertEqual(todo.get_sequence(), 3)
        self.assertIsInstance(todo.get_due(), datetime.datetime)
        self.assertEqual(str(todo.get_due()), "2014-08-22 13:30:00+01:00")
        self.assertEqual(str(todo.get_start()), "2014-08-18 18:00:00+01:00")
        self.assertEqual(todo.get_categories(), ['iTip'])
        self.assertEqual(todo.get_attendee_by_email("john@example.org").get_participant_status(), kolabformat.PartNeedsAction)
        self.assertIsInstance(todo.get_organizer(), kolabformat.ContactReference)
        self.assertEqual(todo.get_organizer().name(), "Thomas")
        self.assertEqual(todo.get_status(True), "IN-PROCESS")


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
        #print vtodo
        todo = todo_from_ical(ical.walk('VTODO')[0].to_ical())
        self.assertEqual(todo.get_summary(), "Sample Task assignment")
        self.assertIsInstance(todo.get_start(), datetime.datetime)
        self.assertEqual(todo.get_percentcomplete(), 20)
        #print str(todo)

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