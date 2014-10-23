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

from pykolab.translate import _
from pykolab.xml import event_from_message
from pykolab.xml import todo_from_message
from pykolab.xml import participant_status_label
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
DTSTAMP:20140213T125414Z
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
DTSTAMP:20140218T125414Z
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
DTSTAMP:20140213T125414Z
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

itip_delegated = """
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
ATTENDEE;PARTSTAT=DELEGATED;DELEGATED-TO=jack@ripper.com;ROLE=NON-PARTICIPANT:mailto:%(mailto)s
ATTENDEE;PARTSTAT=%(partstat)s;DELEGATED-FROM=%(mailto)s;ROLE=REQ-PARTICIPANT:mailto:jack@ripper.com
PRIORITY:0
SEQUENCE:%(sequence)d
END:VEVENT
END:VCALENDAR
"""

itip_todo = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1-git//Sabre//Sabre VObject
 2.1.3//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VTODO
UID:%(uid)s
CREATED;VALUE=DATE-TIME:20140731T100704Z
DTSTAMP;VALUE=DATE-TIME:20140820T101333Z
DTSTART;VALUE=DATE-TIME;TZID=Europe/Berlin:%(start)s
DUE;VALUE=DATE-TIME;TZID=Europe/Berlin:%(end)s
SUMMARY:%(summary)s
SEQUENCE:%(sequence)d
PRIORITY:1
STATUS:NEEDS-ACTION
PERCENT-COMPLETE:0
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;PARTSTAT=%(partstat)s;ROLE=REQ-PARTICIPANT:mailto:%(mailto)s
END:VTODO
END:VCALENDAR
"""

itip_todo_reply = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1-git//Sabre//Sabre VObject
  2.1.3//EN
CALSCALE:GREGORIAN
METHOD:REPLY
BEGIN:VTODO
UID:%(uid)s
CREATED;VALUE=DATE-TIME:20140731T100704Z
DTSTAMP;VALUE=DATE-TIME:20140821T085424Z
DTSTART;VALUE=DATE-TIME;TZID=Europe/Berlin:%(start)s
DUE;VALUE=DATE-TIME;TZID=Europe/Berlin:%(end)s
SUMMARY:%(summary)s
SEQUENCE:%(sequence)d
PRIORITY:1
STATUS:NEEDS-ACTION
PERCENT-COMPLETE:40
ATTENDEE;PARTSTAT=%(partstat)s;ROLE=REQ-PARTICIPANT;CUTYPE=INDIVIDUAL:mailto:%(mailto)s
ORGANIZER;CN="Doe, John":mailto:%(organizer)s
END:VTODO
END:VCALENDAR
"""

itip_todo_cancel = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.1-git//Sabre//Sabre VObject
 2.1.3//EN
CALSCALE:GREGORIAN
METHOD:CANCEL
BEGIN:VTODO
UID:%(uid)s
CREATED;VALUE=DATE-TIME:20140731T100704Z
DTSTAMP;VALUE=DATE-TIME:20140820T101333Z
SUMMARY:%(summary)s
SEQUENCE:%(sequence)d
PRIORITY:1
STATUS:CANCELLED
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;PARTSTAT=ACCEPTED;ROLE=REQ-PARTICIPANT:mailto:%(mailto)s
END:VTODO
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
    itip_reply_subject = None

    @classmethod
    def setUp(self):
        """ Compatibility for twisted.trial.unittest
        """
        if not self.john:
            self.setup_class()

    @classmethod
    def setup_class(self, *args, **kw):
        # set language to default
        pykolab.translate.setUserLanguage(conf.get('kolab','default_locale'))

        self.itip_reply_subject = _('"%(summary)s" has been %(status)s')

        from tests.functional.purge_users import purge_users
        purge_users()

        self.john = {
            'displayname': 'John Doe',
            'mail': 'john.doe@example.org',
            'dn': 'uid=doe,ou=People,dc=example,dc=org',
            'preferredlanguage': 'en_US',
            'mailbox': 'user/john.doe@example.org',
            'kolabcalendarfolder': 'user/john.doe/Calendar@example.org',
            'kolabtasksfolder': 'user/john.doe/Tasks@example.org',
            'kolabinvitationpolicy': ['ACT_UPDATE_AND_NOTIFY','ACT_MANUAL']
        }

        self.jane = {
            'displayname': 'Jane Manager',
            'mail': 'jane.manager@example.org',
            'dn': 'uid=manager,ou=People,dc=example,dc=org',
            'preferredlanguage': 'en_US',
            'mailbox': 'user/jane.manager@example.org',
            'kolabcalendarfolder': 'user/jane.manager/Calendar@example.org',
            'kolabtasksfolder': 'user/jane.manager/Tasks@example.org',
            'kolabconfidentialcalendar': 'user/jane.manager/Calendar/Confidential@example.org',
            'kolabinvitationpolicy': ['ACT_ACCEPT_IF_NO_CONFLICT','ACT_REJECT_IF_CONFLICT','TASK_ACCEPT','ACT_UPDATE']
        }

        self.jack = {
            'displayname': 'Jack Tentative',
            'mail': 'jack.tentative@example.org',
            'dn': 'uid=tentative,ou=People,dc=example,dc=org',
            'preferredlanguage': 'en_US',
            'mailbox': 'user/jack.tentative@example.org',
            'kolabcalendarfolder': 'user/jack.tentative/Calendar@example.org',
            'kolabtasksfolder': 'user/jack.tentative/Tasks@example.org',
            'kolabinvitationpolicy': ['ACT_TENTATIVE_IF_NO_CONFLICT','ALL_SAVE_TO_FOLDER','ACT_UPDATE']
        }

        self.mark = {
            'displayname': 'Mark German',
            'mail': 'mark.german@example.org',
            'dn': 'uid=german,ou=People,dc=example,dc=org',
            'preferredlanguage': 'de_DE',
            'mailbox': 'user/mark.german@example.org',
            'kolabcalendarfolder': 'user/mark.german/Calendar@example.org',
            'kolabtasksfolder': 'user/mark.german/Tasks@example.org',
            'kolabinvitationpolicy': ['ACT_ACCEPT','ACT_UPDATE_AND_NOTIFY']
        }

        self.external = {
            'displayname': 'Bob External',
            'mail': 'bob.external@gmail.com'
        }

        from tests.functional.user_add import user_add
        user_add("John", "Doe", kolabinvitationpolicy=self.john['kolabinvitationpolicy'], preferredlanguage=self.john['preferredlanguage'])
        user_add("Jane", "Manager", kolabinvitationpolicy=self.jane['kolabinvitationpolicy'], preferredlanguage=self.jane['preferredlanguage'])
        user_add("Jack", "Tentative", kolabinvitationpolicy=self.jack['kolabinvitationpolicy'], preferredlanguage=self.jack['preferredlanguage'])
        user_add("Mark", "German", kolabinvitationpolicy=self.mark['kolabinvitationpolicy'], preferredlanguage=self.mark['preferredlanguage'])

        time.sleep(1)
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        # create confidential calendar folder for jane
        imap = IMAP()
        imap.connect(domain='example.org') # sets self.domain
        imap.user_mailbox_create_additional_folders(self.jane['mail'], {
            'Calendar/Confidential': {
                'annotations': {
                    '/shared/vendor/kolab/folder-type': "event",
                    '/private/vendor/kolab/folder-type': "event.confidential"
                }
            }
        })
        imap.disconnect()


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

    def send_itip_reply(self, uid, attendee_email, mailto, start=None, template=None, summary="test", sequence=0, partstat='ACCEPTED'):
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

    def send_itip_cancel(self, attendee_email, uid, template=None, summary="test", sequence=1):
        self.send_message((template if template is not None else itip_cancellation) % {
                'uid': uid,
                'mailto': attendee_email,
                'summary': summary,
                'sequence': sequence,
            },
            attendee_email,
            method='CANCEL')

        return uid

    def create_calendar_event(self, start=None, summary="test", sequence=0, user=None, attendees=None, folder=None):
        if start is None:
            start = datetime.datetime.now(pytz.timezone("Europe/Berlin"))
        if user is None:
            user = self.john
        if attendees is None:
            attendees = [self.jane]
        if folder is None:
            folder = user['kolabcalendarfolder']

        end = start + datetime.timedelta(hours=4)

        event = pykolab.xml.Event()
        event.set_start(start)
        event.set_end(end)
        event.set_organizer(user['mail'], user['displayname'])

        for attendee in attendees:
            event.add_attendee(attendee['mail'], attendee['displayname'], role="REQ-PARTICIPANT", participant_status="NEEDS-ACTION", rsvp=True)

        event.set_summary(summary)
        event.set_sequence(sequence)

        # create event with attachment
        vattach = event.get_attachments()
        attachment = kolabformat.Attachment()
        attachment.setLabel('attach.txt')
        attachment.setData('This is a text attachment', 'text/plain')
        vattach.append(attachment)
        event.event.setAttachments(vattach)

        imap = IMAP()
        imap.connect()

        mailbox = imap.folder_quote(folder)
        imap.set_acl(mailbox, "cyrus-admin", "lrswipkxtecda")
        imap.imap.m.select(mailbox)

        result = imap.imap.m.append(
            mailbox,
            None,
            None,
            event.to_message().as_string()
        )

        return event.get_uid()

    def create_task_assignment(self, due=None, summary="test", sequence=0, user=None, attendees=None):
        if due is None:
            due = datetime.datetime.now(pytz.timezone("Europe/Berlin")) + datetime.timedelta(days=2)
        if user is None:
            user = self.john
        if attendees is None:
            attendees = [self.jane]

        todo = pykolab.xml.Todo()
        todo.set_due(due)
        todo.set_organizer(user['mail'], user['displayname'])

        for attendee in attendees:
            todo.add_attendee(attendee['mail'], attendee['displayname'], role="REQ-PARTICIPANT", participant_status="NEEDS-ACTION", rsvp=True)

        todo.set_summary(summary)
        todo.set_sequence(sequence)

        imap = IMAP()
        imap.connect()

        mailbox = imap.folder_quote(user['kolabtasksfolder'])
        imap.set_acl(mailbox, "cyrus-admin", "lrswipkxtecda")
        imap.imap.m.select(mailbox)

        result = imap.imap.m.append(
            mailbox,
            None,
            None,
            todo.to_message().as_string()
        )

        return todo.get_uid()

    def update_calendar_event(self, uid, start=None, summary=None, sequence=0, user=None):
        if user is None:
            user = self.john

        event = self.check_user_calendar_event(user['kolabcalendarfolder'], uid)
        if event:
            if start is not None:
                event.set_start(start)
            if summary is not None:
                event.set_summary(summary)
            if sequence is not None:
                event.set_sequence(sequence)

            imap = IMAP()
            imap.connect()

            mailbox = imap.folder_quote(user['kolabcalendarfolder'])
            imap.set_acl(mailbox, "cyrus-admin", "lrswipkxtecda")
            imap.imap.m.select(mailbox)

            return imap.imap.m.append(
                mailbox,
                None,
                None,
                event.to_message().as_string()
            )

        return False

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
        return self.check_user_imap_object(mailbox, uid)

    def check_user_imap_object(self, mailbox, uid=None, type='event'):
        imap = IMAP()
        imap.connect()

        mailbox = imap.folder_quote(mailbox)
        imap.set_acl(mailbox, "cyrus-admin", "lrs")
        imap.imap.m.select(mailbox)

        found = None
        retries = 15

        while not found and retries > 0:
            retries -= 1

            typ, data = imap.imap.m.search(None, '(UNDELETED HEADER SUBJECT "%s")' % (uid) if uid else '(UNDELETED HEADER X-Kolab-Type "application/x-vnd.kolab.' + type + '")')
            for num in data[0].split():
                typ, data = imap.imap.m.fetch(num, '(RFC822)')
                object_message = message_from_string(data[0][1])

                # return matching UID or first event found
                if uid and object_message['subject'] != uid:
                    continue

                if type == 'task':
                    found = todo_from_message(object_message)
                else:
                    found = event_from_message(object_message)

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


    def test_001_invite_accept_udate(self):
        start = datetime.datetime(2014,8,13, 10,0,0)
        uid = self.send_itip_invitation(self.jane['mail'], start)

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test', 'status':participant_status_label('ACCEPTED') }, self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")

        # send update with the same sequence: no re-scheduling
        self.send_itip_update(self.jane['mail'], uid, start, summary="test updated", sequence=0, partstat='ACCEPTED')

        time.sleep(10)
        event = self.check_user_calendar_event(self.jane['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test updated")
        self.assertEqual(event.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)


    # @depends on test_001_invite_user
    def test_002_invite_conflict_reject(self):
        uid = self.send_itip_invitation(self.jane['mail'], datetime.datetime(2014,8,13, 11,0,0), summary="test2")

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test2', 'status':participant_status_label('DECLINED') }, self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test2")


    def test_003_invite_accept_tentative(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.jack['mail'], datetime.datetime(2014,7,24, 8,0,0))

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test', 'status':participant_status_label('TENTATIVE') }, self.jack['mail'])
        self.assertIsInstance(response, email.message.Message)


    def test_004_copy_to_calendar(self):
        self.purge_mailbox(self.john['mailbox'])

        self.send_itip_invitation(self.jack['mail'], datetime.datetime(2014,7,29, 8,0,0))
        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test', 'status':participant_status_label('TENTATIVE') }, self.jack['mail'])
        self.assertIsInstance(response, email.message.Message)

        # send conflicting request to jack
        uid = self.send_itip_invitation(self.jack['mail'], datetime.datetime(2014,7,29, 10,0,0), summary="test2")
        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test2', 'status':participant_status_label('DECLINED') }, self.jack['mail'])
        self.assertEqual(response, None, "No reply expected")

        event = self.check_user_calendar_event(self.jack['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test2")
        self.assertEqual(event.get_attendee(self.jack['mail']).get_participant_status(), kolabformat.PartNeedsAction)


    def test_005_invite_rescheduling_accept(self):
        self.purge_mailbox(self.john['mailbox'])

        start = datetime.datetime(2014,8,14, 9,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.send_itip_invitation(self.jane['mail'], start)

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test', 'status':participant_status_label('ACCEPTED') }, self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")

        self.purge_mailbox(self.john['mailbox'])

        # send update with new date and incremented sequence
        new_start = pytz.timezone("Europe/Berlin").localize(datetime.datetime(2014,8,15, 15,0,0))
        self.send_itip_update(self.jane['mail'], uid, new_start, summary="test", sequence=1)

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test', 'status':participant_status_label('ACCEPTED') }, self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_user_calendar_event(self.jane['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_start(), new_start)
        self.assertEqual(event.get_sequence(), 1)


    def test_005_invite_rescheduling_reject(self):
        self.purge_mailbox(self.john['mailbox'])
        self.purge_mailbox(self.jack['kolabcalendarfolder'])

        start = datetime.datetime(2014,8,9, 17,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.send_itip_invitation(self.jack['mail'], start)

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test', 'status':participant_status_label('TENTATIVE') }, self.jack['mail'])
        self.assertIsInstance(response, email.message.Message)

        # send update with new but conflicting date and incremented sequence
        self.create_calendar_event(datetime.datetime(2014,8,10, 10,30,0, tzinfo=pytz.timezone("Europe/Berlin")), user=self.jack)
        new_start = pytz.timezone("Europe/Berlin").localize(datetime.datetime(2014,8,10, 9,30,0))
        self.send_itip_update(self.jack['mail'], uid, new_start, summary="test (updated)", sequence=1)

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'test', 'status':participant_status_label('DECLINED') }, self.jack['mail'])
        self.assertEqual(response, None)

        # verify re-scheduled copy in jack's calendar with NEEDS-ACTION
        event = self.check_user_calendar_event(self.jack['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_start(), new_start)
        self.assertEqual(event.get_sequence(), 1)

        attendee = event.get_attendee(self.jack['mail'])
        self.assertTrue(attendee.get_rsvp())
        self.assertEqual(attendee.get_participant_status(), kolabformat.PartNeedsAction)


    def test_006_invitation_reply(self):
        self.purge_mailbox(self.john['mailbox'])

        start = datetime.datetime(2014,8,18, 14,30,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.john)

        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        # send a reply from jane to john
        self.send_itip_reply(uid, self.jane['mail'], self.john['mail'], start=start)

        # check for the updated event in john's calendar
        time.sleep(10)
        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        attendee = event.get_attendee(self.jane['mail'])
        self.assertIsInstance(attendee, pykolab.xml.Attendee)
        self.assertEqual(attendee.get_participant_status(), kolabformat.PartAccepted)

        # check attachments in update event
        attachments = event.get_attachments()
        self.assertEqual(len(attachments), 1)
        self.assertEqual(event.get_attachment_data(0), 'This is a text attachment')


    def test_006_invitation_reply_delegated(self):
        self.purge_mailbox(self.john['mailbox'])

        start = datetime.datetime(2014,8,28, 14,30,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.john)

        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        # send a reply from jane to john
        self.send_itip_reply(uid, self.jane['mail'], self.john['mail'], start=start, template=itip_delegated, partstat='NEEDS-ACTION')

        # check for the updated event in john's calendar
        time.sleep(10)
        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        attendee = event.get_attendee(self.jane['mail'])
        self.assertIsInstance(attendee, pykolab.xml.Attendee)
        self.assertEqual(attendee.get_participant_status(), kolabformat.PartDelegated)
        self.assertEqual(len(attendee.get_delegated_to()), 1)
        self.assertEqual(attendee.get_delegated_to(True)[0], 'jack@ripper.com')

        delegatee = event.get_attendee('jack@ripper.com')
        self.assertIsInstance(delegatee, pykolab.xml.Attendee)
        self.assertEqual(delegatee.get_participant_status(), kolabformat.PartNeedsAction)
        self.assertEqual(len(delegatee.get_delegated_from()), 1)
        self.assertEqual(delegatee.get_delegated_from(True)[0], self.jane['mail'])


    def test_007_invitation_cancel(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.jane['mail'], summary="cancelled")

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'cancelled', 'status':participant_status_label('ACCEPTED') }, self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.send_itip_cancel(self.jane['mail'], uid, summary="cancelled")

        time.sleep(10)
        event = self.check_user_calendar_event(self.jane['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "cancelled")
        self.assertEqual(event.get_status(True), 'CANCELLED')
        self.assertTrue(event.get_transparency())


    def test_008_inivtation_reply_notify(self):
        self.purge_mailbox(self.john['mailbox'])

        start = datetime.datetime(2014,8,12, 16,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.john, attendees=[self.jane, self.mark, self.jack])

        # send a reply from jane to john
        self.send_itip_reply(uid, self.jane['mail'], self.john['mail'], start=start)

        # check for notification message
        # this notification should be suppressed until mark has replied, too
        notification = self.check_message_received(_('"%s" has been updated') % ('test'), self.john['mail'])
        self.assertEqual(notification, None)

        # send a reply from mark to john
        self.send_itip_reply(uid, self.mark['mail'], self.john['mail'], start=start, partstat='ACCEPTED')

        notification = self.check_message_received(_('"%s" has been updated') % ('test'), self.john['mail'])
        self.assertIsInstance(notification, email.message.Message)

        notification_text = str(notification.get_payload());
        self.assertIn(self.jane['mail'], notification_text)
        self.assertIn(_("PENDING"), notification_text)

        self.purge_mailbox(self.john['mailbox'])

        # send a reply from mark to john
        self.send_itip_reply(uid, self.jack['mail'], self.john['mail'], start=start, partstat='ACCEPTED')

        # this triggers an additional notification
        notification = self.check_message_received(_('"%s" has been updated') % ('test'), self.john['mail'])
        self.assertIsInstance(notification, email.message.Message)

        notification_text = str(notification.get_payload());
        self.assertNotIn(_("PENDING"), notification_text)


    def test_008_notify_translated(self):
        self.purge_mailbox(self.mark['mailbox'])

        start = datetime.datetime(2014,8,12, 16,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.mark, attendees=[self.jane])

        # send a reply from jane to mark
        self.send_itip_reply(uid, self.jane['mail'], self.mark['mail'], start=start)

        # change translations to de_DE
        pykolab.translate.setUserLanguage(self.mark['preferredlanguage'])
        notification = self.check_message_received(_('"%s" has been updated') % ('test'), self.mark['mail'], self.mark['mailbox'])
        self.assertIsInstance(notification, email.message.Message)

        notification_text = str(notification.get_payload());
        self.assertIn(self.jane['mail'], notification_text)
        self.assertIn(participant_status_label("ACCEPTED")+":", notification_text)

        # reset localization
        pykolab.translate.setUserLanguage(conf.get('kolab','default_locale'))


    def test_009_outdated_reply(self):
        self.purge_mailbox(self.john['mailbox'])

        start = datetime.datetime(2014,9,2, 11,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.john, sequence=2)

        # send a reply from jane to john
        self.send_itip_reply(uid, self.jane['mail'], self.john['mail'], start=start, sequence=1)

        # verify jane's attendee status was not updated
        time.sleep(10)
        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_sequence(), 2)
        self.assertEqual(event.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartNeedsAction)


    def test_010_partstat_update_propagation(self):
        # ATTENTION: this test requires wallace.invitationpolicy_autoupdate_other_attendees_on_reply to be enabled in config

        start = datetime.datetime(2014,8,21, 13,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.john, attendees=[self.jane, self.jack, self.external])

        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        # send invitations to jack and jane
        event_itip = event.as_string_itip()
        self.send_itip_invitation(self.jane['mail'], start, template=event_itip)
        self.send_itip_invitation(self.jack['mail'], start, template=event_itip)

        # wait for replies from jack and jane to be processed and propagated
        time.sleep(10)
        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        # check updated event in organizer's calendar
        self.assertEqual(event.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)
        self.assertEqual(event.get_attendee(self.jack['mail']).get_participant_status(), kolabformat.PartTentative)

        # check updated partstats in jane's calendar
        janes = self.check_user_calendar_event(self.jane['kolabcalendarfolder'], uid)
        self.assertEqual(janes.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)
        self.assertEqual(janes.get_attendee(self.jack['mail']).get_participant_status(), kolabformat.PartTentative)

        # check updated partstats in jack's calendar
        jacks = self.check_user_calendar_event(self.jack['kolabcalendarfolder'], uid)
        self.assertEqual(jacks.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)
        self.assertEqual(jacks.get_attendee(self.jack['mail']).get_participant_status(), kolabformat.PartTentative)

        # PART 2: create conflicting event in jack's calendar
        new_start = datetime.datetime(2014,8,21, 6,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        self.create_calendar_event(new_start, user=self.jack, attendees=[], summary="blocker")

        # re-schedule initial event to new date
        self.update_calendar_event(uid, start=new_start, sequence=1, user=self.john)
        self.send_itip_update(self.jane['mail'], uid, new_start, summary="test (updated)", sequence=1)
        self.send_itip_update(self.jack['mail'], uid, new_start, summary="test (updated)", sequence=1)

        # wait for replies to be processed and propagated
        time.sleep(10)
        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        # check updated event in organizer's calendar (jack didn't reply yet)
        self.assertEqual(event.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)
        self.assertEqual(event.get_attendee(self.jack['mail']).get_participant_status(), kolabformat.PartTentative)

        # check partstats in jack's calendar: jack's status should remain needs-action
        jacks = self.check_user_calendar_event(self.jack['kolabcalendarfolder'], uid)
        self.assertEqual(jacks.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)
        self.assertEqual(jacks.get_attendee(self.jack['mail']).get_participant_status(), kolabformat.PartNeedsAction)


    def test_011_manual_schedule_auto_update(self):
        self.purge_mailbox(self.john['mailbox'])

        # create an event in john's calendar as it was manually accepted
        start = datetime.datetime(2014,9,2, 11,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_calendar_event(start, user=self.jane, sequence=1, folder=self.john['kolabcalendarfolder'])

        # send update with the same sequence: no re-scheduling
        templ = itip_invitation.replace("RSVP=TRUE", "RSVP=FALSE").replace("Doe, John", self.jane['displayname']).replace("john.doe@example.org", self.jane['mail'])
        self.send_itip_update(self.john['mail'], uid, start, summary="test updated", sequence=1, partstat='ACCEPTED', template=templ)

        time.sleep(10)
        event = self.check_user_calendar_event(self.john['kolabcalendarfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test updated")
        self.assertEqual(event.get_attendee(self.john['mail']).get_participant_status(), kolabformat.PartAccepted)

        # this should also trigger an update notification
        notification = self.check_message_received(_('"%s" has been updated') % ('test updated'), self.jane['mail'], mailbox=self.john['mailbox'])
        self.assertIsInstance(notification, email.message.Message)

        # send outdated update: should not be saved
        self.send_itip_update(self.john['mail'], uid, start, summary="old test", sequence=0, partstat='NEEDS-ACTION', template=templ)
        notification = self.check_message_received(_('"%s" has been updated') % ('old test'), self.jane['mail'], mailbox=self.john['mailbox'])
        self.assertEqual(notification, None)


    def test_012_confidential_invitation(self):
        start = datetime.datetime(2014,9,21, 9,30,0)
        uid = self.send_itip_invitation(self.jane['mail'], start, summary='confidential', template=itip_invitation.replace("DESCRIPTION:test", "CLASS:CONFIDENTIAL"))

        # check event being stored in the folder annotared with event.confidential
        event = self.check_user_calendar_event(self.jane['kolabconfidentialcalendar'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "confidential")


    def test_020_task_assignment_accept(self):
        start = datetime.datetime(2014,9,10, 19,0,0)
        uid = self.send_itip_invitation(self.jane['mail'], start, summary='work', template=itip_todo)

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'work', 'status':participant_status_label('ACCEPTED') }, self.jane['mail'])
        self.assertIsInstance(response, email.message.Message)

        todo = self.check_user_imap_object(self.jane['kolabtasksfolder'], uid, 'task')
        self.assertIsInstance(todo, pykolab.xml.Todo)
        self.assertEqual(todo.get_summary(), "work")

        # send update with the same sequence: no re-scheduling
        self.send_itip_update(self.jane['mail'], uid, start, summary='work updated', template=itip_todo, sequence=0, partstat='ACCEPTED')

        response = self.check_message_received(self.itip_reply_subject % { 'summary':'work updated', 'status':participant_status_label('ACCEPTED') }, self.jane['mail'])
        self.assertEqual(response, None)

        time.sleep(10)
        todo = self.check_user_imap_object(self.jane['kolabtasksfolder'], uid, 'task')
        self.assertIsInstance(todo, pykolab.xml.Todo)
        self.assertEqual(todo.get_summary(), "work updated")
        self.assertEqual(todo.get_attendee(self.jane['mail']).get_participant_status(), kolabformat.PartAccepted)


    def test_021_task_assignment_reply(self):
        self.purge_mailbox(self.john['mailbox'])

        due = datetime.datetime(2014,9,12, 14,0,0, tzinfo=pytz.timezone("Europe/Berlin"))
        uid = self.create_task_assignment(due, user=self.john)

        todo = self.check_user_imap_object(self.john['kolabtasksfolder'], uid, 'task')
        self.assertIsInstance(todo, pykolab.xml.Todo)

        # send a reply from jane to john
        partstat = 'COMPLETED'
        self.send_itip_reply(uid, self.jane['mail'], self.john['mail'], start=due, template=itip_todo_reply, partstat=partstat)

        # check for the updated task in john's tasklist
        time.sleep(10)
        todo = self.check_user_imap_object(self.john['kolabtasksfolder'], uid, 'task')
        self.assertIsInstance(todo, pykolab.xml.Todo)

        attendee = todo.get_attendee(self.jane['mail'])
        self.assertIsInstance(attendee, pykolab.xml.Attendee)
        self.assertEqual(attendee.get_participant_status(True), partstat)

        # this should trigger an update notification
        notification = self.check_message_received(_('"%s" has been updated') % ('test'), self.john['mail'])
        self.assertIsInstance(notification, email.message.Message)

        notification_text = str(notification.get_payload());
        self.assertIn(participant_status_label(partstat), notification_text)


    def test_022_task_cancellation(self):
        uid = self.send_itip_invitation(self.jane['mail'], summary='more work', template=itip_todo)

        time.sleep(10)
        self.send_itip_cancel(self.jane['mail'], uid, template=itip_todo_cancel, summary="cancelled")

        time.sleep(10)
        todo = self.check_user_imap_object(self.jane['kolabtasksfolder'], uid, 'task')
        self.assertIsInstance(todo, pykolab.xml.Todo)
        self.assertEqual(todo.get_summary(), "more work")
        self.assertEqual(todo.get_status(True), 'CANCELLED')

        # this should trigger a notification message
        notification = self.check_message_received(_('"%s" has been cancelled') % ('more work'), self.john['mail'], mailbox=self.jane['mailbox'])
        self.assertIsInstance(notification, email.message.Message)

