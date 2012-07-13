import datetime
import pytz

def to_dt(dt):
    """
        Convert a naive date or datetime to a tz-aware datetime.
    """

    if type(dt) == 'datetime.date' or not hasattr(dt, 'hour'):
        dt = datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0, 0)

    else:
        if dt.tzinfo == None:
            return dt.replace(tzinfo=pytz.utc)
        else:

            return dt


