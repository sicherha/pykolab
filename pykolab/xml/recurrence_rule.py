import pytz
import icalendar
import datetime
import kolabformat
from pykolab.xml import utils as xmlutils

from pykolab.translate import _
from pykolab.translate import N_

"""
    def setFrequency(self, *args): return _kolabformat.RecurrenceRule_setFrequency(self, *args)
    def frequency(self): return _kolabformat.RecurrenceRule_frequency(self)
    def setWeekStart(self, *args): return _kolabformat.RecurrenceRule_setWeekStart(self, *args)
    def weekStart(self): return _kolabformat.RecurrenceRule_weekStart(self)
    def setEnd(self, *args): return _kolabformat.RecurrenceRule_setEnd(self, *args)
    def end(self): return _kolabformat.RecurrenceRule_end(self)
    def setCount(self, *args): return _kolabformat.RecurrenceRule_setCount(self, *args)
    def count(self): return _kolabformat.RecurrenceRule_count(self)
    def setInterval(self, *args): return _kolabformat.RecurrenceRule_setInterval(self, *args)
    def interval(self): return _kolabformat.RecurrenceRule_interval(self)
    def setBysecond(self, *args): return _kolabformat.RecurrenceRule_setBysecond(self, *args)
    def bysecond(self): return _kolabformat.RecurrenceRule_bysecond(self)
    def setByminute(self, *args): return _kolabformat.RecurrenceRule_setByminute(self, *args)
    def byminute(self): return _kolabformat.RecurrenceRule_byminute(self)
    def setByhour(self, *args): return _kolabformat.RecurrenceRule_setByhour(self, *args)
    def byhour(self): return _kolabformat.RecurrenceRule_byhour(self)
    def setByday(self, *args): return _kolabformat.RecurrenceRule_setByday(self, *args)
    def byday(self): return _kolabformat.RecurrenceRule_byday(self)
    def setBymonthday(self, *args): return _kolabformat.RecurrenceRule_setBymonthday(self, *args)
    def bymonthday(self): return _kolabformat.RecurrenceRule_bymonthday(self)
    def setByyearday(self, *args): return _kolabformat.RecurrenceRule_setByyearday(self, *args)
    def byyearday(self): return _kolabformat.RecurrenceRule_byyearday(self)
    def setByweekno(self, *args): return _kolabformat.RecurrenceRule_setByweekno(self, *args)
    def byweekno(self): return _kolabformat.RecurrenceRule_byweekno(self)
    def setBymonth(self, *args): return _kolabformat.RecurrenceRule_setBymonth(self, *args)
    def bymonth(self): return _kolabformat.RecurrenceRule_bymonth(self)
    def isValid(self): return _kolabformat.RecurrenceRule_isValid(self)
"""

frequency_labels = {
    "YEARLY":   N_("Every %d year(s)"),
    "MONTHLY":  N_("Every %d month(s)"),
    "WEEKLY":   N_("Every %d week(s)"),
    "DAILY":    N_("Every %d day(s)"),
    "HOURLY":   N_("Every %d hours"),
    "MINUTELY": N_("Every %d minutes"),
    "SECONDLY": N_("Every %d seconds")
}

def frequency_label(freq):
    return _(frequency_labels[freq]) if frequency_labels.has_key(freq) else _(freq)


class RecurrenceRule(kolabformat.RecurrenceRule):
    frequency_map = {
        None: kolabformat.RecurrenceRule.FreqNone,
        "YEARLY": kolabformat.RecurrenceRule.Yearly,
        "MONTHLY": kolabformat.RecurrenceRule.Monthly,
        "WEEKLY": kolabformat.RecurrenceRule.Weekly,
        "DAILY": kolabformat.RecurrenceRule.Daily,
        "HOURLY": kolabformat.RecurrenceRule.Hourly,
        "MINUTELY": kolabformat.RecurrenceRule.Minutely,
        "SECONDLY": kolabformat.RecurrenceRule.Secondly
    }

    weekday_map = {
        "MO": kolabformat.Monday,
        "TU": kolabformat.Tuesday,
        "WE": kolabformat.Wednesday,
        "TH": kolabformat.Thursday,
        "FR": kolabformat.Friday,
        "SA": kolabformat.Saturday,
        "SU": kolabformat.Sunday
    }

    properties_map = {
        'freq': 'get_frequency',
        'interval':  'interval',
        'count':     'count',
        'until':     'end',
        'bymonth':   'bymonth',
        'byday':     'byday',
        'bymonthday':'bymonthday',
        'byyearday': 'byyearday',
        'byweekno':  'byweekno',
        'byhour':    'byhour',
        'byminute':  'byminute',
        'wkst':      'get_weekstart'
    }

    def __init__(self, rrule=None):
        if rrule == None:
            kolabformat.RecurrenceRule.__init__(self)
        else:
            kolabformat.RecurrenceRule.__init__(self, rrule)

    def from_ical(self, vrecur):
        vectorimap = {
            'BYSECOND': 'setBysecond',
            'BYMINUTE': 'setByminute',
            'BYHOUR': 'setByhour',
            'BYMONTHDAY': 'setBymonthday',
            'BYYEARDAY': 'setByyearday',
            'BYMONTH': 'setBymonth',
        }

        settermap = {
            'FREQ': 'set_frequency',
            'INTERVAL': 'set_interval',
            'COUNT': 'set_count',
            'UNTIL': 'set_until',
            'WKST': 'set_weekstart',
            'BYDAY': 'set_byday',
        }

        for prop,setter in vectorimap.items():
            if vrecur.has_key(prop):
                getattr(self, setter)([int(v) for v in vrecur[prop]])

        for prop,setter in settermap.items():
            if vrecur.has_key(prop):
                getattr(self, setter)(vrecur[prop])

    def set_count(self, count):
        if isinstance(count, list):
            count = count[0]
        self.setCount(int(count))

    def set_interval(self, val):
        if isinstance(val, list):
            val = val[0]
        self.setInterval(int(val))

    def set_frequency(self, freq):
        self._set_map_value(freq, self.frequency_map, 'setFrequency')

    def get_frequency(self, translated=False):
        freq = self.frequency()
        if translated:
            return self._translate_value(freq, self.frequency_map)
        return freq

    def set_byday(self, bdays):
        daypos = kolabformat.vectordaypos()
        for wday in bdays:
            if isinstance(wday, str):
                wday = icalendar.vWeekday(wday)

            weekday = str(wday)[-2:]
            occurrence = int(wday.relative)
            if str(wday)[0] == '-':
                occurrence = occurrence * -1
            if self.weekday_map.has_key(weekday):
                daypos.append(kolabformat.DayPos(occurrence, self.weekday_map[weekday]))
        self.setByday(daypos)

    def set_weekstart(self, wkst):
        self._set_map_value(wkst, self.weekday_map, 'setWeekStart')

    def get_weekstart(self, translated=False):
        wkst = self.weekStart()
        if translated:
            return self._translate_value(wkst, self.weekday_map)
        return wkst

    def set_until(self, until):
        if isinstance(until, list):
            until = until[0]
        if isinstance(until, datetime.datetime) or isinstance(until, datetime.date):
            # move into UTC timezone according to RFC 5545
            if isinstance(until, datetime.datetime):
                until = until.astimezone(pytz.utc)
            self.setEnd(xmlutils.to_cdatetime(until, True))

    def _set_map_value(self, val, pmap, setter):
        if isinstance(val, list):
            val = val[0]
        if val in pmap:
            getattr(self, setter)(pmap[val])
        elif val in pmap.values():
            getattr(self, setter)(val)

    def _translate_value(self, val, map):
        name_map = dict([(v, k) for (k, v) in map.iteritems()])
        return name_map[val] if name_map.has_key(val) else 'UNKNOWN'

    def to_ical(self):
        rrule = icalendar.vRecur(dict((k,v) for k,v in self.to_dict(True).items() if not (type(v) == str and v == '' or type(v) == list and len(v) == 0)))
        return rrule

    def to_dict(self, raw=False):
        if not self.isValid() or self.frequency() == kolabformat.RecurrenceRule.FreqNone:
            return None

        data = dict()

        for p, getter in self.properties_map.iteritems():
            val = None
            args = {}
            if hasattr(self, getter):
                if getter.startswith('get_'):
                    args = dict(translated=True)
            if hasattr(self, getter):
                val = getattr(self, getter)(**args)
            if isinstance(val, kolabformat.cDateTime):
                val = xmlutils.from_cdatetime(val, True)
            elif isinstance(val, kolabformat.vectori):
                val = [int(x) for x in val]
            elif isinstance(val, kolabformat.vectordaypos):
                val = ["%s%s" % (str(x.occurence()) if x.occurence() != 0 else '', self._translate_value(x.weekday(), self.weekday_map)) for x in val]

            if not raw and isinstance(val, list):
                val = ",".join(val)
            if val is not None:
                data[p] = val

        return data


