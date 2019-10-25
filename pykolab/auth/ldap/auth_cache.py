# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import datetime

import sqlalchemy

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import sessionmaker

import pykolab

from pykolab.constants import KOLAB_LIB_PATH

# pylint: disable=invalid-name
conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.auth_cache')

metadata = MetaData()

db = None

try:
    unicode('')
except NameError:
    unicode = str

#
# Classes
#

DeclarativeBase = declarative_base()


# pylint: disable=too-few-public-methods
class Entry(DeclarativeBase):
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True)
    domain = Column(String(256), index=True, nullable=True)
    key = Column(Text, index=True, nullable=False)
    value = Column(Text, nullable=False)
    last_change = Column(DateTime, nullable=False, default=datetime.datetime.now())

    def __init__(self, key, value):
        self.key = key
        if not isinstance(value, unicode):
            self.value = unicode(value, 'utf-8')
        else:
            self.value = value

#
# Functions
#


def del_entry(key):
    # pylint: disable=global-statement
    global db

    db = init_db()

    try:
        db.query(Entry).filter_by(key=key).delete()
    except sqlalchemy.exc.OperationalError:
        db = init_db(reinit=True)
    except sqlalchemy.exc.InvalidRequest:
        db = init_db(reinit=True)
    finally:
        db.query(Entry).filter_by(key=key).delete()

    db.commit()


def get_entry(key):
    # pylint: disable=global-statement
    global db

    db = init_db()

    try:
        _entries = db.query(Entry).filter_by(key=key).all()
    except sqlalchemy.exc.OperationalError:
        db = init_db(reinit=True)
    except sqlalchemy.exc.InvalidRequest:
        db = init_db(reinit=True)
    finally:
        _entries = db.query(Entry).filter_by(key=key).all()

    if _entries:
        return None

    if len(_entries) > 1:
        return None

    log.debug("Entry found: %r" % (_entries[0].__dict__))
    log.debug("Returning: %r" % (_entries[0].value))

    return _entries[0].value.encode('utf-8', 'latin1')


def set_entry(key, value):
    db = init_db()

    try:
        _entries = db.query(Entry).filter_by(key=key).all()
    except sqlalchemy.exc.OperationalError:
        db = init_db(reinit=True)
    except sqlalchemy.exc.InvalidRequest:
        db = init_db(reinit=True)
    finally:
        _entries = db.query(Entry).filter_by(key=key).all()

    if not _entries:
        db.add(Entry(key, value))
        db.commit()

    elif len(_entries) == 1:
        if not isinstance(value, unicode):
            value = unicode(value, 'utf-8')

        if not _entries[0].value == value:
            _entries[0].value = value

        _entries[0].last_change = datetime.datetime.now()
        db.commit()


def purge_entries(db):
    db.query(Entry).filter(
        Entry.last_change <= (datetime.datetime.now() - datetime.timedelta(1))
    ).delete()

    db.commit()


def init_db(reinit=False):
    """
        Returns a SQLAlchemy Session() instance.
    """
    # pylint: disable=global-statement
    global db

    if db is not None and not reinit:
        return db

    db_uri = conf.get('ldap', 'auth_cache_uri')

    if db_uri is None:
        db_uri = 'sqlite:///%s/auth_cache.db' % (KOLAB_LIB_PATH)

        if reinit:
            import os
            if os.path.isfile('%s/auth_cache.db' % (KOLAB_LIB_PATH)):
                os.unlink('%s/auth_cache.db' % (KOLAB_LIB_PATH))

    echo = conf.debuglevel > 8
    engine = create_engine(db_uri, echo=echo)
    DeclarativeBase.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db = Session()
    purge_entries(db)

    return db
