import unittest

from pykolab.xml import Todo
from pykolab.xml.utils import compute_diff
from pykolab.xml.utils import order_proplists

xml_todo_01 = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
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
            <text>E49000485B9EE3299A8870AD6A3E75E5-A4BF5BBB9FEAA271</text>
          </uid>
          <created>
            <date-time>2015-03-25T10:32:18Z</date-time>
          </created>
          <dtstamp>
            <date-time>2015-03-25T16:09:11Z</date-time>
          </dtstamp>
          <sequence>
            <integer>0</integer>
          </sequence>
          <summary>
            <text>Old attachments</text>
          </summary>
          <attach>
            <parameters>
              <fmttype>
                <text>image/png</text>
              </fmttype>
              <x-label>
                <text>silhouette.png</text>
              </x-label>
            </parameters>
            <uri>cid:silhouette.1427297477.7514.png</uri>
          </attach>
          <attach>
            <parameters>
              <fmttype>
                <text>text/plain</text>
              </fmttype>
              <x-label>
                <text>notes.txt</text>
              </x-label>
            </parameters>
            <uri>cid:notes.1427298885.9012.txt</uri>
          </attach>
          <attach>
            <parameters>
              <fmttype>
                <text>image/gif</text>
              </fmttype>
              <x-label>
                <text>landspeeder-lego-icon.gif</text>
              </x-label>
            </parameters>
            <uri>cid:landspeeder-lego-icon.1427299751.8542.gif</uri>
          </attach>
        </properties>
      </vtodo>
    </components>
  </vcalendar>
</icalendar>
"""

xml_todo_02 = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
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
            <text>E49000485B9EE3299A8870AD6A3E75E5-A4BF5BBB9FEAA271</text>
          </uid>
          <created>
            <date-time>2015-03-25T10:32:18Z</date-time>
          </created>
          <dtstamp>
            <date-time>2015-03-25T16:09:53Z</date-time>
          </dtstamp>
          <sequence>
            <integer>1</integer>
          </sequence>
          <summary>
            <text>New attachments</text>
          </summary>
          <description>
            <text>Removed attachment</text>
          </description>
          <attach>
            <parameters>
              <fmttype>
                <text>text/plain</text>
              </fmttype>
              <x-label>
                <text>notes.txt</text>
              </x-label>
            </parameters>
            <uri>cid:notes.1427298885.9012.txt</uri>
          </attach>
          <attach>
            <parameters>
              <fmttype>
                <text>image/gif</text>
              </fmttype>
              <x-label>
                <text>landspeeder-lego-icon.gif</text>
              </x-label>
            </parameters>
            <uri>cid:landspeeder-lego-icon.1427299751.8542.gif</uri>
          </attach>
        </properties>
      </vtodo>
    </components>
  </vcalendar>
</icalendar>
"""


class TestComputeDiff(unittest.TestCase):

    def test_000_order_proplists(self):
        one = {
            "uri": "cid:one",
            "label": "one.txt"
        }
        two = {
            "uri": "cid:two",
            "label": "two.png"
        }
        three = {
            "foo": "three"
        }
        four = {
            "foo": "four"
        }

        (aa, bb) = order_proplists([one, two, four], [three, two, one, four])
        self.assertEqual(len(aa), 3)
        self.assertEqual(len(bb), 4)
        self.assertEqual(aa[0], bb[0])
        self.assertEqual(aa[1], bb[1])

        (aa, bb) = order_proplists([four, three, one, two], [two, one])
        self.assertEqual(len(aa), 4)
        self.assertEqual(len(bb), 2)
        self.assertEqual(aa[0], bb[0])
        self.assertEqual(aa[1], bb[1])

    def test_000_order_proplists2(self):
        a1 = {'code': '4567',  'locality': 'Worktown', 'country': 'Switzerland', 'region': '', 'label': '', 'street': 'Workstreet 22', 'type': 'work'}
        a2 = {'code': '55550', 'locality': 'San Francisco', 'country': 'USA', 'region': 'CA', 'label': '', 'street': 'O-steet', 'type': 'office'}
        a3 = {'code': '6666',  'locality': 'Workcity', 'country': 'Switzerland', 'region': 'ZH', 'label': '', 'street': 'Workstreet 22', 'type': 'work'}
        a4 = dict(a2)

        (aa, bb) = order_proplists([a1, a2], [a3, a4])
        self.assertEqual(aa[1], bb[1])

    def test_001_attachments(self):
        old = Todo(from_string=xml_todo_01)
        new = Todo(from_string=xml_todo_02)
        diff = compute_diff(old.to_dict(), new.to_dict())

        self.assertEqual(len(diff), 5)
        self.assertEqual(diff[0]['property'], 'sequence')
        self.assertEqual(diff[0]['old'], 0)
        self.assertEqual(diff[0]['new'], 1)

        self.assertEqual(diff[1]['property'], 'description')
        self.assertEqual(diff[1]['old'], '')

        self.assertEqual(diff[2]['property'], 'summary')
        self.assertEqual(diff[2]['old'], 'Old attachments')
        self.assertEqual(diff[2]['new'], 'New attachments')

        self.assertEqual(diff[3]['property'], 'attach')
        self.assertEqual(diff[3]['new'], None)
        self.assertEqual(diff[3]['old']['uri'], "cid:silhouette.1427297477.7514.png")

        self.assertEqual(diff[4]['property'], 'lastmodified-date')

if __name__ == '__main__':
    unittest.main()
