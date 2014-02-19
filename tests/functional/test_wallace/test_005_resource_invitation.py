import time
import pykolab
import smtplib
import email

from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP
from wallace import module_resources

from icalendar import Calendar
from email import message_from_string
from twisted.trial import unittest

import tests.functional.resource_func as funcs

conf = pykolab.getConf()

itip_invitation = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Tue, 25 Feb 2014 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: %s
Subject: "test" has been created

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: quoted-printable

*test*

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/calendar; charset=UTF-8; method=REQUEST; name=event.ics
Content-Disposition: attachment; filename=event.ics
Content-Transfer-Encoding: 8bit

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:626421779C777FBE9C9B85A80D04DDFA-A4BF5BBB9FEAA271
DTSTAMP:20120713T1254140
DTSTART;TZID=Europe/London:20140713T100000
DTEND;TZID=Europe/London:20140713T160000
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
--=_c8894dbdb8baeedacae836230e3436fd--
"""

class TestResourceInvitation(unittest.TestCase):

    john = None

    @classmethod
    def setUp(self):
        """ Compatibility for twisted.trial.unittest
        """
        if not self.john:
            self.setup_class()

    @classmethod
    def setup_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

        self.john = {
            'displayname': 'John Doe',
            'mail': 'john.doe@example.org',
            'sender': 'John Doe <john.doe@example.org>'
        }

        from tests.functional.user_add import user_add
        user_add("John", "Doe")

        funcs.purge_resources()
        self.audi = funcs.resource_add("car", "Audi A4")
        self.passat = funcs.resource_add("car", "VW Passat")
        self.boxter = funcs.resource_add("car", "Porsche Boxter S")
        self.cars = funcs.resource_add("collection", "Company Cars", [ self.audi['dn'], self.passat['dn'], self.boxter['dn'] ])

        time.sleep(1)
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    def send_message(self, msg_source, to_addr, from_addr=None):
        if from_addr is None:
            from_addr = self.john['mail']

        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(from_addr, to_addr, msg_source)

    def send_itip_invitation(self, resource_email):
        self.send_message(itip_invitation % (resource_email, resource_email), resource_email)

    def check_message_received(self, subject):
        imap = IMAP()
        imap.connect()
        imap.set_acl("user/john.doe@example.org", "cyrus-admin", "lrs")
        imap.imap.m.select("user/john.doe@example.org")

        found = None
        max_tries = 20

        while not found and max_tries > 0:
            max_tries -= 1

            typ, data = imap.imap.m.search(None, 'ALL')
            for num in data[0].split():
                typ, msg = imap.imap.m.fetch(num, '(RFC822)')
                message = message_from_string(msg[0][1])
                if message['Subject'] == subject:
                    found = message
                    break

            time.sleep(1)

        imap.disconnect()

        return found

    def check_resource_calendar_event(self, mailbox, uid=None):
        imap = IMAP()
        imap.connect()

        imap.imap.m.select(u'"'+mailbox+'"')
        typ, data = imap.imap.m.search(None, '(UNDELETED HEADER SUBJECT "%s")' % (uid) if uid else '(UNDELETED HEADER X-Kolab-Type "application/x-vnd.kolab.event")')

        found = None

        for num in data[0].split():
            typ, data = imap.imap.m.fetch(num, '(RFC822)')
            event_message = message_from_string(data[0][1])

            for part in event_message.walk():
                # return matching UID or first event found
                if (not uid or event_message['subject'] == uid) and part.get_content_type() == "application/calendar+xml":
                    payload = part.get_payload(decode=True)
                    found = pykolab.xml.event_from_string(payload)
                    break

            if found:
                break

        imap.disconnect()

        return found


    def test_001_resource_from_email_address(self):
        resource = module_resources.resource_record_from_email_address(self.audi['mail'])
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0], self.audi['dn'])

        collection = module_resources.resource_record_from_email_address(self.cars['mail'])
        self.assertEqual(len(collection), 1)
        self.assertEqual(collection[0], self.cars['dn'])


    def test_002_invite_resource(self):
        self.send_itip_invitation(self.audi['mail'])

        response = self.check_message_received("Meeting Request ACCEPTED")
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], '626421779C777FBE9C9B85A80D04DDFA-A4BF5BBB9FEAA271')
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")
