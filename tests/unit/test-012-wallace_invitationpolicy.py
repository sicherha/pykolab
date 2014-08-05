import os
import pykolab
import logging
import time

from icalendar import Calendar
from email import message
from email import message_from_string
from wallace import module_invitationpolicy as MIP
from twisted.trial import unittest

from pykolab.auth.ldap import LDAP
from pykolab.constants import *


# define some iTip MIME messages

itip_multipart = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Fri, 13 Jul 2012 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: jane.doe@example.org
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
PRODID:-//Roundcube Webmail 1.0.1//NONSGML Calendar//EN
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
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailt=
o:jane.doe@example.org
ATTENDEE;ROLE=3DOPT-PARTICIPANT;PARTSTAT=3DNEEDS-ACTION;RSVP=3DTRUE:mailt=
user.external@example.com
SEQUENCE:1
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR

--=_c8894dbdb8baeedacae836230e3436fd--
"""

conf = pykolab.getConf()

if not hasattr(conf, 'defaults'):
    conf.finalize_conf()

class TestWallaceInvitationpolicy(unittest.TestCase):

    def setUp(self):
        # monkey-patch the pykolab.auth module to check API calls
        # without actually connecting to LDAP
        self.patch(pykolab.auth.Auth, "connect", self._mock_nop)
        self.patch(pykolab.auth.Auth, "disconnect", self._mock_nop)
        self.patch(pykolab.auth.Auth, "find_user_dn", self._mock_find_user_dn)
        self.patch(pykolab.auth.Auth, "get_entry_attributes", self._mock_get_entry_attributes)

        # intercept calls to smtplib.SMTP.sendmail()
        import smtplib
        self.patch(smtplib.SMTP, "__init__", self._mock_smtp_init)
        self.patch(smtplib.SMTP, "quit", self._mock_nop)
        self.patch(smtplib.SMTP, "sendmail", self._mock_smtp_sendmail)

        self.smtplog = [];

    def _mock_find_user_dn(self, value, kolabuser=False):
        (prefix, domain) = value.split('@')
        return "uid=" + prefix + ",ou=People,dc=" + ",dc=".join(domain.split('.'))

    def _mock_get_entry_attributes(self, domain, entry, attributes):
        (_, uid) = entry.split(',')[0].split('=')
        return { 'cn': uid, 'mail': uid + "@example.org", '_attrib': attributes }

    def _mock_nop(self, domain=None):
        pass

    def _mock_smtp_init(self, host=None, port=None, local_hostname=None, timeout=0):
        pass

    def _mock_smtp_sendmail(self, from_addr, to_addr, message, mail_options=None, rcpt_options=None):
        self.smtplog.append((from_addr, to_addr, message))

    def test_001_itip_events_from_message(self):
        itips = pykolab.itip.events_from_message(message_from_string(itip_multipart))
        self.assertEqual(len(itips), 1, "Multipart iTip message with text/calendar")
        self.assertEqual(itips[0]['method'], "REQUEST", "iTip request method property")
        self.assertEqual(len(itips[0]['attendees']), 2, "List attendees from iTip")
        self.assertEqual(itips[0]['attendees'][0], "mailto:jane.doe@example.org", "First attendee from iTip")

    def test_002_user_dn_from_email_address(self):
        res = MIP.user_dn_from_email_address("doe@example.org")
        # assert call to (patched) pykolab.auth.Auth.find_resource()
        self.assertEqual("uid=doe,ou=People,dc=example,dc=org", res);

    def test_003_get_matching_invitation_policy(self):
        user = { 'kolabinvitationpolicy': [
            'ACT_ACCEPT:example.org',
            'ACT_REJECT:gmail.com',
            'ACT_MANUAL:*'
        ] }
        self.assertEqual(MIP.get_matching_invitation_policies(user, 'a@fastmail.net'), [MIP.ACT_MANUAL])
        self.assertEqual(MIP.get_matching_invitation_policies(user, 'b@example.org'),  [MIP.ACT_ACCEPT,MIP.ACT_MANUAL])
        self.assertEqual(MIP.get_matching_invitation_policies(user, 'c@gmail.com'),    [MIP.ACT_REJECT,MIP.ACT_MANUAL])

        user = { 'kolabinvitationpolicy': ['ACT_ACCEPT:example.org', 'ACT_MANUAL:others'] }
        self.assertEqual(MIP.get_matching_invitation_policies(user, 'd@somedomain.net'), [MIP.ACT_MANUAL])

    def test_004_write_locks(self):
        user = { 'cn': 'John Doe', 'mail': "doe@example.org" }

        lock_key = MIP.get_lock_key(user, '1234567890-abcdef')
        lock_file = os.path.join(MIP.mybasepath, 'locks', lock_key + '.lock')
        MIP.set_write_lock(lock_key)

        time.sleep(1)
        self.assertTrue(os.path.isfile(lock_file))
        self.assertFalse(MIP.set_write_lock(lock_key, False))

        MIP.remove_write_lock(lock_key)
        self.assertFalse(os.path.isfile(lock_file))

    def test_005_is_auto_reply(self):
        all_manual  = [ 'ACT_MANUAL' ]
        accept_none = [ 'ACT_REJECT' ]
        accept_all  = [ 'ACT_ACCEPT', 'ACT_UPDATE' ]
        accept_cond = [ 'ACT_ACCEPT_IF_NO_CONFLICT', 'ACT_REJECT_IF_CONFLICT' ]
        accept_some = [ 'ACT_ACCEPT_IF_NO_CONFLICT', 'ACT_SAVE_TO_CALENDAR:example.org', 'ACT_REJECT_IF_CONFLICT' ]
        accept_avail = [ 'ACT_ACCEPT_IF_NO_CONFLICT', 'ACT_REJECT_IF_CONFLICT:example.org' ]

        self.assertFalse( MIP.is_auto_reply({ 'kolabinvitationpolicy':all_manual },   'user@domain.org'))
        self.assertTrue(  MIP.is_auto_reply({ 'kolabinvitationpolicy':accept_none },  'user@domain.org'))
        self.assertTrue(  MIP.is_auto_reply({ 'kolabinvitationpolicy':accept_all },   'user@domain.com'))
        self.assertTrue(  MIP.is_auto_reply({ 'kolabinvitationpolicy':accept_cond },  'user@domain.com'))
        self.assertTrue(  MIP.is_auto_reply({ 'kolabinvitationpolicy':accept_some },  'user@domain.com'))
        self.assertFalse( MIP.is_auto_reply({ 'kolabinvitationpolicy':accept_some },  'sam@example.org'))
        self.assertFalse( MIP.is_auto_reply({ 'kolabinvitationpolicy':accept_avail }, 'user@domain.com'))
        self.assertTrue(  MIP.is_auto_reply({ 'kolabinvitationpolicy':accept_avail }, 'john@example.org'))
        