import datetime
import icalendar
import kolabformat
import pytz
import time
import uuid
import base64
import re

import pykolab
from pykolab import constants
from pykolab import utils
from pykolab.xml import utils as xmlutils
from pykolab.xml import participant_status_label
from pykolab.translate import _

from os import path
from attendee import Attendee
from contact_reference import ContactReference
from recurrence_rule import RecurrenceRule

log = pykolab.getLogger('pykolab.xml_event')

def ustr(s):
    if not isinstance(s, unicode):
        for cs in ['utf-8','latin-1']:
            try:
                s = unicode(s, cs)
                break
            except:
                pass

    if isinstance(s, unicode):
        return s.encode('utf-8')

    return s

def event_from_ical(ical, string=None):
    return Event(from_ical=ical, from_string=string)

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
    type = 'event'
    thisandfuture = False

    status_map = {
            None: kolabformat.StatusUndefined,
            "TENTATIVE": kolabformat.StatusTentative,
            "CONFIRMED": kolabformat.StatusConfirmed,
            "CANCELLED": kolabformat.StatusCancelled,
            "COMPLETD":  kolabformat.StatusCompleted,
            "IN-PROCESS": kolabformat.StatusInProcess,
            "NEEDS-ACTION": kolabformat.StatusNeedsAction,
        }

    classification_map = {
            "PUBLIC": kolabformat.ClassPublic,
            "PRIVATE": kolabformat.ClassPrivate,
            "CONFIDENTIAL": kolabformat.ClassConfidential,
        }

    alarm_type_map = {
            'EMAIL': kolabformat.Alarm.EMailAlarm,
            'DISPLAY': kolabformat.Alarm.DisplayAlarm,
            'AUDIO': kolabformat.Alarm.AudioAlarm
        }

    related_map = {
            'START': kolabformat.Start,
            'END': kolabformat.End
        }

    properties_map = {
        # property: getter
        "uid": "get_uid",
        "created": "get_created",
        "lastmodified-date": "get_lastmodified",
        "sequence": "sequence",
        "classification": "get_classification",
        "categories": "categories",
        "start": "get_start",
        "end": "get_end",
        "duration": "get_duration",
        "transparency": "transparency",
        "rrule": "recurrenceRule",
        "rdate": "recurrenceDates",
        "exdate": "exceptionDates",
        "recurrence-id": "recurrenceID",
        "summary": "summary",
        "description": "description",
        "priority": "priority",
        "status": "get_ical_status",
        "location": "location",
        "organizer": "organizer",
        "attendee": "get_attendees",
        "attach": "attachments",
        "url": "url",
        "alarm": "alarms",
        "x-custom": "customProperties",
        # TODO: add to_dict() support for these
        # "exception": "exceptions",
    }

    def __init__(self, from_ical="", from_string=""):
        self._attendees = []
        self._categories = []
        self._exceptions = []
        self._attachment_parts = []

        if isinstance(from_ical, str) and from_ical == "":
            if from_string == "":
                self.event = kolabformat.Event()
            else:
                self.event = kolabformat.readEvent(from_string, False)
                self._load_attendees()
                self._load_exceptions()
        else:
            self.from_ical(from_ical, from_string)

        self.uid = self.get_uid()

    def _load_attendees(self):
        for a in self.event.attendees():
            att = Attendee(a.contact().email())
            att.copy_from(a)
            self._attendees.append(att)

    def _load_exceptions(self):
        for ex in self.event.exceptions():
            exception = Event()
            exception.uid = ex.uid()
            exception.event = ex
            exception._load_attendees()
            self._exceptions.append(exception)

    def add_attendee(self, email_or_attendee, name=None, rsvp=False, role=None, participant_status=None, cutype="INDIVIDUAL", params=None):
        if isinstance(email_or_attendee, Attendee):
            attendee = email_or_attendee
        else:
            attendee = Attendee(email_or_attendee, name, rsvp, role, participant_status, cutype, params)

        # apply update to self and all exceptions
        self.update_attendees([attendee])

    def add_category(self, category):
        self._categories.append(ustr(category))
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

    def add_exception(self, exception):
        # sanity checks
        if not self.is_recurring():
            raise EventIntegrityError, "Cannot add exceptions to a non-recurring event"

        recurrence_id = exception.get_recurrence_id()
        if recurrence_id is None:
            raise EventIntegrityError, "Recurrence exceptions require a Recurrence-ID property"

        # check if an exception with the given recurrence-id already exists
        append = True
        vexceptions = self.event.exceptions()
        for i, ex in enumerate(self._exceptions):
            if ex.get_recurrence_id() == recurrence_id and ex.thisandfuture == exception.thisandfuture:
                # update the existing exception
                vexceptions[i] = exception.event
                self._exceptions[i] = exception
                append = False

        if append:
            vexceptions.append(exception.event)
            self._exceptions.append(exception)

        self.event.setExceptions(vexceptions)

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

        cal.add_component(self.to_ical())

        # add recurrence exceptions
        if len(self._exceptions) > 0 and not method == 'REPLY':
            for exception in self._exceptions:
                cal.add_component(exception.to_ical())

        if hasattr(cal, 'to_ical'):
            return cal.to_ical()
        elif hasattr(cal, 'as_string'):
            return cal.as_string()

    def to_ical(self):
        event = icalendar.Event()

        # Required
        event['uid'] = self.get_uid()

        # NOTE: Make sure to list(set()) or duplicates may arise
        for attr in list(set(event.singletons)):
            _attr = attr.lower().replace('-', '')
            ical_getter = 'get_ical_%s' % (_attr)
            default_getter = 'get_%s' % (_attr)
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
            _attr = attr.lower().replace('-', '')
            ical_getter = 'get_ical_%s' % (_attr)
            default_getter = 'get_%s' % (_attr)
            retval = None
            if hasattr(self, ical_getter):
                retval = getattr(self, ical_getter)()
            elif hasattr(self, default_getter):
                retval = getattr(self, default_getter)()

            if isinstance(retval, list) and not len(retval) == 0:
                for _retval in retval:
                    event.add(attr.lower(), _retval, encode=0)

        # copy custom properties to iCal
        for cs in self.event.customProperties():
            event.add(cs.identifier, cs.value)

        return event

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

    def from_ical(self, ical, raw=None):
        if isinstance(ical, icalendar.Event) or isinstance(ical, icalendar.Calendar):
            ical_event = ical
        elif hasattr(icalendar.Event, 'from_ical'):
            ical_event = icalendar.Event.from_ical(ical)
        elif hasattr(icalendar.Event, 'from_string'):
            ical_event = icalendar.Event.from_string(ical)

        # VCALENDAR block was given, find the first VEVENT item
        if isinstance(ical_event, icalendar.Calendar):
            for c in ical_event.walk():
                if c.name == 'VEVENT':
                    ical_event = c
                    break

        # use the libkolab calendaring bindings to load the full iCal data
        if ical_event.has_key('RRULE') or ical_event.has_key('ATTACH') \
             or [part for part in ical_event.walk() if part.name == 'VALARM']:
            if raw is None or raw == "":
                raw = ical if isinstance(ical, str) else ical.to_ical()
            self._xml_from_ical(raw)
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
        if not "BEGIN:VCALENDAR" in ical:
            ical = "BEGIN:VCALENDAR\nVERSION:2.0\n" + ical + "\nEND:VCALENDAR"
        from kolab.calendaring import EventCal
        self.event = EventCal()
        success = self.event.fromICal(ical)
        if success:
            self._load_exceptions()
        return success

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

    def find_attendee(self, attendee):
        try:
            return self.get_attendee(attendee)
        except:
            return None

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
            return xmlutils.from_cdatetime(self.event.created(), True)
        except ValueError:
            return datetime.datetime.now()

    def get_description(self):
        return self.event.description()

    def get_comment(self):
        if hasattr(self.event, 'comment'):
            return self.event.comment()
        else:
            return None

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

    def get_date_text(self, date_format=None, time_format=None):
        if date_format is None:
            date_format = _("%Y-%m-%d")
        if time_format is None:
            time_format = _("%H:%M (%Z)")

        start = self.get_start()
        end = self.get_end()
        all_day = not hasattr(start, 'date')
        start_date = start.date() if not all_day else start
        end_date = end.date() if not all_day else end

        if start_date == end_date:
            end_format = time_format
        else:
            end_format = date_format + " " + time_format

        if all_day:
            time_format = ''
            if start_date == end_date:
                return start.strftime(date_format)

        return "%s - %s" % (start.strftime(date_format + " " + time_format), end.strftime(end_format))

    def get_exception_dates(self):
        return map(lambda _: xmlutils.from_cdatetime(_, True), self.event.exceptionDates())

    def get_exceptions(self):
        return self._exceptions

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
        dtend = self.get_end()
        # shift end by one day on all-day events
        if not hasattr(dtend, 'hour'):
            dtend = dtend + datetime.timedelta(days=1)
        return dtend

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

        return self._translate_value(status, self.status_map) if status else None

    def get_ical_class(self):
        class_ = self.event.classification()
        return self._translate_value(class_, self.classification_map) if class_ else None

    def get_ical_sequence(self):
        return str(self.event.sequence()) if self.event.sequence() else None

    def get_ical_comment(self):
        comment = self.get_comment()
        if comment is not None:
            return [ comment ]
        return None

    def get_ical_recurrenceid(self):
        rid = self.get_recurrence_id()
        if isinstance(rid, datetime.datetime) or isinstance(rid, datetime.date):
            prop = icalendar.vDatetime(rid)
            if self.thisandfuture:
                prop.params.update({'RANGE':'THISANDFUTURE'})
            return prop

        return None

    def get_location(self):
        return self.event.location()

    def get_lastmodified(self):
        try:
            _datetime = self.event.lastModified()
            if retval == None or retval == "":
                self.__str__()
        except:
            self.__str__()

        return xmlutils.from_cdatetime(self.event.lastModified(), True)

    def get_organizer(self):
        organizer = self.event.organizer()
        return organizer

    def get_priority(self):
        return str(self.event.priority())

    def get_start(self):
        return xmlutils.from_cdatetime(self.event.start(), True)

    def get_status(self, translated=False):
        status = self.event.status()
        if translated:
            return self._translate_value(status, self.status_map) if status else None

        return status

    def get_summary(self):
        return self.event.summary()

    def get_uid(self):
        uid = self.event.uid()
        if not uid == '':
            return uid
        else:
            self.set_uid(uuid.uuid4())
            return self.get_uid()

    def get_recurrence_id(self):
        self.thisandfuture = self.event.thisAndFuture();
        return xmlutils.from_cdatetime(self.event.recurrenceID(), True)

    def get_thisandfuture(self):
        self.thisandfuture = self.event.thisAndFuture();
        return self.thisandfuture

    def get_sequence(self):
        return self.event.sequence()

    def get_url(self):
        return self.event.url()

    def get_transparency(self):
        return self.event.transparency()

    def set_attendees(self, _attendees):
        self._attendees = _attendees
        self.event.setAttendees(self._attendees)

        # apply update to all exceptions
        for exception in self._exceptions:
            exception.merge_attendee_data(_attendees)

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

        # apply update to self and all exceptions
        self.update_attendees([attendee])

    def update_attendees(self, _attendees):
        self.merge_attendee_data(_attendees)

        for exception in self._exceptions:
            exception.merge_attendee_data(_attendees)

    def merge_attendee_data(self, _attendees):
        for attendee in _attendees:
            found = False

            for candidate in self._attendees:
                if candidate.get_email() == attendee.get_email():
                    candidate.copy_from(attendee)
                    found = True
                    break

            if not found:
                self._attendees.append(attendee)

        self.event.setAttendees(self._attendees)

    def set_classification(self, classification):
        if classification in self.classification_map.keys():
            self.event.setClassification(self.classification_map[classification])
        elif classification in self.classification_map.values():
            self.event.setClassification(status)
        else:
            raise ValueError, _("Invalid classification %r") % (classification)

    def set_created(self, _datetime=None):
        if _datetime == None:
            _datetime = datetime.datetime.utcnow()

        self.event.setCreated(xmlutils.to_cdatetime(_datetime, False, True))

    def set_description(self, description):
        self.event.setDescription(ustr(description))

    def set_comment(self, comment):
        if hasattr(self.event, 'setComment'):
            self.event.setComment(ustr(comment))

    def set_dtstamp(self, _datetime):
        self.event.setLastModified(xmlutils.to_cdatetime(_datetime, False, True))

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

    def add_custom_property(self, name, value):
        if not name.upper().startswith('X-'):
            raise ValueError, _("Invalid custom property name %r") % (name)

        props = self.event.customProperties()
        props.append(kolabformat.CustomProperty(name.upper(), value))
        self.event.setCustomProperties(props)

    def set_from_ical(self, attr, value):
        attr = attr.replace('-', '')
        ical_setter = 'set_ical_' + attr
        default_setter = 'set_' + attr
        params = value.params if hasattr(value, 'params') else {}

        if isinstance(value, icalendar.vDDDTypes) and hasattr(value, 'dt'):
            value = value.dt

        if attr == "categories":
            self.add_category(value)
        elif attr == "class":
            self.set_classification(value)
        elif attr == "recurrenceid":
            self.set_ical_recurrenceid(value, params)
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
                    name = ustr(params['CN'])
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
        # shift end by one day on all-day events
        if not hasattr(dtend, 'hour'):
            dtend = dtend - datetime.timedelta(days=1)
        self.set_end(dtend)

    def set_ical_dtstamp(self, dtstamp):
        self.set_dtstamp(dtstamp)

    def set_ical_dtstart(self, dtstart):
        self.set_start(dtstart)

    def set_ical_lastmodified(self, lastmod):
        self.set_lastmodified(lastmod)

    def set_ical_duration(self, value):
        if hasattr(value, 'dt'):
            value = value.dt

        duration = kolabformat.Duration(value.days, 0, 0, value.seconds, False)
        self.event.setDuration(duration)

    def set_ical_organizer(self, organizer):
        address = str(organizer).split(':')[-1]

        cn = None

        if hasattr(organizer, 'params'):
            params = organizer.params
        else:
            params = {}

        if params.has_key('CN'):
            cn = ustr(params['CN'])

        self.set_organizer(str(address), name=cn)

    def set_ical_priority(self, priority):
        self.set_priority(priority)

    def set_ical_sequence(self, sequence):
        self.set_sequence(sequence)

    def set_ical_summary(self, summary):
        self.set_summary(ustr(summary))

    def set_ical_uid(self, uid):
        self.set_uid(str(uid))

    def set_ical_recurrenceid(self, value, params):
        try:
            self.thisandfuture = params.get('RANGE', '') == 'THISANDFUTURE'
            self.set_recurrence_id(value, self.thisandfuture)
        except InvalidEventDateError, e:
            pass

    def set_lastmodified(self, _datetime=None):
        valid_datetime = False
        if isinstance(_datetime, datetime.date):
            valid_datetime = True

        if isinstance(_datetime, datetime.datetime):
            valid_datetime = True

        if _datetime == None:
            valid_datetime = True
            _datetime = datetime.datetime.utcnow()

        if not valid_datetime:
            raise InvalidEventDateError, _("Event start needs datetime.date or datetime.datetime instance")

        self.event.setLastModified(xmlutils.to_cdatetime(_datetime, False, True))

    def set_location(self, location):
        self.event.setLocation(ustr(location))

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
        elif not status == kolabformat.StatusUndefined:
            raise InvalidEventStatusError, _("Invalid status set: %r") % (status)

    def set_summary(self, summary):
        self.event.setSummary(summary)

    def set_uid(self, uid):
        self.uid = uid
        self.event.setUid(str(uid))

    def set_recurrence_id(self, _datetime, _thisandfuture=None):
        valid_datetime = False
        if isinstance(_datetime, datetime.date):
            valid_datetime = True

        if isinstance(_datetime, datetime.datetime):
            # If no timezone information is passed on, use the one from event start
            if _datetime.tzinfo == None:
                _start = self.get_start()
                _datetime = _datetime.replace(tzinfo=_start.tzinfo)

            valid_datetime = True

        if not valid_datetime:
            raise InvalidEventDateError, _("Event recurrence-id needs datetime.datetime instance")

        if _thisandfuture is None:
            _thisandfuture = self.thisandfuture

        self.event.setRecurrenceID(xmlutils.to_cdatetime(_datetime), _thisandfuture)

    def set_transparency(self, transp):
        return self.event.setTransparency(transp)

    def __str__(self):
        event_xml = kolabformat.writeEvent(self.event)

        error = kolabformat.error()

        if error == None or not error:
            return event_xml
        else:
            raise EventIntegrityError, kolabformat.errorMessage()

    def to_dict(self):
        data = dict()

        for p, getter in self.properties_map.iteritems():
            val = None
            if hasattr(self, getter):
                val = getattr(self, getter)()
            elif hasattr(self.event, getter):
                val = getattr(self.event, getter)()

            if isinstance(val, kolabformat.cDateTime):
                val = xmlutils.from_cdatetime(val, True)
            elif isinstance(val, kolabformat.vectordatetime):
                val = [xmlutils.from_cdatetime(x, True) for x in val]
            elif isinstance(val, kolabformat.vectors):
                val = [str(x) for x in val]
            elif isinstance(val, kolabformat.vectorcs):
                for x in val:
                    data[x.identifier] = x.value
                val = None
            elif isinstance(val, kolabformat.ContactReference):
                val = ContactReference(val).to_dict()
            elif isinstance(val, kolabformat.RecurrenceRule):
                val = RecurrenceRule(val).to_dict()
            elif isinstance(val, kolabformat.vectorattachment):
                val = [dict(fmttype=x.mimetype(), label=x.label(), uri=x.uri()) for x in val]
            elif isinstance(val, kolabformat.vectoralarm):
                val = [self._alarm_to_dict(x) for x in val]
            elif isinstance(val, list):
                val = [x.to_dict() for x in val if hasattr(x, 'to_dict')]

            if val is not None:
                data[p] = val

        return data

    def _alarm_to_dict(self, alarm):
        ret = dict(
            action=self._translate_value(alarm.type(), self.alarm_type_map),
            summary=alarm.summary(),
            description=alarm.description(),
            trigger=None
        )

        start = alarm.start()
        if start and start.isValid():
            ret['trigger'] = xmlutils.from_cdatetime(start, True)
        else:
            ret['trigger'] = dict(related=self._translate_value(alarm.relativeTo(), self.related_map))
            duration = alarm.relativeStart()
            if duration and duration.isValid():
                prefix = '-' if duration.isNegative() else '+'
                value = prefix + "P%dW%dDT%dH%dM%dS" % (
                    duration.weeks(), duration.days(), duration.hours(), duration.minutes(), duration.seconds()
                )
                ret['trigger']['value'] = re.sub(r"T$", '', re.sub(r"0[WDHMS]", '', value))

        if alarm.type() == kolabformat.Alarm.EMailAlarm:
            ret['attendee'] = [ContactReference(a).to_dict() for a in alarm.attendees()]

        return ret

    def _translate_value(self, val, map):
        name_map = dict([(v, k) for (k, v) in map.iteritems()])
        return name_map[val] if name_map.has_key(val) else 'UNKNOWN'

    def to_message(self, creator=None):
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase
        from email.MIMEText import MIMEText
        from email.Utils import COMMASPACE, formatdate

        msg = MIMEMultipart()
        organizer = self.get_organizer()
        email = organizer.email()
        name = organizer.name()

        if creator:
            msg['From'] = creator
        elif not name:
            msg['From'] = email
        else:
            msg['From'] = '"%s" <%s>' % (name, email)

        msg['To'] = ', '.join([x.__str__() for x in self.get_attendees()])
        msg['Date'] = formatdate(localtime=True)

        msg.add_header('X-Kolab-MIME-Version', '3.0')
        msg.add_header('X-Kolab-Type', 'application/x-vnd.kolab.' + self.type)

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

        # encode unicode strings with quoted-printable
        from email import charset
        charset.add_charset('utf-8', charset.SHORTEST, charset.QP)

        msg = MIMEMultipart()

        msg_from = None
        attendees = None

        if method == "REPLY":
            # TODO: Make user friendly name <email>
            msg['To'] = self.get_organizer().email()

            attendees = self.get_attendees()
            reply_attendees = []

            # There's an exception here for delegation (partstat DELEGATED)
            for attendee in attendees:
                if attendee.get_email() == from_address:
                    # Only the attendee is supposed to be listed in a reply
                    attendee.set_participant_status(participant_status)
                    attendee.set_rsvp(False)

                    reply_attendees.append(attendee)

                    name = attendee.get_name()
                    email = attendee.get_email()

                    if not name:
                        msg_from = email
                    else:
                        msg_from = '"%s" <%s>' % (name, email)

                elif from_address in attendee.get_delegated_from(True):
                    reply_attendees.append(attendee)

            # keep only replying (and delegated) attendee(s)
            self._attendees = reply_attendees
            self.event.setAttendees(self._attendees)

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

        msg['From'] = utils.str2unicode(msg_from)

        msg['Date'] = formatdate(localtime=True)

        if subject is None:
            subject = _("Invitation for %s was %s") % (self.get_summary(), participant_status_label(participant_status))

        msg['Subject'] = utils.str2unicode(subject)

        if message_text is None:
            message_text = _("""This is an automated response to one of your event requests.""")

        msg.attach(MIMEText(utils.stripped_message(message_text), _charset='utf-8'))

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

    def get_next_occurence(self, _datetime):
        if not hasattr(self, 'eventcal'):
            self.eventcal = self.to_event_cal()

        next_cdatetime = self.eventcal.getNextOccurence(xmlutils.to_cdatetime(_datetime, True))
        next_datetime  = xmlutils.from_cdatetime(next_cdatetime, True) if next_cdatetime is not None else None

        # cut infinite recurrence at a reasonable point
        if next_datetime and not self.get_last_occurrence() and next_datetime > xmlutils.to_dt(self._recurrence_end()):
            next_datetime = None

        # next_datetime is always a cdatetime, convert to date if necessary
        if not isinstance(self.get_start(), datetime.datetime):
            next_datetime = datetime.date(next_datetime.year, next_datetime.month, next_datetime.day)

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
            instance.event.setRecurrenceID(xmlutils.to_cdatetime(next_start), False)
            next_end = self.get_occurence_end_date(next_start)
            if next_end:
                instance.set_end(next_end)

            # unset recurrence rule and exceptions
            instance.set_recurrence(kolabformat.RecurrenceRule())
            instance.event.setExceptions(kolabformat.vectorevent())
            instance.event.setExceptionDates(kolabformat.vectordatetime())
            instance._exceptions = []
            instance._isexception = False

            # copy data from matching exception
            # (give precedence to single occurrence exceptions over thisandfuture)
            for exception in self._exceptions:
                recurrence_id = exception.get_recurrence_id()
                if recurrence_id == next_start and (not exception.thisandfuture or not instance._isexception):
                    instance = exception
                    instance._isexception = True
                    if not exception.thisandfuture:
                        break
                elif exception.thisandfuture and next_start > recurrence_id:
                    # TODO: merge exception properties over this instance + adjust start/end with the according offset
                    pass

            return instance

        return None

    def get_instance(self, _datetime):
        # If no timezone information is given, use the one from event start
        if _datetime.tzinfo == None:
            _start = self.get_start()
            _datetime = _datetime.replace(tzinfo=_start.tzinfo)

        instance = self.get_next_instance(_datetime - datetime.timedelta(days=1))
        while instance:
            recurrence_id = instance.get_recurrence_id()
            if type(recurrence_id) == type(_datetime) and recurrence_id <= _datetime:
                if recurrence_id == _datetime:
                    return instance
                instance = self.get_next_instance(instance.get_start())
            else:
                break

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

