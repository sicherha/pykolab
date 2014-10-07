import kolabformat
from pykolab.xml import utils as xmlutils

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

    def get_frequency(self, translated=False):
        freq = self.frequency()
        if translated:
            return self._translate_value(freq, self.frequency_map)
        return freq

    def get_weekstart(self, translated=False):
        wkst = self.weekStart()
        if translated:
            return self._translate_value(wkst, self.weekday_map)
        return wkst

    def _translate_value(self, val, map):
        name_map = dict([(v, k) for (k, v) in map.iteritems()])
        return name_map[val] if name_map.has_key(val) else 'UNKNOWN'

    def to_dict(self):
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
                val = ",".join([int(v) for x in val])
            elif isinstance(val, kolabformat.vectordaypos):
                val = ",".join(["%s%s" % (str(x.occurence()) if x.occurence() != 0 else '', self._translate_value(x.weekday(), self.weekday_map)) for x in val])
            if val is not None:
                data[p] = val

        return data


