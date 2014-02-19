import pykolab
import logging

from icalendar import Calendar
from email import message
from email import message_from_string
from wallace import module_resources
from twisted.trial import unittest

# define some iTip MIME messages

itip_multipart = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
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
ORGANIZER;CN=3D"Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailt=
o:resource-collection-car@example.org
ATTENDEE;ROLE=3DOPTIONAL;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailto:anoth=
er-resource@example.org
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR

--=_c8894dbdb8baeedacae836230e3436fd--
"""

itip_non_multipart = """Return-Path: <john.doe@example.org>
Sender: john.doe@example.org
Content-Type: text/calendar; method=REQUEST; charset=UTF-8
Content-Transfer-Encoding: quoted-printable
To: resource-collection-car@example.org
From: john.doe@example.org
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
ORGANIZER;CN=3D"Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DACCEPTED;RSVP=3DTRUE:mailt=
o:resource-collection-car@example.org
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""

itip_google_multipart = """MIME-Version: 1.0
Message-ID: <001a11c2ad84243e0604f3246bae@google.com>
Date: Mon, 24 Feb 2014 10:27:28 +0000
Subject: =?ISO-8859-1?Q?Invitation=3A_iTip_from_Apple_=40_Mon_Feb_24=2C_2014_12pm_?=
	=?ISO-8859-1?Q?=2D_1pm_=28Tom_=26_T=E4m=29?=
From: "john.doe" <john.doe@gmail.com>
To: <john.sample@example.org>
Content-Type: multipart/mixed; boundary=001a11c2ad84243df004f3246bad

--001a11c2ad84243df004f3246bad
Content-Type: multipart/alternative; boundary=001a11c2ad84243dec04f3246bab

--001a11c2ad84243dec04f3246bab
Content-Type: text/plain; charset=ISO-8859-1; format=flowed; delsp=yes

<some text content here>

--001a11c2ad84243dec04f3246bab
Content-Type: text/html; charset=ISO-8859-1
Content-Transfer-Encoding: quoted-printable

<div style=3D""><!-- some HTML message content here --></div>
--001a11c2ad84243dec04f3246bab
Content-Type: text/calendar; charset=UTF-8; method=REQUEST
Content-Transfer-Encoding: 7bit

BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
DTSTART:20140224T110000Z
DTEND:20140224T120000Z
DTSTAMP:20140224T102728Z
ORGANIZER:mailto:kepjllr6mcq7d0959u4cdc7000@group.calendar.google.com
UID:0BE2F640-5814-47C9-ABAE-E7E959204E76
ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=TRUE
 ;X-NUM-GUESTS=0:mailto:kepjllr6mcq7d0959u4cdc7000@group.calendar.google.com
ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=
 TRUE;CN=John Sample;X-NUM-GUESTS=0:mailto:john.sample@example.org
CREATED:20140224T102728Z
DESCRIPTION:Testing Multipart structure\\nView your event at http://www.goog
 le.com/calendar/event?action=VIEW&eid=XzYxMTRhY2k2Nm9xMzBiOWw3MG9qOGI5azZ0M
 WppYmExODkwa2FiYTU2dDJqaWQ5cDY4bzM4aDluNm8gdGhvbWFzQGJyb3RoZXJsaS5jaA&tok=N
 TIja2VwamxscjZtY3E3ZDA5NTl1NGNkYzcwMDBAZ3JvdXAuY2FsZW5kYXIuZ29vZ2xlLmNvbTkz
 NTcyYTU2YmUwNWMxNjY0Zjc3OTU0MzhmMDcwY2FhN2NjZjIzYWM&ctz=Europe/Zurich&hl=en
 .
LAST-MODIFIED:20140224T102728Z
LOCATION:
SEQUENCE:5
STATUS:CONFIRMED
SUMMARY:iTip from Apple
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR

--001a11c2ad84243dec04f3246bab--
--001a11c2ad84243df004f3246bad
Content-Type: application/ics; name="invite.ics"
Content-Disposition: attachment; filename="invite.ics"
Content-Transfer-Encoding: base64

QkVHSU46VkNBTEVOREFSDQpQUk9ESUQ6LS8vR29vZ2xlIEluYy8vR29vZ2xlIENhbGVuZGFyIDcw
LjkwNTQvL0VODQpWRVJTSU9OOjIuMA0KQ0FMU0NBTEU6R1JFR09SSUFODQpNRVRIT0Q6UkVRVUVT
VA0KQkVHSU46VkVWRU5UDQpEVFNUQVJUOjIwMTQwMjI0VDExMDAwMFoNCkRURU5EOjIwMTQwMjI0
VDEyMDAwMFoNCkRUU1RBTVA6MjAxNDAyMjRUMTAyNzI4Wg0KT1JHQU5JWkVSOm1haWx0bzprZXBq
bGxyNm1jcTdkMDk1OXU0Y2RjNzAwMEBncm91cC5jYWxlbmRhci5nb29nbGUuY29tDQpVSUQ6MEJF
MkY2NDAtNTgxNC00N0M5LUFCQUUtRTdFOTU5MjA0RTc2DQpBVFRFTkRFRTtDVVRZUEU9SU5ESVZJ
RFVBTDtST0xFPVJFUS1QQVJUSUNJUEFOVDtQQVJUU1RBVD1BQ0NFUFRFRDtSU1ZQPVRSVUUNCiA7
WC1OVU0tR1VFU1RTPTA6bWFpbHRvOmtlcGpsbHI2bWNxN2QwOTU5dTRjZGM3MDAwQGdyb3VwLmNh
bGVuZGFyLmdvb2dsZS5jb20NCkFUVEVOREVFO0NVVFlQRT1JTkRJVklEVUFMO1JPTEU9UkVRLVBB
UlRJQ0lQQU5UO1BBUlRTVEFUPU5FRURTLUFDVElPTjtSU1ZQPQ0KIFRSVUU7WC1OVU0tR1VFU1RT
PTA6bWFpbHRvOnRob21hc0Bicm90aGVybGkuY2gNCkFUVEVOREVFO0NVVFlQRT1JTkRJVklEVUFM
O1JPTEU9UkVRLVBBUlRJQ0lQQU5UO1BBUlRTVEFUPU5FRURTLUFDVElPTjtSU1ZQPQ0KIFRSVUU7
Q049VGhvbWFzIEJydWVkZXJsaTtYLU5VTS1HVUVTVFM9MDptYWlsdG86cm91bmRjdWJlQGdtYWls
LmNvbQ0KQ1JFQVRFRDoyMDE0MDIyNFQxMDI3MjhaDQpERVNDUklQVElPTjpUZXN0aW5nIE11bHRp
cGFydCBzdHJ1Y3R1cmVcblZpZXcgeW91ciBldmVudCBhdCBodHRwOi8vd3d3Lmdvb2cNCiBsZS5j
b20vY2FsZW5kYXIvZXZlbnQ/YWN0aW9uPVZJRVcmZWlkPVh6WXhNVFJoWTJrMk5tOXhNekJpT1d3
M01HOXFPR0k1YXpaME0NCiBXcHBZbUV4T0Rrd2EyRmlZVFUyZERKcWFXUTVjRFk0YnpNNGFEbHVO
bThnZEdodmJXRnpRR0p5YjNSb1pYSnNhUzVqYUEmdG9rPU4NCiBUSWphMlZ3YW14c2NqWnRZM0Uz
WkRBNU5UbDFOR05rWXpjd01EQkFaM0p2ZFhBdVkyRnNaVzVrWVhJdVoyOXZaMnhsTG1OdmJUa3oN
CiBOVGN5WVRVMlltVXdOV014TmpZMFpqYzNPVFUwTXpobU1EY3dZMkZoTjJOalpqSXpZV00mY3R6
PUV1cm9wZS9adXJpY2gmaGw9ZW4NCiAuDQpMQVNULU1PRElGSUVEOjIwMTQwMjI0VDEwMjcyOFoN
CkxPQ0FUSU9OOg0KU0VRVUVOQ0U6NQ0KU1RBVFVTOkNPTkZJUk1FRA0KU1VNTUFSWTppVGlwIGZy
b20gQXBwbGUNClRSQU5TUDpPUEFRVUUNCkVORDpWRVZFTlQNCkVORDpWQ0FMRU5EQVINCg==
--001a11c2ad84243df004f3246bad--
"""

itip_application_ics = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Fri, 13 Jul 2012 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c101622@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: resource-collection-car@example.org
Subject: "test" has been updated

--=_c8894dbdb8baeedacae836230e3436fd
Content-Transfer-Encoding: quoted-printable
Content-Type: text/plain; charset=UTF-8; format=flowed

<some text here>

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: application/ics; charset=UTF-8; method=REQUEST;
 name=event.ics
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
ORGANIZER;CN=3D"Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailt=
o:resource-collection-car@example.org
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR

--=_c8894dbdb8baeedacae836230e3436fd--
"""

itip_empty = """MIME-Version: 1.0
Date: Fri, 17 Jan 2014 13:51:50 +0100
From: <john.doe@example.org>
User-Agent: Roundcube Webmail/0.9.5
To: john.sample@example.org
Subject: "test" has been sent
Message-ID: <52D92766.5040508@somedomain.com>
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 7bit

Message plain text goes here...
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

        # intercept calls to smtplib.SMTP.sendmail()
        import smtplib
        self.patch(smtplib.SMTP, "__init__", self._mock_smtp_init)
        self.patch(smtplib.SMTP, "quit", self._mock_nop)
        self.patch(smtplib.SMTP, "sendmail", self._mock_smtp_sendmail)

        self.smtplog = [];

    def _mock_nop(self, domain=None):
        pass

    def _mock_find_resource(self, address):
        (prefix, domain) = address.split('@')
        entry_dn = "uid=" + prefix + ",dc=" + ",dc=".join(domain.split('.'))
        return [ entry_dn ];

    def _mock_smtp_init(self, host=None, port=None, local_hostname=None, timeout=0):
        pass

    def _mock_smtp_sendmail(self, from_addr, to_addr, message, mail_options=None, rcpt_options=None):
        self.smtplog.append((from_addr, to_addr, message))

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

    def test_001_itip_events_from_message(self):
        itips1 = module_resources.itip_events_from_message(message_from_string(itip_multipart))
        self.assertEqual(len(itips1), 1, "Multipart iTip message with text/calendar")

        itips2 = module_resources.itip_events_from_message(message_from_string(itip_non_multipart))
        self.assertEqual(len(itips2), 1, "Detect non-multipart iTip messages")

        itips3 = module_resources.itip_events_from_message(message_from_string(itip_application_ics))
        self.assertEqual(len(itips3), 1, "Multipart iTip message with application/ics attachment")

        itips4 = module_resources.itip_events_from_message(message_from_string(itip_google_multipart))
        self.assertEqual(len(itips4), 1, "Multipart iTip message from Google")

        itips5 = module_resources.itip_events_from_message(message_from_string(itip_empty))
        self.assertEqual(len(itips5), 0, "Simple plain text message")


    def test_002_resource_record_from_email_address(self):
        res = module_resources.resource_record_from_email_address("doe@example.org")
        # assert call to (patched) pykolab.auth.Auth.find_resource()
        self.assertEqual(len(res), 1);
        self.assertEqual("uid=doe,dc=example,dc=org", res[0]);


    def test_003_resource_records_from_itip_events(self):
        message = message_from_string(itip_multipart)
        itips = module_resources.itip_events_from_message(message)

        res = module_resources.resource_records_from_itip_events(itips)
        self.assertEqual(len(res), 2, "Return all attendee resources");

        res = module_resources.resource_records_from_itip_events(itips, message['To'])
        self.assertEqual(len(res), 1, "Return only recipient resource");
        self.assertEqual("uid=resource-collection-car,dc=example,dc=org", res[0]);


    def test_004_send_response_accept(self):
        itip_event = module_resources.itip_events_from_message(message_from_string(itip_non_multipart))
        module_resources.send_response("resource-collection-car@example.org", itip_event)

        self.assertEqual(len(self.smtplog), 1);
        self.assertEqual("resource-collection-car@example.org", self.smtplog[0][0])
        self.assertEqual("john.doe@example.org", self.smtplog[0][1])

        response = message_from_string(self.smtplog[0][2])
        self.assertIn("ACCEPTED", response['subject'], "Participant status in message subject")
        self.assertTrue(response.is_multipart())

        # find ics part of the response
        ics_part = self._get_ics_part(response)
        self.assertIsInstance(ics_part, message.Message)
        self.assertEqual(ics_part.get_param('method'), "REPLY")


    def test_005_send_response_delegate(self):
        # delegate resource-collection-car@example.org => resource-car-audi-a4@example.org
        itip_event = module_resources.itip_events_from_message(message_from_string(itip_non_multipart))[0]
        itip_event['xml'].delegate('resource-collection-car@example.org', 'resource-car-audi-a4@example.org')
        itip_event['xml'].set_attendee_participant_status(itip_event['xml'].get_attendee('resource-car-audi-a4@example.org'), "ACCEPTED")

        module_resources.send_response("resource-collection-car@example.org", itip_event)

        self.assertEqual(len(self.smtplog), 2);
        self.assertEqual("resource-car-audi-a4@example.org", self.smtplog[0][0])
        self.assertEqual("resource-collection-car@example.org", self.smtplog[1][0])

        # delegated resource responds ACCEPTED
        response1 = message_from_string(self.smtplog[0][2])
        ical1 = self._get_ical(self._get_ics_part(response1).get_payload(decode=True))
        self.assertIn("ACCEPTED", response1['subject'], "Participant status in message subject")
        self.assertEqual(ical1['attendee'], "MAILTO:resource-car-audi-a4@example.org")

        # resource collection responds DELEGATED
        response2 = message_from_string(self.smtplog[1][2])
        ical2 = self._get_ical(self._get_ics_part(response2).get_payload(decode=True))
        self.assertIn("DELEGATED", response2['subject'], "Delegation message subject")
        self.assertEqual(ical2['attendee'], "MAILTO:resource-collection-car@example.org")
        self.assertEqual(ical2['attendee'].params['PARTSTAT'], "DELEGATED")

