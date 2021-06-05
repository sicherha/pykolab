import datetime
import kolabformat
import icalendar
import pytz
import base64

import pykolab
from pykolab import constants
from pykolab.xml import Event
from pykolab.xml import RecurrenceRule
from pykolab.xml import utils as xmlutils
from pykolab.xml.event import InvalidEventDateError
from pykolab.translate import _

log = pykolab.getLogger('pykolab.xml_todo')

def todo_from_ical(ical, string=None):
    return Todo(from_ical=ical, from_string=string)

def todo_from_string(string):
    return Todo(from_string=string)

def todo_from_message(message):
    todo = None
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "application/calendar+xml":
                payload = part.get_payload(decode=True)
                todo = todo_from_string(payload)

            # append attachment parts to Todo object
            elif todo and 'Content-ID' in part:
                todo._attachment_parts.append(part)

    return todo

# FIXME: extend a generic pykolab.xml.Xcal class instead of Event
class Todo(Event):
    type = 'task'

    # This have to be a copy (see T1221)
    properties_map = Event.properties_map.copy()

    def __init__(self, from_ical="", from_string=""):
        self._attendees = []
        self._categories = []
        self._exceptions = []
        self._attachment_parts = []

        self.properties_map.update({
            "due": "get_due",
            "percent-complete": "get_percentcomplete",
            "related-to": "get_related_to",
            "duration": "void",
            "end": "void"
        })

        if isinstance(from_ical, str) and from_ical == "":
            if from_string == "":
                self.event = kolabformat.Todo()
            else:
                self.event = kolabformat.readTodo(from_string, False)
                self._load_attendees()
        else:
            self.from_ical(from_ical, from_string)

        self.set_created(self.get_created())
        self.uid = self.get_uid()

    def from_ical(self, ical, raw):
        if isinstance(ical, icalendar.Todo):
            ical_todo = ical
        elif hasattr(icalendar.Todo, 'from_ical'):
            ical_todo = icalendar.Todo.from_ical(ical)
        elif hasattr(icalendar.Todo, 'from_string'):
            ical_todo = icalendar.Todo.from_string(ical)

        # VCALENDAR block was given, find the first VTODO item
        if isinstance(ical_todo, icalendar.Calendar):
            for c in ical_todo.walk():
                if c.name == 'VTODO':
                    ical_todo = c
                    break

        log.debug("Todo.from_ical(); %r, %r, %r" % (type(ical_todo), 'ATTACH' in ical_todo, 'ATTENDEE' in ical_todo), level=8)

        # DISABLED: use the libkolab calendaring bindings to load the full iCal data
        # TODO: this requires support for iCal parsing in the kolab.calendaring bindings
        if False and 'ATTACH' in ical_todo or [part for part in ical_todo.walk() if part.name == 'VALARM']:
            if raw is None or raw == "":
                raw = ical if isinstance(ical, str) else ical.to_ical()
            self._xml_from_ical(raw)
        else:
            self.event = kolabformat.Todo()

        for attr in list(set(ical_todo.required)):
            if attr in ical_todo:
                self.set_from_ical(attr.lower(), ical_todo[attr])

        for attr in list(set(ical_todo.singletons)):
            if attr in ical_todo:
                if isinstance(ical_todo[attr], list):
                    ical_todo[attr] = ical_todo[attr][0];
                self.set_from_ical(attr.lower(), ical_todo[attr])

        for attr in list(set(ical_todo.multiple)):
            if attr in ical_todo:
                self.set_from_ical(attr.lower(), ical_todo[attr])

        # although specified by RFC 2445/5545, icalendar doesn't have this property listed
        if 'PERCENT-COMPLETE' in ical_todo:
            self.set_from_ical('percentcomplete', ical_todo['PERCENT-COMPLETE'])

    def _xml_from_ical(self, ical):
        # FIXME: kolabformat or kolab.calendaring modules do not provide bindings to import Todo from iCal
        self.event = Todo()

    def set_ical_attach(self, attachment):
        if hasattr(attachment, 'params'):
            params = attachment.params
        else:
            params = {}

        _attachment = kolabformat.Attachment()
        if 'FMTTYPE' in params:
            mimetype = str(params['FMTTYPE'])
        else:
            mimetype = 'application/octet-stream'

        if 'X-LABEL' in params:
            _attachment.setLabel(str(params['X-LABEL']))

        decode = False
        if 'ENCODING' in params:
            if params['ENCODING'] == "BASE64" or params['ENCODING'] == "B":
                decode = True

        _attachment.setData(base64.b64decode(str(attachment)) if decode else str(attachment), mimetype)
        vattach = self.event.attachments()
        vattach.append(_attachment)
        self.event.setAttachments(vattach)

    def set_ical_rrule(self, rrule):
        _rrule = RecurrenceRule()
        _rrule.from_ical(rrule)
        if _rrule.isValid():
            self.event.setRecurrenceRule(_rrule)

    def set_ical_due(self, due):
        self.set_due(due)

    def set_due(self, _datetime):
        valid_datetime = False
        if isinstance(_datetime, datetime.date):
            valid_datetime = True

        if isinstance(_datetime, datetime.datetime):
            # If no timezone information is passed on, make it UTC
            if _datetime.tzinfo == None:
                _datetime = _datetime.replace(tzinfo=pytz.utc)

            valid_datetime = True

        if not valid_datetime:
            raise InvalidEventDateError(_("Todo due needs datetime.date or datetime.datetime instance"))

        self.event.setDue(xmlutils.to_cdatetime(_datetime, True))

    def set_ical_percent(self, percent):
        self.set_percentcomplete(percent)

    def set_percentcomplete(self, percent):
        self.event.setPercentComplete(int(percent))

    def set_transparency(self, transp):
        # empty stub
        pass

    def get_due(self):
        return xmlutils.from_cdatetime(self.event.due(), True)

    def get_ical_due(self):
        dt = self.get_due()
        if dt:
            return icalendar.vDatetime(dt)
        return None

    def get_percentcomplete(self):
        return self.event.percentComplete()

    def get_duration(self):
        return None

    def get_related_to(self):
        for x in self.event.relatedTo():
            return x
        return None

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
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', method)

        ical_todo = icalendar.Todo()

        singletons = list(set(ical_todo.singletons))
        singletons.extend(['PERCENT-COMPLETE'])
        for attr in singletons:
            ical_getter = 'get_ical_%s' % (attr.lower())
            default_getter = 'get_%s' % (attr.lower())
            retval = None
            if hasattr(self, ical_getter):
                retval = getattr(self, ical_getter)()
                if not retval == None and not retval == "":
                    ical_todo.add(attr.lower(), retval)
            elif hasattr(self, default_getter):
                retval = getattr(self, default_getter)()
                if not retval == None and not retval == "":
                    ical_todo.add(attr.lower(), retval, encode=0)

        for attr in list(set(ical_todo.multiple)):
            ical_getter = 'get_ical_%s' % (attr.lower())
            default_getter = 'get_%s' % (attr.lower())
            retval = None
            if hasattr(self, ical_getter):
                retval = getattr(self, ical_getter)()
            elif hasattr(self, default_getter):
                retval = getattr(self, default_getter)()

            if isinstance(retval, list) and not len(retval) == 0:
                for _retval in retval:
                    ical_todo.add(attr.lower(), _retval, encode=0)

        # copy custom properties to iCal
        for cs in self.event.customProperties():
            ical_todo.add(cs.identifier, cs.value)

        cal.add_component(ical_todo)

        if hasattr(cal, 'to_ical'):
            return cal.to_ical()
        elif hasattr(cal, 'as_string'):
            return cal.as_string()

    def __str__(self):
        xml = kolabformat.writeTodo(self.event)

        error = kolabformat.error()

        if error == None or not error:
            return xml
        else:
            raise TodoIntegrityError(kolabformat.errorMessage())


class TodoIntegrityError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
