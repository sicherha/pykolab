import datetime
import icalendar
from icalendar import vDatetime
from icalendar import vText
import kolabformat
import pytz
import time
import uuid
import base64

import pykolab
from pykolab import constants
from pykolab import utils
from pykolab.xml import utils as xmlutils
from pykolab.translate import _

from os import path
from attendee import Attendee
from contact_reference import ContactReference

log = pykolab.getLogger('pykolab.xml_event')

def event_from_ical(string):
    return Event(from_ical=string)

def event_from_string(string):
    return Event(from_string=string)

def event_from_message(message):
    event = None
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "application/calendar+xml":
                payload = part.get_payload(decode=True)
                event = event_from_string(payload)

            # append attachment parts to Event object
            elif event and part.has_key('Content-ID'):
                event._attachment_parts.append(part)

    return event


class Event(object):
    status_map = {
            "TENTATIVE": kolabformat.StatusTentative,
            "CONFIRMED": kolabformat.StatusConfirmed,
            "CANCELLED": kolabformat.StatusCancelled,
        }

    classification_map = {
            "PUBLIC": kolabformat.ClassPublic,
            "PRIVATE": kolabformat.ClassPrivate,
            "CONFIDENTIAL": kolabformat.ClassConfidential,
        }

    def __init__(self, from_ical="", from_string=""):
        self._attendees = []
        self._categories = []
        self._attachment_parts = []

        if from_ical == "":
            if from_string == "":
                self.event = kolabformat.Event()
            else:
                self.event = kolabformat.readEvent(from_string, False)
                self._load_attendees()
        else:
            self.from_ical(from_ical)

        self.uid = self.get_uid()

    def _load_attendees(self):
        for a in self.event.attendees():
            self._attendees.append(Attendee(a.contact().email(), a.contact().name(), a.rsvp(), a.role(), a.partStat(), a.cutype()))

    def add_attendee(self, email, name=None, rsvp=False, role=None, participant_status=None, cutype="INDIVIDUAL", params=None):
        attendee = Attendee(email, name, rsvp, role, participant_status, cutype, params)
        self._attendees.append(attendee)
        self.event.setAttendees(self._attendees)

    def add_category(self, category):
        self._categories.append(str(category))
        self.event.setCategories(self._categories)

    def add_exception_date(self, _datetime):
        valid_datetime = False
        if isinstance(_datetime, datetime.date):
            valid_datetime = True

        if isinstance(_datetime, datetime.datetime):
            # If no timezone information is passed on, make it UTC
            if _datetime.tzinfo == None:
                _datetime = _datetime.replace(tzinfo=pytz.utc)

            valid_datetime = True

        if not valid_datetime:
            raise InvalidEventDateError, _("Event start needs datetime.date or datetime.datetime instance")

        self.event.addExceptionDate(xmlutils.to_cdatetime(_datetime, True))

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
            ical_getter = 'get_ical_%s' % (attr.lower())
            default_getter = 'get_%s' % (attr.lower())
            retval = None
            if hasattr(self, ical_getter):
                retval = getattr(self, ical_getter)()
                if not retval == None and not retval == "":
                    event.add(attr.lower(), retval)
            elif hasattr(self, default_getter):
                retval = getattr(self, default_getter)()
                if not retval == None and not retval == "":
                    event.add(attr.lower(), retval, encode=0)

        # NOTE: Make sure to list(set()) or duplicates may arise
        for attr in list(set(event.multiple)):
            ical_getter = 'get_ical_%s' % (attr.lower())
            default_getter = 'get_%s' % (attr.lower())
            retval = None
            if hasattr(self, ical_getter):
                retval = getattr(self, ical_getter)()
            elif hasattr(self, default_getter):
                retval = getattr(self, default_getter)()

            if isinstance(retval, list) and not len(retval) == 0:
                for _retval in retval:
                    event.add(attr.lower(), _retval, encode=0)

        cal.add_component(event)

        if hasattr(cal, 'to_ical'):
            return cal.to_ical()
        elif hasattr(cal, 'as_string'):
            return cal.as_string()

    def delegate(self, delegators, delegatees, names=None):
        if not isinstance(delegators, list):
            delegators = [delegators]

        if not isinstance(delegatees, list):
            delegatees = [delegatees]

        if not isinstance(names, list):
            names = [names]

        _delegators = []
        for delegator in delegators:
            _delegators.append(self.get_attendee(delegator))

        _delegatees = []

        for i,delegatee in enumerate(delegatees):
            try:
                _delegatees.append(self.get_attendee(delegatee))
            except:
                # TODO: An iTip needs to be sent out to the new attendee
                self.add_attendee(delegatee, names[i] if i < len(names) else None)
                _delegatees.append(self.get_attendee(delegatee))

        for delegator in _delegators:
            delegator.delegate_to(_delegatees)

        for delegatee in _delegatees:
            delegatee.delegate_from(_delegators)

        self.event.setAttendees(self._attendees)

    def from_ical(self, ical):
        if hasattr(icalendar.Event, 'from_ical'):
            ical_event = icalendar.Event.from_ical(ical)
        elif hasattr(icalendar.Event, 'from_string'):
            ical_event = icalendar.Event.from_string(ical)

        # use the libkolab calendaring bindings to load the full iCal data
        if ical_event.has_key('RRULE') or ical_event.has_key('ATTACH') \
             or [part for part in ical_event.walk() if part.name == 'VALARM']:
            self._xml_from_ical(ical)
        else:
            self.event = kolabformat.Event()

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
                self.set_from_ical(attr.lower(), ical_event[attr])

    def _xml_from_ical(self, ical):
        from kolab.calendaring import EventCal
        self.event = EventCal()
        self.event.fromICal("BEGIN:VCALENDAR\nVERSION:2.0\n" + ical + "\nEND:VCALENDAR")

    def get_attendee_participant_status(self, attendee):
        return attendee.get_participant_status()

    def get_attendee(self, attendee):
        if isinstance(attendee, basestring):
            if attendee in [x.get_email() for x in self.get_attendees()]:
                attendee = self.get_attendee_by_email(attendee)

            elif attendee in [x.get_name() for x in self.get_attendees()]:
                attendee = self.get_attendee_by_name(attendee)

            else:
                raise ValueError, _("No attendee with email or name %r") %(attendee)

            return attendee

        elif isinstance(attendee, Attendee):
            return attendee

        else:
            raise ValueError, _("Invalid argument value attendee %r, must be basestring or Attendee") % (attendee)

    def get_attendee_by_email(self, email):
        if email in [x.get_email() for x in self.get_attendees()]:
            return [x for x in self.get_attendees() if x.get_email() == email][0]

        raise ValueError, _("No attendee with email %r") %(email)

    def get_attendee_by_name(self, name):
        if name in [x.get_name() for x in self.get_attendees()]:
            return [x for x in self.get_attendees() if x.get_name() == name][0]

        raise ValueError, _("No attendee with name %r") %(name)

    def get_attendees(self):
        return self._attendees

    def get_categories(self):
        return [str(c) for c in self.event.categories()]

    def get_classification(self):
        return self.event.classification()

    def get_created(self):
        try:
            return xmlutils.from_cdatetime(self.event.created(), False)
        except ValueError:
            return datetime.datetime.now()

    def get_description(self):
        return self.event.description()

    def get_duration(self):
        duration = self.event.duration()
        if duration and duration.isValid():
            dtd = datetime.timedelta(
                days=duration.days(),
                seconds=duration.seconds(),
                minutes=duration.minutes(),
                hours=duration.hours(),
                weeks=duration.weeks()
            )
            return dtd

        return None

    def get_end(self):
        dt = xmlutils.from_cdatetime(self.event.end(), True)
        if not dt:
            duration = self.get_duration()
            if duration is not None:
                dt = self.get_start() + duration
        return dt

    def get_date_text(self, date_format='%Y-%m-%d', time_format='%H:%M %Z'):
        start = self.get_start()
        end = self.get_end()
        if start.date() == end.date():
            end_format = time_format
        else:
            end_format = date_format + " " + time_format

        return "%s - %s" % (start.strftime(date_format + " " + time_format), end.strftime(end_format))

    def get_exception_dates(self):
        return map(lambda _: xmlutils.from_cdatetime(_, True), self.event.exceptionDates())

    def get_attachments(self):
        return self.event.attachments()

    def get_attachment_data(self, i):
        vattach = self.event.attachments()
        if i < len(vattach):
            attachment = vattach[i]
            uri = attachment.uri()
            if uri and uri[0:4] == 'cid:':
                # get data from MIME part with matching content-id
                cid = '<' + uri[4:] + '>'
                for p in self._attachment_parts:
                    if p['Content-ID'] == cid:
                        return p.get_payload(decode=True)
            else:
                return attachment.data()

        return None

    def get_alarms(self):
        return self.event.alarms()

    def get_ical_attendee(self):
        # TODO: Formatting, aye? See also the example snippet:
        #
        # ATTENDEE;RSVP=TRUE;ROLE=REQ-PARTICIPANT;CUTYPE=GROUP:
        # MAILTO:employee-A@host.com

        attendees = []
        for attendee in self.get_attendees():
            email = attendee.get_email()
            name = attendee.get_name()
            rsvp = attendee.get_rsvp()
            role = attendee.get_role()
            partstat = attendee.get_participant_status()
            cutype = attendee.get_cutype()
            delegators = attendee.get_delegated_from()
            delegatees = attendee.get_delegated_to()

            if rsvp in attendee.rsvp_map.keys():
                _rsvp = rsvp
            elif rsvp in attendee.rsvp_map.values():
                _rsvp = [k for k, v in attendee.rsvp_map.iteritems() if v == rsvp][0]
            else:
                _rsvp = None

            if role in attendee.role_map.keys():
                _role = role
            elif role in attendee.role_map.values():
                _role = [k for k, v in attendee.role_map.iteritems() if v == role][0]
            else:
                _role = None

            if partstat in attendee.participant_status_map.keys():
                _partstat = partstat
            elif partstat in attendee.participant_status_map.values():
                _partstat = [k for k, v in attendee.participant_status_map.iteritems() if v == partstat][0]
            else:
                _partstat = None

            if cutype in attendee.cutype_map.keys():
                _cutype = cutype
            elif cutype in attendee.cutype_map.values():
                _cutype = [k for k, v in attendee.cutype_map.iteritems() if v == cutype][0]
            else:
                _cutype = None

            _attendee = icalendar.vCalAddress("MAILTO:%s" % email)
            if not name == None and not name == "":
                _attendee.params['CN'] = icalendar.vText(name)

            if not _rsvp == None:
                _attendee.params['RSVP'] = icalendar.vText(_rsvp)

            if not _role == None:
                _attendee.params['ROLE'] = icalendar.vText(_role)

            if not _partstat == None:
                _attendee.params['PARTSTAT'] = icalendar.vText(_partstat)

            if not _cutype == None:
                _attendee.params['CUTYPE'] = icalendar.vText(_cutype)

            if not delegators == None and len(delegators) > 0:
                _attendee.params['DELEGATED-FROM'] = icalendar.vText(delegators[0].email())

            if not delegatees == None and len(delegatees) > 0:
                _attendee.params['DELEGATED-TO'] = icalendar.vText(delegatees[0].email())

            attendees.append(_attendee)

        return attendees

    def get_ical_attendee_participant_status(self, attendee):
        attendee = self.get_attendee(attendee)

        if attendee.get_participant_status() in attendee.participant_status_map.keys():
            return attendee.get_participant_status()
        elif attendee.get_participant_status() in attendee.participant_status_map.values():
            return [k for k, v in attendee.participant_status_map.iteritems() if v == attendee.get_participant_status()][0]
        else:
            raise ValueError, _("Invalid participant status")

    def get_ical_created(self):
        return self.get_created()

    def get_ical_dtend(self):
        return self.get_end()

    def get_ical_dtstamp(self):
        try:
            retval = self.get_lastmodified()
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

        if status in self.status_map.keys():
            return status

        if status in self.status_map.values():
            return [k for k, v in self.status_map.iteritems() if v == status][0]

    def get_ical_sequence(self):
        return str(self.event.sequence()) if self.event.sequence() else None

    def get_location(self):
        return self.event.location()

    def get_lastmodified(self):
        try:
            _datetime = self.event.lastModified()
            if retval == None or retval == "":
                self.__str__()
        except:
            self.__str__()

        return xmlutils.from_cdatetime(self.event.lastModified(), False)

    def get_organizer(self):
        organizer = self.event.organizer()
        return organizer

    def get_priority(self):
        return str(self.event.priority())

    def get_start(self):
        return xmlutils.from_cdatetime(self.event.start(), True)

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
            self.set_uid(uuid.uuid4())
            return self.get_uid()

    def get_sequence(self):
        return self.event.sequence()

    def get_url(self):
        return self.event.url()

    def get_transparency(self):
        return self.event.transparency()

    def set_attendee_participant_status(self, attendee, status, rsvp=None):
        """
            Set the participant status of an attendee to status.

            As the attendee arg, pass an email address or name, for this
            function to obtain the attendee object by searching the list of
            attendees for this event.
        """
        attendee = self.get_attendee(attendee)
        attendee.set_participant_status(status)

        if rsvp is not None:
            attendee.set_rsvp(rsvp)

        self.event.setAttendees(self._attendees)

    def set_status(self, status):
        if status in self.status_map.keys():
            self.event.setStatus(self.status_map[status])
        elif status in self.status_map.values():
            self.event.setStatus(status)
        else:
            raise ValueError, _("Invalid status %r") % (status)

    def set_classification(self, classification):
        if classification in self.classification_map.keys():
            self.event.setClassification(self.classification_map[classification])
        elif classification in self.classification_map.values():
            self.event.setClassification(status)
        else:
            raise ValueError, _("Invalid classification %r") % (classification)

    def set_created(self, _datetime=None):
        if _datetime == None:
            _datetime = datetime.datetime.now()

        self.event.setCreated(xmlutils.to_cdatetime(_datetime, False))

    def set_description(self, description):
        self.event.setDescription(str(description))

    def set_dtstamp(self, _datetime):
        self.event.setLastModified(xmlutils.to_cdatetime(_datetime, False))

    def set_end(self, _datetime):
        valid_datetime = False
        if isinstance(_datetime, datetime.date):
            valid_datetime = True

        if isinstance(_datetime, datetime.datetime):
            # If no timezone information is passed on, make it UTC
            if _datetime.tzinfo == None:
                _datetime = _datetime.replace(tzinfo=pytz.utc)

            valid_datetime = True

        if not valid_datetime:
            raise InvalidEventDateError, _("Event end needs datetime.date or datetime.datetime instance")

        self.event.setEnd(xmlutils.to_cdatetime(_datetime, True))

    def set_exception_dates(self, _datetimes):
        for _datetime in _datetimes:
            self.add_exception_date(_datetime)

    def set_from_ical(self, attr, value):
        ical_setter = 'set_ical_' + attr
        default_setter = 'set_' + attr

        if attr == "dtend":
            self.set_ical_dtend(value.dt)
        elif attr == "dtstart":
            self.set_ical_dtstart(value.dt)
        elif attr == "dtstamp":
            self.set_ical_dtstamp(value.dt)
        elif attr == "created":
            self.set_created(value.dt)
        elif attr == "lastmodified":
            self.set_lastmodified(value.dt)
        elif attr == "categories":
            self.add_category(value)
        elif attr == "class":
            self.set_classification(value)
        elif hasattr(self, ical_setter):
            getattr(self, ical_setter)(value)
        elif hasattr(self, default_setter):
            getattr(self, default_setter)(value)

    def set_ical_attendee(self, _attendee):
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
                    name = str(params['CN'])
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

                if params.has_key('CUTYPE'):
                    cutype = params['CUTYPE']
                else:
                    cutype = kolabformat.CutypeIndividual

                att = self.add_attendee(address, name=name, rsvp=rsvp, role=role, participant_status=partstat, cutype=cutype, params=params)

    def set_ical_dtend(self, dtend):
        self.set_end(dtend)

    def set_ical_dtstamp(self, dtstamp):
        self.set_dtstamp(dtstamp)

    def set_ical_dtstart(self, dtstart):
        self.set_start(dtstart)

    def set_ical_lastmodified(self, lastmod):
        self.set_lastmodified(lastmod)

    def set_ical_duration(self, value):
        if value.dt:
            duration = kolabformat.Duration(value.dt.days, 0, 0, value.dt.seconds, False)
            self.event.setDuration(duration)

    def set_ical_organizer(self, organizer):
        address = str(organizer).split(':')[-1]

        cn = None

        if hasattr(organizer, 'params'):
            params = organizer.params
        else:
            params = {}

        if params.has_key('CN'):
            cn = str(params['CN'])

        self.set_organizer(str(address), name=cn)

    def set_ical_priority(self, priority):
        self.set_priority(priority)

    def set_ical_sequence(self, sequence):
        self.set_sequence(sequence)

    def set_ical_summary(self, summary):
        self.set_summary(str(summary))

    def set_ical_uid(self, uid):
        self.set_uid(str(uid))

    def set_lastmodified(self, _datetime=None):
        valid_datetime = False
        if isinstance(_datetime, datetime.date):
            valid_datetime = True

        if isinstance(_datetime, datetime.datetime):
            valid_datetime = True

        if _datetime == None:
            valid_datetime = True
            _datetime = datetime.datetime.now()

        if not valid_datetime:
            raise InvalidEventDateError, _("Event start needs datetime.date or datetime.datetime instance")

        self.event.setLastModified(xmlutils.to_cdatetime(_datetime, False))

    def set_location(self, location):
        self.event.setLocation(str(location))

    def set_organizer(self, email, name=None):
        contactreference = ContactReference(email)
        if not name == None:
            contactreference.setName(name)

        self.event.setOrganizer(contactreference)

    def set_priority(self, priority):
        self.event.setPriority(priority)

    def set_sequence(self, sequence):
        self.event.setSequence(int(sequence))

    def set_url(self, url):
        self.event.setUrl(str(url))

    def set_recurrence(self, recurrence):
        self.event.setRecurrenceRule(recurrence)

        # reset eventcal instance
        if hasattr(self, 'eventcal'):
            del self.eventcal

    def set_start(self, _datetime):
        valid_datetime = False
        if isinstance(_datetime, datetime.date):
            valid_datetime = True

        if isinstance(_datetime, datetime.datetime):
            # If no timezone information is passed on, make it UTC
            if _datetime.tzinfo == None:
                _datetime = _datetime.replace(tzinfo=pytz.utc)

            valid_datetime = True

        if not valid_datetime:
            raise InvalidEventDateError, _("Event start needs datetime.date or datetime.datetime instance")

        self.event.setStart(xmlutils.to_cdatetime(_datetime, True))

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
        self.uid = uid
        self.event.setUid(str(uid))

    def set_transparency(self, transp):
        return self.event.setTransparency(transp)

    def __str__(self):
        event_xml = kolabformat.writeEvent(self.event)

        error = kolabformat.error()

        if error == None or not error:
            return event_xml
        else:
            raise EventIntegrityError, kolabformat.errorMessage()

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

        msg.add_header('X-Kolab-MIME-Version', '3.0')
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

        # extract attachment data into separate MIME parts
        vattach = self.event.attachments()
        i = 0
        for attach in vattach:
            if attach.uri():
                continue

            mimetype = attach.mimetype()
            (primary, seconday) = mimetype.split('/')
            name = attach.label()
            if not name:
                name = 'unknown.x'

            (basename, suffix) = path.splitext(name)
            t = datetime.datetime.now()
            cid = "%s.%s.%s%s" % (basename, time.mktime(t.timetuple()), t.microsecond + len(self._attachment_parts), suffix)

            p = MIMEBase(primary, seconday)
            p.add_header('Content-Disposition', 'attachment', filename=name)
            p.add_header('Content-Transfer-Encoding', 'base64')
            p.add_header('Content-ID', '<' + cid + '>')
            p.set_payload(base64.b64encode(attach.data()))

            self._attachment_parts.append(p)

            # modify attachment object
            attach.setData('', mimetype)
            attach.setUri('cid:' + cid, mimetype)
            vattach[i] = attach
            i += 1

        self.event.setAttachments(vattach)

        part.set_payload(str(self))

        part.add_header('Content-Disposition', 'attachment; filename="kolab.xml"')
        part.replace_header('Content-Transfer-Encoding', '8bit')

        msg.attach(part)

        # append attachment parts
        for p in self._attachment_parts:
            msg.attach(p)

        return msg

    def to_message_itip(self, from_address, method="REQUEST", participant_status="ACCEPTED", subject=None, message_text=None):
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase
        from email.MIMEText import MIMEText
        from email.Utils import COMMASPACE, formatdate
        from email import Encoders

        msg = MIMEMultipart()

        msg_from = None
        attendees = None

        if method == "REPLY":
            # TODO: Make user friendly name <email>
            msg['To'] = self.get_organizer().email()

            attendees = self.get_attendees()

            # TODO: There's an exception here for delegation (partstat DELEGATED)
            for attendee in attendees:
                if attendee.get_email() == from_address:
                    # Only the attendee is supposed to be listed in a reply
                    attendee.set_participant_status(participant_status)
                    attendee.set_rsvp(False)

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
                email = organizer.email()
                name = organizer.name()
                if email == from_address:
                    if not name:
                        msg_from = email
                    else:
                        msg_from = '"%s" <%s>' % (name, email)

        elif method == "REQUEST":
            organizer = self.get_organizer()
            email = organizer.email()
            name = organizer.name()
            if not name:
                msg_from = email
            else:
                msg_from = '"%s" <%s>' % (name, email)

        if msg_from == None:
            if from_address == None:
                log.error(_("No sender specified"))
            else:
                msg_from = from_address

        msg['From'] = msg_from

        msg['Date'] = formatdate(localtime=True)

        if subject is None:
            subject = _("Invitation for %s was %s") % (self.get_summary(), _(participant_status))

        msg["Subject"] = subject

        if message_text is None:
            message_text = _("""This is an automated response to one of your event requests.""")

        msg.attach(MIMEText(utils.stripped_message(message_text)))

        part = MIMEBase('text', 'calendar', charset='UTF-8', method=method)
        del part['MIME-Version']  # mime parts don't need this

        part.set_payload(self.as_string_itip(method=method))

        part.add_header('Content-Disposition', 'attachment; filename="event.ics"')
        part.add_header('Content-Transfer-Encoding', '8bit')

        msg.attach(part)

        # restore the original list of attendees
        # attendees being reduced to the replying attendee above
        if attendees is not None:
            self._attendees = attendees
            self.event.setAttendees(self._attendees)

        return msg

    def is_recurring(self):
        return self.event.recurrenceRule().isValid()

    def to_event_cal(self):
        from kolab.calendaring import EventCal
        return EventCal(self.event)

    def get_next_occurence(self, datetime):
        if not hasattr(self, 'eventcal'):
            self.eventcal = self.to_event_cal()

        next_cdatetime = self.eventcal.getNextOccurence(xmlutils.to_cdatetime(datetime, True))
        next_datetime  = xmlutils.from_cdatetime(next_cdatetime, True) if next_cdatetime is not None else None

        # cut infinite recurrence at a reasonable point
        if next_datetime and not self.get_last_occurrence() and next_datetime > self._recurrence_end():
            next_datetime = None

        return next_datetime

    def get_occurence_end_date(self, datetime):
        if not datetime:
            return None

        if not hasattr(self, 'eventcal'):
            return None

        end_cdatetime = self.eventcal.getOccurenceEndDate(xmlutils.to_cdatetime(datetime, True))
        return xmlutils.from_cdatetime(end_cdatetime, True) if end_cdatetime is not None else None

    def get_last_occurrence(self, force=False):
        if not hasattr(self, 'eventcal'):
            self.eventcal = self.to_event_cal()

        last = self.eventcal.getLastOccurrence()
        last_datetime = xmlutils.from_cdatetime(last, True) if last is not None else None

        # we're forced to return some date
        if last_datetime is None and force:
            last_datetime = self._recurrence_end()

        return last_datetime

    def get_next_instance(self, datetime):
        next_start = self.get_next_occurence(datetime)
        if next_start:
            instance = Event(from_string=str(self))
            instance.set_start(next_start)
            instance.set_recurrence(kolabformat.RecurrenceRule())  # remove recurrence rules
            instance.event.setRecurrenceID(instance.event.start(), False)
            next_end = self.get_occurence_end_date(next_start)
            if next_end:
                instance.set_end(next_end)

            return instance

        return None

    def _recurrence_end(self):
        """
            Determine a reasonable end date for infinitely recurring events
        """
        rrule = self.event.recurrenceRule()
        if rrule.isValid() and rrule.count() < 0 and not rrule.end().isValid():
            now = datetime.datetime.now()
            switch = {
                kolabformat.RecurrenceRule.Yearly: 100,
                kolabformat.RecurrenceRule.Monthly: 20
            }
            intvl = switch[rrule.frequency()] if rrule.frequency() in switch else 10
            return self.get_start().replace(year=now.year + intvl)

        return xmlutils.from_cdatetime(rrule.end(), True)


class EventIntegrityError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class InvalidEventDateError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class InvalidEventStatusError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

