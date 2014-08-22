import datetime
import pytz
import kolabformat
from dateutil.tz import tzlocal
from collections import OrderedDict

from pykolab.translate import _
from pykolab.translate import N_


def to_dt(dt):
    """
        Convert a naive date or datetime to a tz-aware datetime.
    """

    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime) or dt is not None and not hasattr(dt, 'hour'):
        dt = datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0, 0, tzinfo=tzlocal())

    elif isinstance(dt, datetime.datetime):
        if dt.tzinfo == None:
            return dt.replace(tzinfo=pytz.utc)

    return dt


def from_cdatetime(_cdatetime, with_timezone=True):
    """
        Convert from kolabformat.cDateTime to datetime.date(time)
    """
    if not _cdatetime.isValid():
        return None

    (
        year,
        month,
        day,
    ) = (
        _cdatetime.year(),
        _cdatetime.month(),
        _cdatetime.day(),
    )

    if _cdatetime.hour() == None or _cdatetime.hour() < 0:
        return datetime.date(year, month, day)

    (
        hour,
        minute,
        second
    ) = (
        _cdatetime.hour(),
        _cdatetime.minute(),
        _cdatetime.second()
    )

    if with_timezone:
        _timezone = _cdatetime.timezone()

        if _timezone == '' or _timezone == None:
            _timezone = pytz.utc
        else:
            _timezone = pytz.timezone(_timezone)

        return datetime.datetime(year, month, day, hour, minute, second, tzinfo=_timezone)

    else:
        return datetime.datetime(year, month, day, hour, minute, second)


def to_cdatetime(_datetime, with_timezone=True, as_utc=False):
    """
        Convert a datetime.dateime object into a kolabformat.cDateTime instance
    """
    # convert date into UTC timezone
    if as_utc and hasattr(_datetime, "tzinfo"):
        if _datetime.tzinfo is not None:
            _datetime = _datetime.astimezone(pytz.utc)
        else:
            datetime = _datetime.replace(tzinfo=pytz.utc)
        with_timezone = False

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
        _cdatetime = kolabformat.cDateTime(year, month, day, hour, minute, second)

    else:
        _cdatetime = kolabformat.cDateTime(year, month, day)

    if with_timezone and hasattr(_datetime, "tzinfo"):
        if _datetime.tzinfo.__str__() in ['UTC','GMT']:
            _cdatetime.setUTC(True)
        else:
            _cdatetime.setTimezone(_datetime.tzinfo.__str__())

    if as_utc:
        _cdatetime.setUTC(True)

    return _cdatetime


property_labels = {
    "name":        N_("Name"),
    "summary":     N_("Summary"),
    "location":    N_("Location"),
    "description": N_("Description"),
    "url":         N_("URL"),
    "status":      N_("Status"),
    "priority":    N_("Priority"),
    "attendee":    N_("Attendee"),
    "start":       N_("Start"),
    "end":         N_("End"),
    "due":         N_("Due"),
    "rrule":       N_("Repeat"),
    "exdate":      N_("Repeat Exception"),
    "organizer":   N_("Organizer"),
    "attach":      N_("Attachment"),
    "alarm":       N_("Alarm"),
    "classification":   N_("Classification"),
    "percent-complete": N_("Progress")
}

def property_label(propname):
    """
        Return a localized name for the given object property
    """
    return _(property_labels[propname]) if property_labels.has_key(propname) else _(propname)


def property_to_string(propname, value):
    """
        Render a human readable string for the given object property
    """
    date_format = _("%Y-%m-%d")
    time_format = _("%H:%M (%Z)")
    date_time_format = date_format + " " + time_format
    maxlen = 50

    if isinstance(value, datetime.datetime):
        return value.strftime(date_time_format)
    elif isinstance(value, datetime.date):
        return value.strftime(date_format)
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        if len(value) > maxlen:
            return value[:maxlen].rsplit(' ', 1)[0] + '...'
        return value
    elif isinstance(value, object) and hasattr(value, 'to_dict'):
        value = value.to_dict()

    if isinstance(value, dict):
        if propname == 'attendee':
            from . import attendee
            name = value['name'] if value.has_key('name') and not value['name'] == '' else value['email']
            return "%s, %s" % (name, attendee.participant_status_label(value['partstat']))

        elif propname == 'organizer':
            return value['name'] if value.has_key('name') and not value['name'] == '' else value['email']

        elif propname == 'rrule':
            from . import recurrence_rule
            rrule = recurrence_rule.frequency_label(value['frequency']) % (value['interval'])
            if value.has_key('count') and value['count'] > 0:
                rrule += " " + _("for %d times") % (value['count'])
            elif value.has_key('until') and (isinstance(value['until'], datetime.datetime) or isinstance(value['until'], datetime.date)):
                rrule += " " + _("until %s") % (value['until'].strftime(date_format))
            return rrule

        elif propname == 'alarm':
            alarm_type_labels = {
                'DISPLAY': _("Display message"),
                'EMAIL':   _("Send email"),
                'AUDIO':   _("Play sound")
            }
            alarm = alarm_type_labels.get(value['action'], "")
            if isinstance(value['trigger'], datetime.datetime):
                alarm += " @ " + property_to_string('trigger', value['trigger'])
            else:
                rel = _("%s after") if value['trigger']['related'] == 'END' else _("%s before")
                offsets = []
                try:
                    from icalendar import vDuration
                    duration = vDuration.from_ical(value['trigger']['value'].strip('-'))
                except:
                    return None

                if duration.days:
                    offsets.append(_("%d day(s)") % (duration.days))
                if duration.seconds:
                    hours = duration.seconds // 3600
                    minutes = duration.seconds % 3600 // 60
                    seconds = duration.seconds % 60
                    if hours:
                        offsets.append(_("%d hour(s)") % (hours))
                    if minutes or (hours and seconds):
                        offsets.append(_("%d minute(s)") % (minutes))
                if len(offsets):
                    alarm += " " + rel % (", ".join(offsets))

            return alarm

        elif propname == 'attach':
            return value['label'] if value.has_key('label') else value['fmttype']

    return None


def compute_diff(a, b, reduced=False):
    """
        List the differences between two given dicts
    """
    diff = []

    properties = a.keys()
    properties.extend([x for x in b.keys() if x not in properties])

    for prop in properties:
        aa = a[prop] if a.has_key(prop) else None
        bb = b[prop] if b.has_key(prop) else None

        # compare two lists
        if isinstance(aa, list) or isinstance(bb, list):
            if not isinstance(aa, list):
                aa = [aa]
            if not isinstance(bb, list):
                bb = [bb]
            index = 0
            length = max(len(aa), len(bb))
            while index < length:
                aai = aa[index] if index < len(aa) else None
                bbi = bb[index] if index < len(bb) else None
                if not compare_values(aai, bbi):
                    if reduced:
                        (old, new) = reduce_properties(aai, bbi)
                    else:
                        (old, new) = (aai, bbi)
                    diff.append(OrderedDict([('property', prop), ('index', index), ('old', old), ('new', new)]))
                index += 1

        # the two properties differ
        elif not compare_values(aa, bb):
            if reduced:
                (old, new) = reduce_properties(aa, bb)
            else:
                (old, new) = (aa, bb)
            diff.append(OrderedDict([('property', prop), ('old', old), ('new', new)]))

    return diff


def compare_values(aa, bb):
    ignore_keys = ['rsvp']
    if not aa.__class__ == bb.__class__:
        return False

    if isinstance(aa, dict) and isinstance(bb, dict):
        aa = dict(aa)
        bb = dict(bb)
        # ignore some properties for comparison
        for k in ignore_keys:
            aa.pop(k, None)
            bb.pop(k, None)

    return aa == bb


def reduce_properties(aa, bb):
    """
        Compares two given structs and removes equal values in bb
    """
    if not isinstance(aa, dict) or not isinstance(bb, dict):
        return (aa, bb)

    properties = aa.keys()
    properties.extend([x for x in bb.keys() if x not in properties])

    for prop in properties:
        if not aa.has_key(prop) or not bb.has_key(prop):
            continue
        if isinstance(aa[prop], dict) and isinstance(bb[prop], dict):
            (aa[prop], bb[prop]) = reduce_properties(aa[prop], bb[prop])
        if aa[prop] == bb[prop]:
            # del aa[prop]
            del bb[prop]

    return (aa, bb)
