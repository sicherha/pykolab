import datetime
import pytz
import kolabformat
from dateutil.tz import tzlocal

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


def to_cdatetime(_datetime, with_timezone=True):
    """
        Convert a datetime.dateime object into a kolabformat.cDateTime instance
    """
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
        _cdatetime.setTimezone(_datetime.tzinfo.__str__())

    return _cdatetime
