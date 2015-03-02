# -*- coding: utf-8 -*-

import pykolab
import datetime
import pytz
import kolabformat

from pykolab import itip
from pykolab.xml import Event
from pykolab.xml import participant_status_label
from pykolab.translate import _

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
ATTENDEE;ROLE=3DOPT-PARTICIPANT;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailto:anoth=
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
DTSTAMP:20120713T125414Z
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

itip_recurring = """Return-Path: <john.doe@example.org>
Sender: john.doe@example.org
Content-Type: text/calendar; method=REQUEST; charset=UTF-8
Content-Transfer-Encoding: 8bit
From: john.doe@example.org
Date: Mon, 24 Feb 2014 11:27:28 +0100
Message-ID: <1a3aa8995e83dd24cf9247e538ac913a@example.org>
Subject: Recurring

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Apple Inc.//Mac OS X 10.9.2//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:dbdb8baeedacae836230e3436fd-5e83dd24cf92
DTSTAMP:20140213T1254140
DTSTART;TZID=Europe/London:20120709T100000
DTEND;TZID=Europe/London:20120709T120000
RRULE:FREQ=DAILY;INTERVAL=1;COUNT=5
SUMMARY:Recurring
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;CUTYPE=RESOURCE;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:jane@example.com
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""

itip_unicode = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Tue, 25 Feb 2014 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: resource-car-audia4@example.org
Subject: "test"

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: quoted-printable

*test*

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/calendar; charset=UTF-8; method=REQUEST; name=event.ics
Content-Disposition: attachment; filename=event.ics
Content-Transfer-Encoding: quoted-printable


BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube=20Webmail=200.9-0.3.el6.kolab_3.0//NONSGML=20Calendar//=
EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:eea25142-fb1c-4831-a02d-ac9fb4c16b70
DTSTAMP:20140213T125414Z
DTSTART;TZID=3DEurope/London:20140713T100000
DTEND;TZID=3DEurope/London:20140713T140000
SUMMARY:Testing =C3=9Cmlauts
DESCRIPTION:Testing =C3=9Cmlauts
LOCATION:Rue the Gen=C3=A8ve
ORGANIZER;CN=3D"D=C3=BE,=20John":mailto:john.doe@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;CUTYPE=3DRESOURCE;PARTSTAT=3DNEEDS-ACTION;R=
SVP=3DTRUE:mailto:resource-car-audia4@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DTENTATIVE;CN=3DSomebody=20Else:m=
ailto:somebody@else.com
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

class TestITip(unittest.TestCase):

    def setUp(self):
        # intercept calls to smtplib.SMTP.sendmail()
        import smtplib
        self.patch(smtplib.SMTP, "__init__", self._mock_smtp_init)
        self.patch(smtplib.SMTP, "quit", self._mock_nop)
        self.patch(smtplib.SMTP, "sendmail", self._mock_smtp_sendmail)

        self.smtplog = [];

    def _mock_nop(self, domain=None):
        pass

    def _mock_smtp_init(self, host=None, port=None, local_hostname=None, timeout=0):
        pass

    def _mock_smtp_sendmail(self, from_addr, to_addr, message, mail_options=None, rcpt_options=None):
        self.smtplog.append((from_addr, to_addr, message))


    def test_001_itip_events_from_message(self):
        itips1 = itip.events_from_message(message_from_string(itip_multipart))
        self.assertEqual(len(itips1), 1, "Multipart iTip message with text/calendar")
        self.assertEqual(itips1[0]['method'], "REQUEST", "iTip request method property")

        itips2 = itip.events_from_message(message_from_string(itip_non_multipart))
        self.assertEqual(len(itips2), 1, "Detect non-multipart iTip messages")

        itips3 = itip.events_from_message(message_from_string(itip_application_ics))
        self.assertEqual(len(itips3), 1, "Multipart iTip message with application/ics attachment")

        itips4 = itip.events_from_message(message_from_string(itip_google_multipart))
        self.assertEqual(len(itips4), 1, "Multipart iTip message from Google")

        itips5 = itip.events_from_message(message_from_string(itip_empty))
        self.assertEqual(len(itips5), 0, "Simple plain text message")

        # invalid itip blocks
        self.assertRaises(Exception, itip.events_from_message, message_from_string(itip_multipart.replace("BEGIN:VEVENT", "")))

        itips6 = itip.events_from_message(message_from_string(itip_multipart.replace("DTSTART;", "X-DTSTART;")))
        self.assertEqual(len(itips6), 0, "Event with not DTSTART")

        itips7 = itip.events_from_message(message_from_string(itip_non_multipart.replace("METHOD:REQUEST", "METHOD:PUBLISH").replace("method=REQUEST", "method=PUBLISH")))
        self.assertEqual(len(itips7), 0, "Invalid METHOD")

        # iTips with unicode data
        itips8 = itip.events_from_message(message_from_string(itip_unicode))
        self.assertEqual(len(itips8), 1)
        xml = itips8[0]['xml']
        self.assertEqual(xml.get_summary(), "Testing Ümlauts")
        self.assertEqual(xml.get_location(), "Rue the Genève")


    def test_002_check_date_conflict(self):
        astart = datetime.datetime(2014,7,13, 10,0,0)
        aend   = astart + datetime.timedelta(hours=2)

        bstart = datetime.datetime(2014,7,13, 10,0,0)
        bend   = astart + datetime.timedelta(hours=1)
        self.assertTrue(itip.check_date_conflict(astart, aend, bstart, bend))

        bstart = datetime.datetime(2014,7,13, 11,0,0)
        bend   = astart + datetime.timedelta(minutes=30)
        self.assertTrue(itip.check_date_conflict(astart, aend, bstart, bend))

        bend   = astart + datetime.timedelta(hours=2)
        self.assertTrue(itip.check_date_conflict(astart, aend, bstart, bend))

        bstart = datetime.datetime(2014,7,13, 12,0,0)
        bend   = astart + datetime.timedelta(hours=1)
        self.assertFalse(itip.check_date_conflict(astart, aend, bstart, bend))

        bstart = datetime.datetime(2014,6,13, 10,0,0)
        bend   = datetime.datetime(2014,6,14, 12,0,0)
        self.assertFalse(itip.check_date_conflict(astart, aend, bstart, bend))

        bstart = datetime.datetime(2014,7,10, 12,0,0)
        bend   = datetime.datetime(2014,7,14, 14,0,0)
        self.assertTrue(itip.check_date_conflict(astart, aend, bstart, bend))


    def test_002_check_event_conflict(self):
        itip_event = itip.events_from_message(message_from_string(itip_non_multipart))[0]

        event = Event()
        event.set_start(datetime.datetime(2012,7,13, 9,30,0, tzinfo=itip_event['start'].tzinfo))
        event.set_end(datetime.datetime(2012,7,13, 10,30,0, tzinfo=itip_event['start'].tzinfo))

        self.assertTrue(itip.check_event_conflict(event, itip_event), "Conflicting dates")

        event.set_uid(itip_event['uid'])
        self.assertFalse(itip.check_event_conflict(event, itip_event), "No conflict for same UID")

        allday = Event()
        allday.set_start(datetime.date(2012,7,13))
        allday.set_end(datetime.date(2012,7,13))

        self.assertTrue(itip.check_event_conflict(allday, itip_event), "Conflicting allday event")

        allday.set_transparency(True)
        self.assertFalse(itip.check_event_conflict(allday, itip_event), "No conflict if event is set to transparent")

        event2 = Event()
        event2.set_start(datetime.datetime(2012,7,13, 10,0,0, tzinfo=pytz.timezone("US/Central")))
        event2.set_end(datetime.datetime(2012,7,13, 11,0,0, tzinfo=pytz.timezone("US/Central")))

        self.assertFalse(itip.check_event_conflict(event, itip_event), "No conflict with timezone shift")

        rrule = kolabformat.RecurrenceRule()
        rrule.setFrequency(kolabformat.RecurrenceRule.Weekly)
        rrule.setCount(10)

        event3 = Event()
        event3.set_recurrence(rrule);
        event3.set_start(datetime.datetime(2012,6,29, 9,30,0, tzinfo=pytz.utc))
        event3.set_end(datetime.datetime(2012,6,29, 10,30,0, tzinfo=pytz.utc))

        self.assertTrue(itip.check_event_conflict(event3, itip_event), "Conflict in (3rd) recurring event instance")

        itip_event = itip.events_from_message(message_from_string(itip_recurring))[0]
        self.assertTrue(itip.check_event_conflict(event3, itip_event), "Conflict in two recurring events")

        event4 = Event()
        event4.set_recurrence(rrule);
        event4.set_start(datetime.datetime(2012,7,1, 9,30,0, tzinfo=pytz.utc))
        event4.set_end(datetime.datetime(2012,7,1, 10,30,0, tzinfo=pytz.utc))
        self.assertFalse(itip.check_event_conflict(event4, itip_event), "No conflict in two recurring events")

        itip_event = itip.events_from_message(message_from_string(itip_non_multipart))[0]

        rrule.setFrequency(kolabformat.RecurrenceRule.Daily)
        rrule.setCount(10)

        event5 = Event()
        event5.set_recurrence(rrule);
        event5.set_start(datetime.datetime(2012,7,9, 10,0,0, tzinfo=pytz.timezone("Europe/London")))
        event5.set_end(datetime.datetime(2012,7,9, 11,0,0, tzinfo=pytz.timezone("Europe/London")))

        event_xml = str(event5)
        exception = Event(from_string=event_xml)
        exception.set_start(datetime.datetime(2012,7,13, 14,0,0, tzinfo=pytz.timezone("Europe/London")))
        exception.set_end(datetime.datetime(2012,7,13, 16,0,0, tzinfo=pytz.timezone("Europe/London")))
        exception.set_recurrence_id(datetime.datetime(2012,7,13, 10,0,0, tzinfo=pytz.timezone("Europe/London")), False)
        event5.add_exception(exception)
        self.assertFalse(itip.check_event_conflict(event5, itip_event), "No conflict with exception date")

        exception = Event(from_string=event_xml)
        exception.set_start(datetime.datetime(2012,7,13, 10,0,0, tzinfo=pytz.timezone("Europe/London")))
        exception.set_end(datetime.datetime(2012,7,13, 11,0,0, tzinfo=pytz.timezone("Europe/London")))
        exception.set_status('CANCELLED')
        exception.set_recurrence_id(datetime.datetime(2012,7,13, 10,0,0, tzinfo=pytz.timezone("Europe/London")), False)
        event5.add_exception(exception)
        self.assertFalse(itip.check_event_conflict(event5, itip_event), "No conflict with cancelled exception")

    def test_002_check_event_conflict_single(self):
        itip_event = itip.events_from_message(message_from_string(itip_non_multipart))[0]

        event = Event()
        event.set_start(datetime.datetime(2012,7,10, 9,30,0, tzinfo=itip_event['start'].tzinfo))
        event.set_end(datetime.datetime(2012,7,10, 10,30,0, tzinfo=itip_event['start'].tzinfo))
        event.set_recurrence_id(event.get_start())

        dtstart = datetime.datetime(2012,7,13, 9,30,0, tzinfo=itip_event['start'].tzinfo)
        second = Event(from_string=str(event))
        second.set_start(dtstart)
        second.set_end(dtstart + datetime.timedelta(hours=1))
        second.set_recurrence_id(dtstart)
        event.add_exception(second)

        self.assertTrue(itip.check_event_conflict(event, itip_event), "Conflicting dates (exception)")

        itip_event = itip.events_from_message(message_from_string(itip_non_multipart))[0]

        dtstart = datetime.datetime(2012,7,15, 10,0,0, tzinfo=itip_event['start'].tzinfo)
        second = Event(from_string=str(itip_event['xml']))
        second.set_start(dtstart + datetime.timedelta(hours=1))
        second.set_end(dtstart + datetime.timedelta(hours=2))
        second.set_recurrence_id(dtstart)
        second.set_transparency(True)
        itip_event['xml'].add_exception(second)
        self.assertEqual(len(itip_event['xml'].get_exceptions()), 1)

        event = Event()
        event.set_start(datetime.datetime(2012,7,11, 9,30,0, tzinfo=itip_event['start'].tzinfo))
        event.set_end(datetime.datetime(2012,7,11, 10,30,0, tzinfo=itip_event['start'].tzinfo))

        self.assertFalse(itip.check_event_conflict(event, itip_event), "Conflicting dates (no)")

        event = Event()
        event.set_start(datetime.datetime(2012,7,15, 11,0,0, tzinfo=itip_event['start'].tzinfo))
        event.set_end(datetime.datetime(2012,7,15, 11,30,0, tzinfo=itip_event['start'].tzinfo))

        self.assertFalse(itip.check_event_conflict(event, itip_event), "Conflicting dates (exception)")


    def test_003_send_reply(self):
        itip_events = itip.events_from_message(message_from_string(itip_non_multipart))
        itip.send_reply("resource-collection-car@example.org", itip_events, "SUMMARY=%(summary)s; STATUS=%(status)s; NAME=%(name)s;")

        self.assertEqual(len(self.smtplog), 1)
        self.assertEqual(self.smtplog[0][0], 'resource-collection-car@example.org', "From attendee")
        self.assertEqual(self.smtplog[0][1], 'john.doe@example.org', "To organizer")

        _accepted = participant_status_label('ACCEPTED')
        message = message_from_string(self.smtplog[0][2])
        self.assertEqual(message.get('Subject'), _("Invitation for %(summary)s was %(status)s") % { 'summary':'test', 'status':_accepted })

        text = str(message.get_payload(0));
        self.assertIn('SUMMARY=3Dtest', text)
        self.assertIn('STATUS=3D' + _accepted, text)

    def test_004_send_reply_unicode(self):
        itip_events = itip.events_from_message(message_from_string(itip_non_multipart.replace('SUMMARY:test', "SUMMARY:With äöü")))
        itip.send_reply("resource-collection-car@example.org", itip_events, "SUMMARY=%(summary)s; STATUS=%(status)s; NAME=%(name)s;")

        self.assertEqual(len(self.smtplog), 1)
        self.assertIn("Subject: =?utf-8?q?Invitation_for_With_=C3=A4=C3=B6=C3=BC_was_Accepted?=", self.smtplog[0][2])
        self.assertIn('SUMMARY=3DWith =C3=A4=C3=B6=C3=BC', self.smtplog[0][2])
