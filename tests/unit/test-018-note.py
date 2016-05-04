import datetime
import pytz
import unittest
import kolabformat

from pykolab.xml import Note
from pykolab.xml import NoteIntegrityError
from pykolab.xml import note_from_string

xml_note = """
<note xmlns="http://kolab.org" version="3.0">
  <uid>d407f007-cb52-42cb-8e06-67f6132d718f</uid>
  <prodid>Roundcube-libkolab-1.1 Libkolabxml-1.1</prodid>
  <creation-date>2015-03-26T08:12:37Z</creation-date>
  <last-modification-date>2015-03-26T08:12:37Z</last-modification-date>
  <categories>One</categories>
  <categories>Two</categories>
  <classification>PUBLIC</classification>
  <summary>Kolab Note</summary>
  <description>&lt;!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd"&gt;
&lt;html&gt;&lt;head&gt;&lt;meta name="qrichtext" content="1" /&gt;&lt;meta http-equiv="Content-Type" /&gt;&lt;/head&gt;&lt;body&gt;
&lt;p&gt;This is a HTML note&lt;/p&gt;
&lt;/body&gt;&lt;/html&gt;</description>
  <color/>
</note>
"""


class TestNoteXML(unittest.TestCase):

    def assertIsInstance(self, _value, _type):
        if hasattr(unittest.TestCase, 'assertIsInstance'):
            return unittest.TestCase.assertIsInstance(self, _value, _type)
        else:
            if (type(_value)) == _type:
                return True
            else:
                raise AssertionError("%s != %s" % (type(_value), _type))

    def test_001_minimal(self):
        note = Note()
        note.set_summary("test")
        self.assertEqual(note.summary(), "test")
        self.assertIsInstance(note.__str__(), str)

    def test_002_full(self):
        note = Note()
        note.set_summary("test")
        note.set_description("Description")
        note.set_classification("CONFIDENTIAL")
        note.add_category("Foo")
        note.add_category("Bar")
        # print str(note)

        self.assertEqual(len(note.get_uid()), 36)
        self.assertEqual(note.summary(), "test")
        self.assertEqual(note.description(), "Description")
        self.assertEqual(note.get_classification(), "CONFIDENTIAL")
        self.assertEqual(note.get_classification(False), kolabformat.ClassConfidential)
        self.assertEqual(len(note.categories()), 2)

    def test_010_load_from_xml(self):
        note = note_from_string(xml_note)
        self.assertEqual(note.get_uid(), "d407f007-cb52-42cb-8e06-67f6132d718f")
        self.assertEqual(note.summary(), "Kolab Note")
        self.assertIsInstance(note.get_created(), datetime.datetime)
        self.assertEqual(note.get_created().tzinfo, pytz.utc)
        self.assertIsInstance(note.get_lastmodified(), datetime.datetime)
        self.assertEqual(note.get_lastmodified().tzinfo, pytz.utc)

    def test_011_to_xml(self):
        note = Note()
        with self.assertRaises(ValueError):
            note.set_classification(-1)

    def test_012_to_xml(self):
        # minimal
        note = Note()
        xml = str(note)
        self.assertTrue('<summary/>' in xml)
        self.assertTrue('<description/>' in xml)

    def test_020_to_dict(self):
        data = note_from_string(xml_note).to_dict()

        self.assertIsInstance(data, dict)
        self.assertTrue('uid' in data)
        self.assertIsInstance(data.get('created', None), datetime.datetime)
        self.assertIsInstance(data.get('lastmodified-date', None), datetime.datetime)
        self.assertEqual(data.get('summary', None), "Kolab Note")
        self.assertEqual(data.get('classification', None), 'PUBLIC')
        self.assertIsInstance(data.get('categories', None), list)
        self.assertEqual(len(data.get('categories', None)), 2)
        self.assertTrue('<p>This is a HTML note</p>' in data.get('description', None))

if __name__ == '__main__':
    unittest.main()
