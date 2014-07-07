import time
import pykolab
import smtplib
import email
import datetime
import pytz
import uuid
import kolabformat

from pykolab.imap import IMAP
from wallace import module_resources

from email import message_from_string
from twisted.trial import unittest

import tests.functional.resource_func as funcs

conf = pykolab.getConf()

itip_invitation = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:%(uid)s
DTSTAMP:20140213T1254140
DTSTART;TZID=Europe/Berlin:%(start)s
DTEND;TZID=Europe/Berlin:%(end)s
SUMMARY:%(summary)s
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=%(partstat)s;RSVP=TRUE:mailto:%(mailto)s
ATTENDEE;ROLE=OPT-PARTICIPANT;PARTSTAT=TENTATIVE;RSVP=FALSE:mailto:somebody@else.com
TRANSP:OPAQUE
SEQUENCE:%(sequence)d
END:VEVENT
END:VCALENDAR
"""

itip_cancellation = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:CANCEL
BEGIN:VEVENT
UID:%(uid)s
DTSTAMP:20140218T1254140
DTSTART;TZID=Europe/Berlin:20120713T100000
DTEND;TZID=Europe/Berlin:20120713T110000
SUMMARY:%(summary)s
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=TRUE:mailto:%(mailto)s
TRANSP:OPAQUE
SEQUENCE:%(sequence)d
END:VEVENT
END:VCALENDAR
"""

itip_recurring = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Apple Inc.//Mac OS X 10.9.2//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:%(uid)s
DTSTAMP:20140213T1254140
DTSTART;TZID=Europe/Zurich:%(start)s
DTEND;TZID=Europe/Zurich:%(end)s
RRULE:FREQ=WEEKLY;INTERVAL=1;COUNT=10
SUMMARY:%(summary)s
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=%(partstat)s;RSVP=TRUE:mailto:%(mailto)s
TRANSP:OPAQUE
SEQUENCE:%(sequence)d
END:VEVENT
END:VCALENDAR
"""

itip_reply = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//pykolab-0.6.9-1//kolab.org//
CALSCALE:GREGORIAN
METHOD:REPLY
BEGIN:VEVENT
SUMMARY:%(summary)s
UID:%(uid)s
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:%(start)s
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:%(end)s
DTSTAMP;VALUE=DATE-TIME:20140706T171038Z
ORGANIZER;CN="Doe, John":MAILTO:%(organizer)s
ATTENDEE;CUTYPE=INDIVIDUAL;PARTSTAT=%(partstat)s;ROLE=REQ-PARTICIPANT:mailto:%(mailto)s
PRIORITY:0
SEQUENCE:%(sequence)d
END:VEVENT
END:VCALENDAR
"""

mime_message = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Tue, 25 Feb 2014 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
To: %s
Subject: "test"

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: quoted-printable

*test*

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/calendar; charset=UTF-8; method=%s; name=event.ics
Content-Disposition: attachment; filename=event.ics
Content-Transfer-Encoding: 8bit

%s
--=_c8894dbdb8baeedacae836230e3436fd--
"""

class TestWallaceInvitationpolicy(unittest.TestCase):

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
            'sender': 'John Doe <john.doe@example.org>',
            'dn': 'uid=doe,ou=People,dc=example,dc=org',
            'mailbox': 'user/john.doe@example.org',
            'kolabtargetfolder': 'user/john.doe/Calendar@example.org',
            'kolabinvitationpolicy': ['ACT_UPDATE', 'ACT_MANUAL']
        }

        self.jane = {
            'displayname': 'Jane Manager',
            'mail': 'jane.manager@example.org',
            'sender': 'Jane Manager <jane.manager@example.org>',
            'dn': 'uid=manager,ou=People,dc=example,dc=org',
            'mailbox': 'user/jane.manager@example.org',
            'kolabtargetfolder': 'user/jane.manager/Calendar@example.org',
            'kolabinvitationpolicy': ['ACT_ACCEPT_IF_NO_CONFLICT','ACT_REJECT_IF_CONFLICT', 'ACT_UPDATE']
        }

        from tests.functional.user_add import user_add
        user_add("John", "Doe", kolabinvitationpolicy=self.john['kolabinvitationpolicy'])
        user_add("Jane", "Manager", kolabinvitationpolicy=self.jane['kolabinvitationpolicy'])

        time.sleep(1)
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    def send_message(self, itip_payload, to_addr, from_addr=None, method="REQUEST"):
        if from_addr is None:
            from_addr = self.john['mail']

        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(from_addr, to_addr, mime_message % (to_addr, method, itip_payload))

    def send_itip_invitation(self, attendee_email, start=None, allday=False, template=None, summary="test", sequence=0, partstat='NEEDS-ACTION'):
        if start is None:
            start = datetime.datetime.now()

        uid = str(uuid.uuid4())

        if allday:
            default_template = itip_allday
            end = start + datetime.timedelta(days=1)
            date_format = '%Y%m%d'
        else:
            end = start + datetime.timedelta(hours=4)
            default_template = itip_invitation
            date_format = '%Y%m%dT%H%M%S'

        self.send_message((template if template is not None else default_template) % {
                'uid': uid,
                'start': start.strftime(date_format),
                'end': end.strftime(date_format),
                'mailto': attendee_email,
                'summary': summary,
                'sequence': sequence,
                'partstat': partstat
            },
            attendee_email)

        return uid

    def send_itip_update(self, attendee_email, uid, start=None, template=None, summary="test", sequence=1, partstat='ACCEPTED'):
        if start is None:
            start = datetime.datetime.now()

        end = start + datetime.timedelta(hours=4)
        self.send_message((template if template is not None else itip_invitation) % {
                'uid': uid,
                'start': start.strftime('%Y%m%dT%H%M%S'),
                'end': end.strftime('%Y%m%dT%H%M%S'),
                'mailto': attendee_email,
                'summary': summary,
                'sequence': sequence,
                'partstat': partstat
            },
            attendee_email)

        return uid

    def send_itip_reply(self, uid, mailto, attendee_email, start=None, template=None, summary="test", sequence=1, partstat='ACCEPTED'):
        if start is None:
            start = datetime.datetime.now()

        end = start + datetime.timedelta(hours=4)
        self.send_message((template if template is not None else itip_reply) % {
                'uid': uid,
                'start': start.strftime('%Y%m%dT%H%M%S'),
                'end': end.strftime('%Y%m%dT%H%M%S'),
                'mailto': attendee_email,
                'organizer': mailto,
                'summary': summary,
                'sequence': sequence,
                'partstat': partstat
            },
            mailto,
            attendee_email,
            method='REPLY')

        return uid

    def send_itip_cancel(self, attendee_email, uid, summary="test", sequence=1):
        self.send_message(itip_cancellation % {
                'uid': uid,
                'mailto': attendee_email,
                'summary': summary,
                'sequence': sequence,
            },
            attendee_email,
            method='CANCEL')

        return uid

    def create_calendar_event(self, start=None, summary="test", sequence=0, user=None, attendee=None):
        if start is None:
            start = datetime.datetime.now(pytz.timezone("Europe/Berlin"))
        if user is None:
            user = self.john
        if attendee is None:
            attendee = self.jane

        end = start + datetime.timedelta(hours=4)

        event = pykolab.xml.Event()
        event.set_start(start)
        event.set_end(end)
        event.set_organizer(user['mail'], user['displayname'])
        event.add_attendee(attendee['mail'], attendee['displayname'], role="REQ-PARTICIPANT", participant_status="NEEDS-ACTION", rsvp=True)
        event.set_summary(summary)
        event.set_sequence(sequence)

        imap = IMAP()
        imap.connect()

        mailbox = imap.folder_quote(user['kolabtargetfolder'])
        imap.set_acl(mailbox, "cyrus-admin", "lrswipkxtecda")
        imap.imap.m.select(mailbox)

        result = imap.imap.m.append(
            mailbox,
            None,
            None,
            event.to_message().as_string()
        )

        return event.get_uid()

    def check_message_received(self, subject, from_addr=None, mailbox=None):
        if mailbox is None:
            mailbox = self.john['mailbox']

        imap = IMAP()
        imap.connect()

        mailbox = imap.folder_quote(mailbox)
        imap.set_acl(mailbox, "cyrus-admin", "lrs")
        imap.imap.m.select(mailbox)

        found = None
        retries = 15

        while not found and retries > 0:
            retries -= 1

            typ, data = imap.imap.m.search(None, '(UNDELETED HEADER FROM "%s")' % (from_addr) if from_addr else 'UNDELETED')
            for num in data[0].split():
                typ, msg = imap.imap.m.fetch(num, '(RFC822)')
                message = message_from_string(msg[0][1])
                if message['Subject'] == subject:
                    found = message
                    break

            time.sleep(1)

        imap.disconnect()

        return found

    def check_user_calendar_event(self, mailbox, uid=None):
        imap = IMAP()
        imap.connect()

        mailbox = imap.folder_quote(mailbox)
        imap.set_acl(mailbox, "cyrus-admin", "lrs")
        imap.imap.m.select(mailbox)

        found = None
        retries = 15

        while not found and retries > 0:
            retries -= 1

            typ, data = imap.imap.m.search(None, '(UNDELETED HEADER SUBJECT "%s")' % (uid) if uid else '(UNDELETED HEADER X-Kolab-Type "application/x-vnd.kolab.event")')
            for num in data[0].split():
                typ, data = imap.imap.m.fetch(num, '(RFC822)')
                event_message = message_from_string(data[0][1])

                # return matching UID or first event found
                if uid and event_message['subject'] != uid:
                    continue

                for part in event_message.walk():
                    if part.get_content_type() == "application/calendar+xml":
                        payload = part.get_payload(decode=True)
                        found = pykolab.xml.event_from_string(payload)
                        break

                if found:
                    break

            time.sleep(1)

        return found

    def purge_mailbox(self, mailbox):
        imap = IMAP()
        imap.connect()
        mailbox = imap.folder_quote(mailbox)
        imap.set_acl(mailbox, "cyrus-admin", "lrwcdest")
        imap.imap.m.select(mailbox)

        typ, data = imap.imap.m.search(None, 'ALL')
        for num in data[0].split():
            imap.imap.m.store(num, '+FLAGS', '\\Deleted')

        imap.imap.m.expunge()
        imap.disconnect()


    def test_001_invite_user(self):
        start = datetime.datetime(2014,8,13, 10,0,0)
        uid = self.send_itip_invitation(self.jane['mail'], start)

        response = self.check_message_received('"test" has been ACCEPTED', self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")

        # send update with the same sequence: no re-scheduling
        self.send_itip_update(self.jane['mail'], uid, start, summary="test updated", sequence=0, partstat='ACCEPTED')

        time.sleep(10)
        event = self.check_user_calendar_event(self.jane['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test updated")
        self.assertEqual(event.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)


    # @depends on test_001_invite_user
    def test_002_invite_conflict(self):
        uid = self.send_itip_invitation(self.jane['mail'], datetime.datetime(2014,8,13, 11,0,0), summary="test2")

        response = self.check_message_received('"test2" has been DECLINED', self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test2")


    def test_003_invite_rescheduling(self):
        start = datetime.datetime(2014,8,14, 9,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.send_itip_invitation(self.jane['mail'], start)

        response = self.check_message_received('"test" has been ACCEPTED', self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")

        self.purge_mailbox(self.john['mailbox'])

        # send update with new date and incremented sequence
        new_start = datetime.datetime(2014,8,15, 15,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        self.send_itip_update(self.jane['mail'], uid, new_start, summary="test", sequence=1)

        response = self.check_message_received('"test" has been ACCEPTED', self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_start(), new_start)
        self.assertEqual(event.get_sequence(), 1)


    def test_004_invitation_reply(self):
        start = datetime.datetime(2014,8,18, 14,30,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.john)

        event = self.check_user_calendar_event(self.john['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        # send a reply from jane to john
        self.send_itip_reply(uid, self.john['mail'], self.jane['mail'], start=start)

        # check for the updated event in john's calendar
        time.sleep(10)
        event = self.check_user_calendar_event(self.john['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        attendee = event.get_attendee(self.jane['mail'])
        self.assertIsInstance(attendee, pykolab.xml.Attendee)
        self.assertEqual(attendee.get_participant_status(), kolabformat.PartAccepted)

    def test_005_invitation_cancel(self):
        uid = self.send_itip_invitation(self.jane['mail'], summary="cancelled")

        response = self.check_message_received('"cancelled" has been ACCEPTED', self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.send_itip_cancel(self.jane['mail'], uid, summary="cancelled")

        time.sleep(10)
        event = self.check_user_calendar_event(self.jane['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "cancelled")
        self.assertEqual(event.get_status(), 'CANCELLED')
        self.assertTrue(event.get_transparency())

        