import datetime
import pytz
import unittest
import kolabformat

from pykolab.xml import Contact
from pykolab.xml import ContactIntegrityError
from pykolab.xml import contact_from_string
from pykolab.xml import contact_from_message
from email import message_from_string

xml_contact = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<vcards xmlns="urn:ietf:params:xml:ns:vcard-4.0">
  <vcard>
    <uid>
      <uri>urn:uuid:437656b2-d55e-11e4-a43b-080027b7afc5</uri>
    </uid>
    <x-kolab-version>
      <text>3.1.0</text>
    </x-kolab-version>
    <prodid>
      <text>Roundcube-libkolab-1.1 Libkolabxml-1.2</text>
    </prodid>
    <rev>
      <timestamp>20150328T152236Z</timestamp>
    </rev>
    <kind>
      <text>individual</text>
    </kind>
    <fn>
      <text>Sample Dude</text>
    </fn>
    <n>
      <surname>Dude</surname>
      <given>Sample</given>
      <additional>M.</additional>
      <prefix>Dr.</prefix>
      <suffix>Jr.</suffix>
    </n>
    <note>
      <text>This is a sample contact for testing</text>
    </note>
    <title>
      <text>Head of everything</text>
    </title>
    <group name="Affiliation">
      <org>
        <text>Kolab Inc.</text>
        <text>R&amp;D Department</text>
      </org>
      <related>
        <parameters>
          <type>
            <text>x-manager</text>
          </type>
        </parameters>
        <text>Jane Manager</text>
      </related>
      <related>
        <parameters>
          <type>
            <text>x-assistant</text>
          </type>
        </parameters>
        <text>Mrs. Moneypenny</text>
      </related>
      <adr>
        <parameters/>
        <pobox/>
        <ext/>
        <street>O-steet</street>
        <locality>San Francisco</locality>
        <region>CA</region>
        <code>55550</code>
        <country>USA</country>
      </adr>
    </group>
    <url>
      <uri>www.kolab.org</uri>
    </url>
    <adr>
      <parameters>
        <type>
          <text>home</text>
        </type>
      </parameters>
      <pobox/>
      <ext/>
      <street>Homestreet 11</street>
      <locality>Hometown</locality>
      <region/>
      <code>12345</code>
      <country>Germany</country>
    </adr>
    <adr>
      <parameters>
        <type>
          <text>work</text>
        </type>
      </parameters>
      <pobox/>
      <ext/>
      <street>Workstreet 22</street>
      <locality>Worktown</locality>
      <region/>
      <code>4567</code>
      <country>Switzerland</country>
    </adr>
    <nickname>
      <text>the dude</text>
    </nickname>
    <related>
      <parameters>
        <type>
          <text>spouse</text>
        </type>
      </parameters>
      <text>Leia</text>
    </related>
    <related>
      <parameters>
        <type>
          <text>child</text>
        </type>
      </parameters>
      <text>Jay</text>
    </related>
    <related>
      <parameters>
        <type>
          <text>child</text>
        </type>
      </parameters>
      <text>Bob</text>
    </related>
    <bday>
      <date>20010401</date>
    </bday>
    <anniversary>
      <date>20100705</date>
    </anniversary>
    <photo>
      <uri>data:image/gif;base64,R0lGODlhAQABAPAAAOjq6gAAACH/C1hNUCBEYXRhWE1QAT8AIfkEBQAAAAAsAAAAAAEAAQAAAgJEAQA7</uri>
    </photo>
    <gender>
      <sex>M</sex>
    </gender>
    <tel>
      <parameters>
        <type>
          <text>home</text>
        </type>
      </parameters>
      <text>+49-555-11223344</text>
    </tel>
    <tel>
      <parameters>
        <type>
          <text>work</text>
        </type>
      </parameters>
      <text>+49-555-44556677</text>
    </tel>
    <tel>
      <parameters>
        <type>
          <text>cell</text>
        </type>
      </parameters>
      <text>+41-777-55588899</text>
    </tel>
    <impp>
      <uri>jabber:dude@kolab.org</uri>
    </impp>
    <email>
      <parameters>
        <type>
          <text>home</text>
        </type>
      </parameters>
      <text>home@kolab.org</text>
    </email>
    <email>
      <parameters>
        <type>
          <text>work</text>
        </type>
      </parameters>
      <text>work@kolab.org</text>
    </email>
    <key>
      <uri>data:application/pgp-keys;base64,LS0tLS1CRUdJTiBQR1AgUFVCTElDIEtFWSBCTE9DSy0tLS0tDQpWZXJzaW9uOiBHbnVQRy9NYWNHUEcyIHYyLjAuMjINCg0KbVFHaUJFSVNOcUVSQkFDUnovb3J5L0JEY3pBWUFUR3JnTSt5WDgzV2pkaUVrNmZKNFFUekk2ZFZ1TkxTNy4uLg0KLS0tLS1FTkQgUEdQIFBVQkxJQyBLRVkgQkxPQ0stLS0tLQ==</uri>
    </key>
  </vcard>
</vcards>
"""

contact_mime_message = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_4ff5155d75dc1328b7f5fe10ddce8d24"
From: john.doe@example.org
To: john.doe@example.org
Date: Mon, 13 Apr 2015 15:26:44 +0200
X-Kolab-Type: application/x-vnd.kolab.contact
X-Kolab-Mime-Version: 3.0
Subject: 05cfc56d-2bb3-46d1-ada4-5f5310337fb2
User-Agent: Roundcube Webmail/1.2-git

--=_4ff5155d75dc1328b7f5fe10ddce8d24
Content-Transfer-Encoding: quoted-printable
Content-Type: text/plain; charset=ISO-8859-1

This is a Kolab Groupware object. To view this object you will need an emai=
l client that understands the Kolab Groupware format. For a list of such em=
ail clients please visit http://www.kolab.org/

--=_4ff5155d75dc1328b7f5fe10ddce8d24
Content-Transfer-Encoding: 8bit
Content-Type: application/vcard+xml; charset=UTF-8;
 name=kolab.xml
Content-Disposition: attachment;
 filename=kolab.xml;
 size=1636

<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<vcards xmlns="urn:ietf:params:xml:ns:vcard-4.0">
  <vcard>
    <uid>
      <uri>urn:uuid:05cfc56d-2bb3-46d1-ada4-5f5310337fb2</uri>
    </uid>
    <x-kolab-version>
      <text>3.1.0</text>
    </x-kolab-version>
    <prodid>
      <text>Roundcube-libkolab-1.1 Libkolabxml-1.1</text>
    </prodid>
    <rev>
      <timestamp>20150413T132644Z</timestamp>
    </rev>
    <kind>
      <text>individual</text>
    </kind>
    <fn>
      <text>User One</text>
    </fn>
    <n>
      <surname>User One</surname>
      <given>DAV</given>
    </n>
    <note>
      <text>This is a Kolab contact</text>
    </note>
    <tel>
      <parameters>
        <type>
          <text>home</text>
        </type>
      </parameters>
      <text>+1555224488</text>
    </tel>
    <email>
      <parameters>
        <type>
          <text>home</text>
        </type>
      </parameters>
      <text>dav.user01@example.org</text>
    </email>
    <email>
      <parameters>
        <type>
          <text>home</text>
        </type>
      </parameters>
      <text>user.one@example.org</text>
    </email>
  </vcard>
</vcards>

--=_4ff5155d75dc1328b7f5fe10ddce8d24--
"""

class TestContactXML(unittest.TestCase):
    contact = Contact()

    def assertIsInstance(self, _value, _type):
        if hasattr(unittest.TestCase, 'assertIsInstance'):
            return unittest.TestCase.assertIsInstance(self, _value, _type)
        else:
            if (type(_value)) == _type:
                return True
            else:
                raise AssertionError, "%s != %s" % (type(_value), _type)

    def test_001_minimal(self):
        self.contact.set_name("test")
        self.assertEqual("test", self.contact.name())
        self.assertIsInstance(self.contact.__str__(), str)

    def test_002_full(self):
        self.contact.set_name("test")
        # TODO: add more setters and getter tests here

    def test_010_load_from_xml(self):
        contact = contact_from_string(xml_contact)
        self.assertEqual(contact.get_uid(), '437656b2-d55e-11e4-a43b-080027b7afc5')
        self.assertEqual(contact.name(), 'Sample Dude')

    def test_011_load_from_message(self):
        contact = contact_from_message(message_from_string(contact_mime_message))
        self.assertEqual(contact.get_uid(), '05cfc56d-2bb3-46d1-ada4-5f5310337fb2')
        self.assertEqual(contact.name(), 'User One')

    def test_020_to_dict(self):
        data = contact_from_string(xml_contact).to_dict()

        self.assertIsInstance(data, dict)
        self.assertIsInstance(data['lastmodified-date'], datetime.datetime)
        self.assertEqual(data['uid'], '437656b2-d55e-11e4-a43b-080027b7afc5')
        self.assertEqual(data['fn'], 'Sample Dude')
        self.assertEqual(data['given'], 'Sample')
        self.assertEqual(data['surname'], 'Dude')
        self.assertEqual(data['prefix'], 'Dr.')
        self.assertEqual(data['suffix'], 'Jr.')
        self.assertIsInstance(data['birthday'], datetime.date)
        self.assertIsInstance(data['anniversary'], datetime.date)
        self.assertEqual(data['organization'], 'Kolab Inc.')
        self.assertEqual(data['department'], 'R&D Department')
        self.assertEqual(data['manager'], ['Jane Manager'])
        self.assertEqual(data['note'], 'This is a sample contact for testing')
        self.assertEqual(len(data['address']), 3)
        self.assertEqual(data['address'][0]['type'], 'home')
        self.assertEqual(data['address'][1]['type'], 'work')
        self.assertEqual(data['address'][2]['type'], 'office')
        self.assertEqual(len(data['tel']), 3)
        self.assertEqual(data['tel'][0]['type'], 'home')
        self.assertEqual(data['tel'][0]['number'], '+49-555-11223344')
        self.assertEqual(data['tel'][1]['type'], 'work')
        self.assertEqual(data['tel'][2]['type'], 'mobile')
        self.assertEqual(len(data['email']), 2)
        self.assertEqual(data['email'][0]['type'], 'home')
        self.assertEqual(data['email'][0]['address'], 'home@kolab.org')
        self.assertEqual(len(data['url']), 1)
        self.assertEqual(len(data['key']), 1)
        self.assertEqual(data['key'][0]['type'], 'pgp')
        self.assertIsInstance(data['photo'], dict)
        self.assertEqual(data['photo']['mimetype'], 'image/gif')


if __name__ == '__main__':
    unittest.main()