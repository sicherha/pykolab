import datetime
import icalendar
from icalendar import vDatetime
from icalendar import vText
import kolabformat
import time

import pykolab
from pykolab import constants
from pykolab import utils
from pykolab.translate import _

from attendee import Attendee
from contact_reference import ContactReference

log = pykolab.getLogger('pykolab.xml_event')

def event_from_ical(string):
    return Event(from_ical=string)

def event_from_string(string):
    return Event(from_string=string)

class Event(object):
    status_map = {
            "TENTATIVE": kolabformat.StatusTentative,
            "CONFIRMED": kolabformat.StatusConfirmed,
            "CANCELLED": kolabformat.StatusCancelled,
        }

    def __init__(self, from_ical="", from_string=""):
        self._attendees = []

        if from_ical == "":
            if from_string == "":
                self.event = kolabformat.Event()
            else:
                self.event = kolabformat.readEvent(from_string, False)
        else:
            self.from_ical(from_ical)

    def add_attendee(self, email, name=None, rsvp=False, role=None, participant_status=None):
        log.debug(_("adding attendee with email address %r") % (email), level=9)
        attendee = Attendee(email, name, rsvp, role, participant_status)
        self._attendees.append(attendee)
        self.event.setAttendees(self._attendees)

    def as_string_itip(self, method="REQUEST"):
        cal = icalendar.Calendar()
        cal.add(
                'prodid',
                '-//pykolab-%s-%s//kolab.org//' % (
                        constants.__version__,
                        constants.__release__
                    )
            )

        cal.add('version', '2.0')
        # TODO: Really?
        cal.add('calscale', 'GREGORIAN')
        # TODO: Not always a request...
        cal.add('method', method)

        # TODO: Add timezone information using icalendar.?()
        #       Not sure if there is a class for it.

        event = icalendar.Event()

        # Required
        event['uid'] = self.get_uid()

        # NOTE: Make sure to list(set()) or duplicates may arise
        for attr in list(set(event.singletons)):
            if hasattr(self, 'get_ical_%s' % (attr.lower())):
                exec("retval = self.get_ical_%s()" % (attr.lower()))

                #print "as_string_itip()", attr, retval, type(retval)

                if not retval == None and not retval == "":
                    print attr.lower()
                    event.add(attr.lower(), retval)

            elif hasattr(self, 'get_%s' % (attr.lower())):
                exec("retval = self.get_%s()" % (attr.lower()))

                #print "as_string_itip()", attr, retval

                if not retval == None and not retval == "":
                    event.add(attr.lower(), retval, encode=0)

            #else:
                #print "(single) no function for", attr.lower()

        # NOTE: Make sure to list(set()) or duplicates may arise
        for attr in list(set(event.multiple)):
            if hasattr(self, 'get_ical_%s' % (attr.lower())):
                exec("retval = self.get_ical_%s()" % (attr.lower()))

                print "as_string_itip()", attr, retval

                if isinstance(retval, list) and not len(retval) == 0:
                    for _retval in retval:
                        #print _retval.params
                        event.add(attr.lower(), _retval, encode=0)

            elif hasattr(self, 'get_%s' % (attr.lower())):
                exec("retval = self.get_%s()" % (attr.lower()))
                print attr, retval
                if isinstance(retval, list) and not len(retval) == 0:
                    for _retval in retval:
                        event.add(attr.lower(), _retval, encode=0)

            #else:
                #print "(multiple) no function for", attr.lower()

        #event.add('attendee', self.get_attendees())

        #BEGIN:VEVENT
        #DESCRIPTION:Project XYZ Review Meeting
        #CATEGORIES:MEETING
        #CLASS:PUBLIC
        #CREATED:19980309T130000Z
        #SUMMARY:XYZ Project Review
        #DTSTART;TZID=US-Eastern:19980312T083000
        #DTEND;TZID=US-Eastern:19980312T093000
        #LOCATION:1CP Conference Room 4350
        #END:VEVENT

        #event['description'] =

        cal.add_component(event)

        if hasattr(cal, 'to_ical'):
            return cal.to_ical()
        elif hasattr(cal, 'as_string'):
            return cal.as_string()

    def from_ical(self, ical):
        self.event = kolabformat.Event()
        if hasattr(icalendar.Event, 'from_ical'):
            ical_event = icalendar.Event.from_ical(ical)
        elif hasattr(icalendar.Event, 'from_string'):
            ical_event = icalendar.Event.from_string(ical)

        # TODO: Clause the timestamps for zulu suffix causing datetime.datetime
        # to fail substitution.
        for attr in list(set(ical_event.required)):
            if ical_event.has_key(attr):
                self.set_from_ical(attr.lower(), ical_event[attr])

        # NOTE: Make sure to list(set()) or duplicates may arise
        for attr in list(set(ical_event.singletons)):
            if ical_event.has_key(attr):
                self.set_from_ical(attr.lower(), ical_event[attr])

        # NOTE: Make sure to list(set()) or duplicates may arise
        for attr in list(set(ical_event.multiple)):
            if ical_event.has_key(attr):
                #if attr == "ATTENDEE":
                    #print ical_event.decoded(attr)

                self.set_from_ical(attr.lower(), ical_event[attr])

    def get_attendee_participant_status(self, attendee):
        return attendee.get_participant_status()

    def get_attendees(self):
        return self._attendees

    def get_created(self):
        _datetime = self.event.created()

        (
                year,
                month,
                day,
                hour,
                minute,
                second
            ) = (
                    _datetime.year(),
                    _datetime.month(),
                    _datetime.day(),
                    _datetime.hour(),
                    _datetime.minute(),
                    _datetime.second()
                )

        try:
            result = datetime.datetime(year, month, day, hour, minute, second)
        except ValueError:
            result = datetime.datetime.now()

    def get_end(self):
        _datetime = self.event.end()

        (
                year,
                month,
                day,
                hour,
                minute,
                second
            ) = (
                    _datetime.year(),
                    _datetime.month(),
                    _datetime.day(),
                    _datetime.hour(),
                    _datetime.minute(),
                    _datetime.second()
                )

        return datetime.datetime(year, month, day, hour, minute, second)

    def get_ical_attendee(self):
        # TODO: Formatting, aye? See also the example snippet:
        #
        # ATTENDEE;RSVP=TRUE;ROLE=REQ-PARTICIPANT;CUTYPE=GROUP:
        # MAILTO:employee-A@host.com

        attendees = []
        for attendee in self.get_attendees():
            contact = attendee.contact()
            rsvp = attendee.rsvp()
            role = attendee.role()
            partstat = attendee.partStat()

            if rsvp:
                _rsvp = "TRUE"
            else:
                _rsvp = "FALSE"

            #Required = _kolabformat.Required
            #Chair = _kolabformat.Chair
            #Optional = _kolabformat.Optional
            #NonParticipant = _kolabformat.NonParticipant

            # TODO: Check the role strings for validity
            # TODO^2: Use map
            if role == kolabformat.Required:
                _role = "REQ-PARTICIPANT"
            elif role == kolabformat.Chair:
                _role = "CHAIR"
            elif role == kolabformat.Optional:
                _role = "OPTIONAL"
            elif role == kolabformat.NonParticipant:
                _role = "NON-PARTICIPANT"
            else:
                _role = "OPTIONAL"

            if partstat == kolabformat.PartNeedsAction:
                _partstat = "NEEDS-ACTION"
            elif partstat == kolabformat.PartAccepted:
                _partstat = "ACCEPTED"
            elif partstat == kolabformat.PartDeclined:
                _partstat = "DECLINED"
            elif partstat == kolabformat.PartTentative:
                _partstat = "TENTATIVE"
            elif partstat == kolabformat.PartDelegated:
                _partstat = "DELEGATED"

            _attendee = icalendar.vCalAddress("MAILTO:%s" % contact.email())
            _attendee.params['RSVP'] = icalendar.vText(_rsvp)
            _attendee.params['PARTSTAT'] = icalendar.vText(_partstat)
            _attendee.params['ROLE'] = icalendar.vText(_role)

            attendees.append(_attendee)

        #print "get_ical_attendees()", attendees

        return attendees

    def get_ical_created(self):
        return self.get_created()

    def get_ical_dtend(self):
        return self.get_end()

    def get_ical_dtstamp(self):
        return
        try:
            retval = self.event.lastModified()
            if retval == None or retval == "":
                return datetime.datetime.now()
        except:
            return datetime.datetime.now()

    def get_ical_dtstart(self):
        return self.get_start()

    def get_ical_organizer(self):
        contact = self.get_organizer()
        organizer = icalendar.vCalAddress("MAILTO:%s" % contact.email())
        name = contact.name()

        if not name == None and not name == "":
            organizer.params["CN"] = icalendar.vText(name)

        return organizer

    def get_ical_status(self):
        status = self.event.status()

        #print "get_ical_status()", status
        #print self.status_map.keys()
        #print self.status_map.values()
        if status in self.status_map.keys():
            return status

        if status in self.status_map.values():
            return [k for k, v in self.status_map.iteritems() if v == status][0]

        #print "get_ical_status()", status

    def get_organizer(self):
        organizer = self.event.organizer()
        #print organizer
        return organizer

    def get_priority(self):
        return self.event.priority()

    def get_start(self):
        #print "get_start()"
        _datetime = self.event.start()

        (
                year,
                month,
                day,
                hour,
                minute,
                second
            ) = (
                    _datetime.year(),
                    _datetime.month(),
                    _datetime.day(),
                    _datetime.hour(),
                    _datetime.minute(),
                    _datetime.second()
                )

        return datetime.datetime(year, month, day, hour, minute, second)

    def get_status(self):
        status = self.event.status()
        for key in self.status_map.keys():
            if self.status_map[key] == status:
                return key

    def get_summary(self):
        return self.event.summary()

    def get_uid(self):
        uid = self.event.uid()
        if not uid == '':
            return uid
        else:
            self.__str__()
            return kolabformat.getSerializedUID()

    def set_attendee_participant_status(self, attendee, status):
        attendee.set_participant_status(status)
        self.event.setAttendees(self._attendees)

    def set_created(self, _datetime=None):
        if _datetime == None:
            _datetime = datetime.datetime.now()

        (
                year,
                month,
                day,
                hour,
                minute,
                second
            ) = (
                    _datetime.year,
                    _datetime.month,
                    _datetime.day,
                    _datetime.hour,
                    _datetime.minute,
                    _datetime.second
                )

        self.event.setCreated(
                kolabformat.cDateTime(year, month, day, hour, minute, second)
            )

    def set_dtstamp(self, _datetime):
        (
                year,
                month,
                day,
                hour,
                minute,
                second
            ) = (
                    _datetime.year,
                    _datetime.month,
                    _datetime.day,
                    _datetime.hour,
                    _datetime.minute,
                    _datetime.second
                )

        self.event.setLastModified(
                kolabformat.cDateTime(year, month, day, hour, minute, second)
            )

    def set_end(self, _datetime):
        (
                year,
                month,
                day,
            ) = (
                    _datetime.year,
                    _datetime.month,
                    _datetime.day,
                )
        if hasattr(_datetime, 'hour'):
            (
                    hour,
                    minute,
                    second
                ) = (
                        _datetime.hour,
                        _datetime.minute,
                        _datetime.second
                    )
        else:
            (hour, minute, second) = (0,0,0)

        self.event.setEnd(
                kolabformat.cDateTime(year, month, day, hour, minute, second)
            )

    def set_from_ical(self, attr, value):
        if attr == "dtend":
            self.set_ical_dtend(value.dt)
        elif attr == "dtstart":
            self.set_ical_dtstart(value.dt)
        elif attr == "status":
            self.set_ical_status(value)
        elif attr == "summary":
            self.set_ical_summary(value)
        elif attr == "priority":
            self.set_ical_priority(value)
        elif attr == "attendee":
            self.set_ical_attendee(value)
        elif attr == "organizer":
            self.set_ical_organizer(value)
        elif attr == "uid":
            self.set_ical_uid(value)

        else:
            print "WARNING, no function for", attr

    def set_ical_attendee(self, _attendee):
        log.debug(_("set attendees from ical: %r") % (_attendee), level=9)

        if isinstance(_attendee, basestring):
            _attendee = [_attendee]

        if isinstance(_attendee, list):
            for attendee in _attendee:
                address = str(attendee).split(':')[-1]

                if hasattr(attendee, 'params'):
                    params = attendee.params
                else:
                    params = {}

                if params.has_key('CN'):
                    name = params['CN']
                else:
                    name = None

                if params.has_key('ROLE'):
                    role = params['ROLE']
                else:
                    role = None

                if params.has_key('PARTSTAT'):
                    partstat = params['PARTSTAT']
                else:
                    partstat = None

                if params.has_key('RSVP'):
                    rsvp = params['RSVP']
                else:
                    rsvp = None

                self.add_attendee(address, name=name, rsvp=rsvp, role=role, participant_status=partstat)

    def set_ical_dtend(self, dtend):
        self.set_end(dtend)

    def set_ical_dtstamp(self, dtstamp):
        self.set_dtstamp(dtstamp)

    def set_ical_dtstart(self, dtstart):
        self.set_start(dtstart)

    def set_ical_organizer(self, organizer):
        address = str(organizer).split(':')[-1]

        cn = None

        if hasattr(organizer, 'params'):
            params = organizer.params
        else:
            params = {}

        if params.has_key('CN'):
            cn = params['CN']

        self.set_organizer(str(address), name=cn)

    def set_ical_priority(self, priority):
        self.set_priority(priority)

    def set_ical_status(self, status):
        #print "set_ical_status()", status

        # TODO: See which ones are actually valid for iTip
        if status == "UNDEFINED":
            _status = kolabformat.StatusUndefined
        elif status == "NEEDS-ACTION":
            _status = kolabformat.StatusNeedsAction
        elif status == "COMPLETED":
            _status = kolabformat.StatusCompleted
        elif status == "INPROCESS":
            _status = kolabformat.StatusInProcess
        elif status == "CANCELLED":
            _status = kolabformat.StatusCancelled
        elif status == "TENTATIVE":
            _status = kolabformat.StatusTentative
        elif status == "CONFIRMED":
            _status = kolabformat.StatusConfirmed
        elif status == "DRAFT":
            _status = kolabformat.StatusDraft
        elif status == "FINAL":
            _status = kolabformat.StatusFinal
        else:
            _status = kolabformat.StatusUndefined

        self.event.setStatus(_status)

    def set_ical_summary(self, summary):
        self.set_summary(str(summary))

    def set_ical_uid(self, uid):
        self.set_uid(str(uid))

    def set_organizer(self, email, name=None):
        contactreference = ContactReference(email)
        if not name == None:
            contactreference.set_name(name)

        self.event.setOrganizer(contactreference)

    def set_priority(self, priority):
        self.event.setPriority(priority)

    def set_start(self, _datetime):
        (
                year,
                month,
                day,
            ) = (
                    _datetime.year,
                    _datetime.month,
                    _datetime.day,
                )
        if hasattr(_datetime, 'hour'):
            (
                    hour,
                    minute,
                    second
                ) = (
                        _datetime.hour,
                        _datetime.minute,
                        _datetime.second
                    )
        else:
            (hour, minute, second) = (0,0,0)

        self.event.setStart(kolabformat.cDateTime(year, month, day, hour, minute, second))

    def set_status(self, status):
        if status in self.status_map.keys():
            self.event.setStatus(self.status_map[status])
        elif status in self.status_map.values():
            self.event.setStatus(status)
        else:
            raise InvalidEventStatusError, _("Invalid status set: %r") % (status)

    def set_summary(self, summary):
        self.event.setSummary(summary)

    def set_uid(self, uid):
        self.event.setUid(str(uid))

    def __str__(self):
        return kolabformat.writeEvent(self.event)

    def to_message(self):
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase
        from email.MIMEText import MIMEText
        from email.Utils import COMMASPACE, formatdate
        from email import Encoders

        msg = MIMEMultipart()
        organizer = self.get_organizer()
        email = organizer.email()
        name = organizer.name()

        if not name:
            msg['From'] = email
        else:
            msg['From'] = '"%s" <%s>' % (name, email)

        msg['To'] = ', '.join([x.__str__() for x in self.get_attendees()])
        msg['Date'] = formatdate(localtime=True)

        msg.add_header('X-Kolab-Type', 'application/x-vnd.kolab.event')

        text = utils.multiline_message("""
                    This is a Kolab Groupware object. To view this object you
                    will need an email client that understands the Kolab
                    Groupware format. For a list of such email clients please
                    visit http://www.kolab.org/
            """)

        msg.attach( MIMEText(text) )

        part = MIMEBase('application', "calendar+xml")
        part.set_charset('UTF-8')

        msg["Subject"] = self.get_uid()

        part.set_payload(str(self))

        part.add_header('Content-Disposition', 'attachment; filename="kolab.xml"')
        part.replace_header('Content-Transfer-Encoding', '8bit')

        msg.attach(part)

        return msg

    def to_message_itip(self, from_address, method="REQUEST", participant_status="ACCEPTED"):
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase
        from email.MIMEText import MIMEText
        from email.Utils import COMMASPACE, formatdate
        from email import Encoders

        msg = MIMEMultipart()

        msg_from = None

        log.debug(_("MESSAGE ITIP method %r") % (method), level=9)

        if method == "REPLY":
            msg['To'] = self.get_organizer().email()

            log.debug(_("IN ITIP MESSAGE REPLY: %r") % (msg['To']), level=9)

            attendees = self.get_attendees()

            for attendee in attendees:
                if attendee.get_email() == from_address:
                    # Only the attendee is supposed to be listed in a reply
                    attendee.set_participant_status(participant_status)

                    self._attendees = [attendee]
                    self.event.setAttendees(self._attendees)

                    name = attendee.get_name()
                    email = attendee.get_email()

                    if not name:
                        msg_from = email
                    else:
                        msg_from = '"%s" <%s>' % (name, email)

            if msg_from == None:
                organizer = self.get_organizer()
                email = organizer.get_email()
                name = organizer.get_name()
                if email == from_address:
                    if not name:
                        msg_from = email
                    else:
                        msg_from = '"%s" <%s>' % (name, email)

        elif method == "REQUEST":
            organizer = self.get_organizer()
            email = organizer.get_email()
            name = organizer.get_name()
            if not name:
                msg_from = email
            else:
                msg_from = '"%s" <%s>' % (name, email)


        log.debug(_("Message sender: %r") % (msg_from), level=9)

        if msg_from == None:
            log.error(_("No sender specified"))

        msg['From'] = msg_from

        msg['Date'] = formatdate(localtime=True)

        text = utils.multiline_message("""
                    This is a response to one of your event requests.
            """)

        msg.attach( MIMEText(text) )

        part = MIMEBase('text', "calendar")
        part.set_charset('UTF-8')

        msg["Subject"] = "Response to invitation"

        part.set_payload(self.as_string_itip(method=method))

        part.add_header('Content-Disposition', 'attachment; filename="event.ics"')
        part.replace_header('Content-Transfer-Encoding', '8bit')

        msg.attach(part)

        print msg.as_string()

        return msg

class EventIntegrityError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class InvalidEventStatusError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
