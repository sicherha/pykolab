import pykolab
import logging
import datetime

from pykolab import itip
from icalendar import Calendar
from email import message
from email import message_from_string
from wallace import module_resources
from twisted.trial import unittest

# define some iTip MIME messages

itip_multipart = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <doe@example.org>
Date: Fri, 13 Jul 2012 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: resource-collection-car@example.org
Subject: "test" has been updated

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: quoted-printable

*test*

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/calendar; charset=UTF-8; method=REQUEST;
 name=event.ics
Content-Disposition: attachment;
 filename=event.ics
Content-Transfer-Encoding: quoted-printable

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:626421779C777FBE9C9B85A80D04DDFA-A4BF5BBB9FEAA271
DTSTAMP:20120713T1254140
DTSTART;TZID=3DEurope/London:20120713T100000
DTEND;TZID=3DEurope/London:20120713T110000
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN=3D"Doe, John":mailto:doe@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailt=
o:resource-collection-car@example.org
ATTENDEE;ROLE=3DOPT-PARTICIPANT;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailto:anoth=
er-resource@example.org
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR

--=_c8894dbdb8baeedacae836230e3436fd--
"""

itip_non_multipart = """Return-Path: <doe@example.org>
Sender: doe@example.org
Content-Type: text/calendar; method=REQUEST; charset=UTF-8
Content-Transfer-Encoding: quoted-printable
To: resource-collection-car@example.org
From: doe@example.org
Date: Mon, 24 Feb 2014 11:27:28 +0100
Message-ID: <1a3aa8995e83dd24cf9247e538ac913a@example.org>
Subject: test

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:626421779C777FBE9C9B85A80D04DDFA-A4BF5BBB9FEAA271
DTSTAMP:20120713T1254140
DTSTART;TZID=3DEurope/London:20120713T100000
DTEND;TZID=3DEurope/London:20120713T110000
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN=3D"Doe, John":mailto:doe@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DACCEPTED;RSVP=3DTRUE:mailt=
o:resource-collection-car@example.org
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""

conf = pykolab.getConf()

if not hasattr(conf, 'defaults'):
    conf.finalize_conf()


class TestWallaceResources(unittest.TestCase):

    def setUp(self):
        # monkey-patch the pykolab.auth module to check API calls
        # without actually connecting to LDAP
        self.patch(pykolab.auth.Auth, "connect", self._mock_nop)
        self.patch(pykolab.auth.Auth, "disconnect", self._mock_nop)
        self.patch(pykolab.auth.Auth, "find_resource", self._mock_find_resource)
        self.patch(pykolab.auth.Auth, "get_entry_attributes", self._mock_get_entry_attributes)
        self.patch(pykolab.auth.Auth, "search_entry_by_attribute", self._mock_search_entry_by_attribute)

        # intercept calls to smtplib.SMTP.sendmail()
        import smtplib
        self.patch(smtplib.SMTP, "__init__", self._mock_smtp_init)
        self.patch(smtplib.SMTP, "quit", self._mock_nop)
        self.patch(smtplib.SMTP, "connect", self._mock_smtp_init)
        self.patch(smtplib.SMTP, "sendmail", self._mock_smtp_sendmail)

        self.smtplog = []

    def _mock_nop(self, domain=None):
        pass

    def _mock_find_resource(self, address):
        if 'resource' not in address:
            return []

        (prefix, domain) = address.split('@')
        entry_dn = "cn=" + prefix + ",ou=Resources,dc=" + ",dc=".join(domain.split('.'))
        return [entry_dn]

    def _mock_get_entry_attributes(self, domain, entry, attributes):
        (_, uid) = entry.split(',')[0].split('=')
        return {'cn': uid, 'mail': uid + "@example.org", '_attrib': attributes}

    def _mock_search_entry_by_attribute(self, attr, value, **kw):
        results = []
        if value == "cn=Room 101,ou=Resources,dc=example,dc=org":
            results.append(('cn=Rooms,ou=Resources,dc=example,dc=org', {attr: value, 'owner': 'uid=doe,ou=People,dc=example,dc=org'}))
        return results

    def _mock_smtp_init(self, host=None, port=None, local_hostname=None, timeout=0):
        pass

    def _mock_smtp_sendmail(self, from_addr, to_addr, message, mail_options=None, rcpt_options=None):
        self.smtplog.append((from_addr, to_addr, message))
        return []

    def _get_ics_part(self, message):
        ics_part = None
        for part in message.walk():
            if part.get_content_type() == 'text/calendar':
                ics_part = part

        return ics_part

    def _get_ical(self, ics):
        if hasattr(Calendar, 'from_ical'):
            cal = Calendar.from_ical(ics)
        elif hasattr(Calendar, 'from_string'):
            cal = Calendar.from_string(ics)

        for e in cal.walk():
            if e.name == "VEVENT":
                return e

        return None

    def test_002_resource_record_from_email_address(self):
        res = module_resources.resource_record_from_email_address("doe@example.org")
        self.assertEqual(len(res), 0)

    def test_003_resource_records_from_itip_events(self):
        message = message_from_string(itip_multipart)
        itips = itip.events_from_message(message)

        res = module_resources.resource_records_from_itip_events(itips)
        self.assertEqual(len(res), 2, "Return resources: %r" % (res))

        res = module_resources.resource_records_from_itip_events(itips, message['To'])
        self.assertEqual(len(res), 1, "Return target resource: %r" % (res))
        self.assertEqual("cn=resource-collection-car,ou=Resources,dc=example,dc=org", res[0])

    def test_004_get_resource_owner(self):
        owner1 = module_resources.get_resource_owner({'owner': "uid=foo,ou=People,cd=example,dc=org"})
        self.assertIsInstance(owner1, dict)
        self.assertEqual("foo@example.org", owner1['mail'])
        self.assertIn("telephoneNumber", owner1['_attrib'])

        owner2 = module_resources.get_resource_owner({'owner': ["uid=john,ou=People,cd=example,dc=org", "uid=jane,ou=People,cd=example,dc=org"]})
        self.assertIsInstance(owner2, dict)
        self.assertEqual("john@example.org", owner2['mail'])

        owner3 = module_resources.get_resource_owner({'dn': "cn=cars,ou=Resources,cd=example,dc=org"})
        self.assertEqual(owner3, None)

        owner4 = module_resources.get_resource_owner({'dn': "cn=Room 101,ou=Resources,dc=example,dc=org"})
        self.assertEqual("doe@example.org", owner4['mail'])

    def test_005_send_response_accept(self):
        itip_event = itip.events_from_message(message_from_string(itip_non_multipart))
        module_resources.send_response("resource-collection-car@example.org", itip_event)

        self.assertEqual(len(self.smtplog), 1)
        self.assertEqual("resource-collection-car@example.org", self.smtplog[0][0])
        self.assertEqual("doe@example.org", self.smtplog[0][1])

        response = message_from_string(self.smtplog[0][2])
        self.assertIn("ACCEPTED".lower(), response['subject'].lower(), "Participant status in message subject: %r" % (response['subject']))
        self.assertTrue(response.is_multipart())

        # find ics part of the response
        ics_part = self._get_ics_part(response)
        self.assertIsInstance(ics_part, message.Message)
        self.assertEqual(ics_part.get_param('method'), "REPLY")

    def test_006_send_response_delegate(self):
        # delegate resource-collection-car@example.org => resource-car-audi-a4@example.org
        itip_event = itip.events_from_message(message_from_string(itip_non_multipart))[0]
        itip_event['xml'].delegate('resource-collection-car@example.org', 'resource-car-audi-a4@example.org')
        itip_event['xml'].set_attendee_participant_status(itip_event['xml'].get_attendee('resource-car-audi-a4@example.org'), "ACCEPTED")

        module_resources.send_response("resource-collection-car@example.org", itip_event)

        self.assertEqual(len(self.smtplog), 2)
        self.assertEqual("resource-collection-car@example.org", self.smtplog[0][0])
        self.assertEqual("resource-car-audi-a4@example.org", self.smtplog[1][0])

        # delegated resource responds ACCEPTED
        response1 = message_from_string(self.smtplog[0][2])
        ical1 = self._get_ical(self._get_ics_part(response1).get_payload(decode=True))
        self.assertIn("DELEGATED".lower(), response1['subject'].lower(), "Participant status in message subject: %r" % (response1['subject']))
        self.assertEqual(ical1['attendee'][1].__str__(), "MAILTO:resource-car-audi-a4@example.org")

        # resource collection responds DELEGATED
        response2 = message_from_string(self.smtplog[1][2])
        ical2 = self._get_ical(self._get_ics_part(response2).get_payload(decode=True))
        self.assertIn("ACCEPTED".lower(), response2['subject'].lower(), "Delegation message subject: %r" % (response2['subject']))
        self.assertEqual(ical2['attendee'].__str__(), "MAILTO:resource-car-audi-a4@example.org")
        self.assertEqual(ical2['attendee'].params['PARTSTAT'], u"ACCEPTED")
