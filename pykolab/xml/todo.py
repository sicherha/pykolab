import datetime
import kolabformat
import icalendar
import pytz

import pykolab
from pykolab import constants
from pykolab.xml import Event
from pykolab.xml import utils as xmlutils
from pykolab.xml.event import InvalidEventDateError
from pykolab.translate import _

log = pykolab.getLogger('pykolab.xml_todo')

def todo_from_ical(string):
    return Todo(from_ical=string)

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
            elif todo and part.has_key('Content-ID'):
                todo._attachment_parts.append(part)

    return todo

# FIXME: extend a generic pykolab.xml.Xcal class instead of Event
class Todo(Event):
    type = 'task'

    def __init__(self, from_ical="", from_string=""):
        self._attendees = []
        self._categories = []
        self._attachment_parts = []

        self.properties_map.update({
            "due": "get_due",
            "percent-complete": "get_percentcomplete",
            "duration": "void",
            "end": "void"
        })

        if from_ical == "":
            if from_string == "":
                self.event = kolabformat.Todo()
            else:
                self.event = kolabformat.readTodo(from_string, False)
                self._load_attendees()
        else:
            self.from_ical(from_ical)

        self.uid = self.get_uid()

    def from_ical(self, ical):
        if hasattr(icalendar.Todo, 'from_ical'):
            ical_todo = icalendar.Todo.from_ical(ical)
        elif hasattr(icalendar.Todo, 'from_string'):
            ical_todo = icalendar.Todo.from_string(ical)

        # use the libkolab calendaring bindings to load the full iCal data
        if ical_todo.has_key('ATTACH') or [part for part in ical_todo.walk() if part.name == 'VALARM']:
            self._xml_from_ical(ical)
        else:
            self.event = kolabformat.Todo()

        for attr in list(set(ical_todo.required)):
            if ical_todo.has_key(attr):
                self.set_from_ical(attr.lower(), ical_todo[attr])

        for attr in list(set(ical_todo.singletons)):
            if ical_todo.has_key(attr):
                self.set_from_ical(attr.lower(), ical_todo[attr])

        for attr in list(set(ical_todo.multiple)):
            if ical_todo.has_key(attr):
                self.set_from_ical(attr.lower(), ical_todo[attr])

        # although specified by RFC 2445/5545, icalendar doesn't have this property listed
        if ical_todo.has_key('PERCENT-COMPLETE'):
            self.set_from_ical('percentcomplete', ical_todo['PERCENT-COMPLETE'])

    def _xml_from_ical(self, ical):
        self.event = Todo()
        self.event.fromICal("BEGIN:VCALENDAR\nVERSION:2.0\n" + ical + "\nEND:VCALENDAR")

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
            raise InvalidEventDateError, _("Todo due needs datetime.date or datetime.datetime instance")

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
            raise TodoIntegrityError, kolabformat.errorMessage()


class TodoIntegrityError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
