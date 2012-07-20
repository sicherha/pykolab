from email import message_from_string
import icalendar
import unittest

class TestICalendar(unittest.TestCase):

    def test_001_from_message_recurrence(self):
        message = message_from_string("""Received: from localhost (localhost [127.0.0.1])
    by kolab.example.org (Postfix) with ESMTP id 513B942E10
    for <resource-collection-car@example.org>; Fri, 13 Jul 2012 14:54:16 +0200 (CEST)
X-Virus-Scanned: amavisd-new at example.org
X-Spam-Flag: NO
X-Spam-Score: 0.551
X-Spam-Level:
X-Spam-Status: No, score=0.551 tagged_above=-10 required=6.2
    tests=[ALL_TRUSTED=-1, DNS_FROM_RFC_DSN=0.001,
    NORMAL_HTTP_TO_IP=0.001, TVD_RCVD_IP=0.054, TVD_RCVD_IP4=1.495]
    autolearn=no
Received: from kolab.example.org ([127.0.0.1])
    by localhost (kolab.example.org [127.0.0.1]) (amavisd-new, port 10024)
    with ESMTP id KNJgv841fj-1 for <resource-collection-car@example.org>;
    Fri, 13 Jul 2012 14:54:15 +0200 (CEST)
Received: from 192.168.122.228 (localhost [127.0.0.1])
    (Authenticated sender: john.doe@example.org)
    by kolab.example.org (Postfix) with ESMTPSA id 0EBDA42E39
    for <resource-collection-car@example.org>; Fri, 13 Jul 2012 14:54:14 +0200 (CEST)
MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Fri, 13 Jul 2012 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
X-Sender: john.doe@example.org
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: resource-collection-car@example.org
Subject: "test" has been updated

--=_c8894dbdb8baeedacae836230e3436fd
Content-Transfer-Encoding: quoted-printable
Content-Type: text/plain; charset=UTF-8;
 format=flowed

*test*

When: 2012-07-13 10:00 - 11:00 (Europe/London)

Invitees: Doe, John <john.doe@example.org>,=20
resource-collection-car@example.org

Please find attached an iCalendar file with the updated event details which=
=20
you can import to your calendar application.

In case your email client doesn't support iTip requests you can use the=20
following link to either accept or decline this invitation:
http://192.168.122.228/roundcubemail/?_task=3Dcalendar&_t=3D9febd7562df0f5b=
ca7646a7bf6696801a394dd5a.cmVzb3VyY2UtY29sbGVjdGlvbi1jYXJAZXhhbXBsZS5vcmc%3=
D.726d2f&_action=3Dattend
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
o:resourc
 e-collection-car@example.org
RRULE:FREQ=3DWEEKLY;INTERVAL=3D1;BYDAY=3DFR
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR

--=_c8894dbdb8baeedacae836230e3436fd--
""")

        self.assertTrue(message.is_multipart())

        itip_methods = [ "REQUEST" ]

        # Check each part
        for part in message.walk():

            # The iTip part MUST be Content-Type: text/calendar (RFC 6047,
            # section 2.4)
            if part.get_content_type() == "text/calendar":
                if not part.get_param('method') in itip_methods:
                    raise Exception, "method not interesting"

                # Get the itip_payload
                itip_payload = part.get_payload(decode=True)

                # Python iCalendar prior to 3.0 uses "from_string".
                if hasattr(icalendar.Calendar, 'from_ical'):
                    cal = icalendar.Calendar.from_ical(itip_payload)
                elif hasattr(icalendar.Calendar, 'from_string'):
                    cal = icalendar.Calendar.from_string(itip_payload)
                # If we can't read it, we're out
                else:
                    return []

    def test_002_from_message(self):
        message = message_from_string("""Received: from localhost (localhost [127.0.0.1])
    by kolab.example.org (Postfix) with ESMTP id 513B942E10
    for <resource-collection-car@example.org>; Fri, 13 Jul 2012 14:54:16 +0200 (CEST)
X-Virus-Scanned: amavisd-new at example.org
X-Spam-Flag: NO
X-Spam-Score: 0.551
X-Spam-Level:
X-Spam-Status: No, score=0.551 tagged_above=-10 required=6.2
    tests=[ALL_TRUSTED=-1, DNS_FROM_RFC_DSN=0.001,
    NORMAL_HTTP_TO_IP=0.001, TVD_RCVD_IP=0.054, TVD_RCVD_IP4=1.495]
    autolearn=no
Received: from kolab.example.org ([127.0.0.1])
    by localhost (kolab.example.org [127.0.0.1]) (amavisd-new, port 10024)
    with ESMTP id KNJgv841fj-1 for <resource-collection-car@example.org>;
    Fri, 13 Jul 2012 14:54:15 +0200 (CEST)
Received: from 192.168.122.228 (localhost [127.0.0.1])
    (Authenticated sender: john.doe@example.org)
    by kolab.example.org (Postfix) with ESMTPSA id 0EBDA42E39
    for <resource-collection-car@example.org>; Fri, 13 Jul 2012 14:54:14 +0200 (CEST)
MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Fri, 13 Jul 2012 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
X-Sender: john.doe@example.org
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: resource-collection-car@example.org
Subject: "test" has been updated

--=_c8894dbdb8baeedacae836230e3436fd
Content-Transfer-Encoding: quoted-printable
Content-Type: text/plain; charset=UTF-8;
 format=flowed

*test*

When: 2012-07-13 10:00 - 11:00 (Europe/London)

Invitees: Doe, John <john.doe@example.org>,=20
resource-collection-car@example.org

Please find attached an iCalendar file with the updated event details which=
=20
you can import to your calendar application.

In case your email client doesn't support iTip requests you can use the=20
following link to either accept or decline this invitation:
http://192.168.122.228/roundcubemail/?_task=3Dcalendar&_t=3D9febd7562df0f5b=
ca7646a7bf6696801a394dd5a.cmVzb3VyY2UtY29sbGVjdGlvbi1jYXJAZXhhbXBsZS5vcmc%3=
D.726d2f&_action=3Dattend
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
o:resourc
 e-collection-car@example.org
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR

--=_c8894dbdb8baeedacae836230e3436fd--
""")

        self.assertTrue(message.is_multipart())

        itip_methods = [ "REQUEST" ]

        # Check each part
        for part in message.walk():

            # The iTip part MUST be Content-Type: text/calendar (RFC 6047,
            # section 2.4)
            if part.get_content_type() == "text/calendar":
                if not part.get_param('method') in itip_methods:
                    raise Exception, "method not interesting"

                # Get the itip_payload
                itip_payload = part.get_payload(decode=True)

                # Python iCalendar prior to 3.0 uses "from_string".
                if hasattr(icalendar.Calendar, 'from_ical'):
                    cal = icalendar.Calendar.from_ical(itip_payload)
                elif hasattr(icalendar.Calendar, 'from_string'):
                    cal = icalendar.Calendar.from_string(itip_payload)
                # If we can't read it, we're out
                else:
                    return []
