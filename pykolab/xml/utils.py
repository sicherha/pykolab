import datetime
import pytz
import kolabformat
from dateutil.tz import tzlocal
from collections import OrderedDict


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
                if not aai == bbi:
                    if reduced:
                        (old, new) = reduce_properties(aai, bbi)
                    else:
                        (old, new) = (aai, bbi)
                    diff.append(OrderedDict([('property', prop), ('index', index), ('old', old), ('new', new)]))
                index += 1

        # the two properties differ
        elif not aa.__class__ == bb.__class__ or not aa == bb:
            if reduced:
                (old, new) = reduce_properties(aa, bb)
            else:
                (old, new) = (aa, bb)
            diff.append(OrderedDict([('property', prop), ('old', old), ('new', new)]))

    return diff


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
