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
from sqlalchemy import Table

from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.orm import mapper

try:
    from sqlalchemy.orm import relationship
except:
    from sqlalchemy.orm import relation as relationship

try:
    from sqlalchemy.orm import sessionmaker
except:
    from sqlalchemy.orm import create_session

import pykolab

from pykolab import utils
from pykolab.constants import KOLAB_LIB_PATH
from pykolab.translate import _

conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.auth_cache')

metadata = MetaData()

db = None

##
## Classes
##

class Entry(object):
    def __init__(self, key, value):
        self.key = key
        self.value = value

##
## Tables
##

entry_table = Table(
        'entries', metadata,
        Column('id', Integer, primary_key=True),
        Column('domain', String(128), index=True, nullable=True),
        Column('key', String(512), index=True, nullable=False),
        Column('value', String(128), nullable=False),
        Column('last_change', DateTime, nullable=False, default=datetime.datetime.now())
    )

##
## Table <-> Class Mappers
##

mapper(Entry, entry_table)

##
## Functions
##

def del_entry(key):
    db = init_db()

    try:
        _entries = db.query(Entry).filter_by(key=key).delete()
    except sqlalchemy.exc.OperationalError, errmsg:
        db = init_db(reinit=True)
    except sqlalchemy.exc.InvalidRequest, errmsg:
        db = init_db(reinit=True)
    finally:
        _entries = db.query(Entry).filter_by(key=key).delete()

    db.commit()

def get_entry(key):
    db = init_db()

    try:
        _entries = db.query(Entry).filter_by(key=key).all()
    except sqlalchemy.exc.OperationalError, errmsg:
        db = init_db(reinit=True)
    except sqlalchemy.exc.InvalidRequest, errmsg:
        db = init_db(reinit=True)
    finally:
        _entries = db.query(Entry).filter_by(key=key).all()

    if len(_entries) == 0:
        return None
    if len(_entries) > 1:
        return None

    log.debug("Entry found: %r" % (_entries[0].__dict__))
    log.debug("Returning: %r" % (_entries[0].value))

    return _entries[0].value

def set_entry(key, value):
    db = init_db()
    try:
        _entries = db.query(Entry).filter_by(key=key).all()
    except sqlalchemy.exc.OperationalError, errmsg:
        db = init_db(reinit=True)
    except sqlalchemy.exc.InvalidRequest, errmsg:
        db = init_db(reinit=True)
    finally:
        _entries = db.query(Entry).filter_by(key=key).all()

    if len(_entries) == 0:
        db.add(
                Entry(
                        key,
                        value
                    )
            )

        db.commit()
    elif len(_entries) == 1:
        if not _entries[0].value == value:
            _entries[0].value = value

        _entries[0].last_change = datetime.datetime.now()
        db.commit()

def purge_entries(db):
    db.query(Entry).filter(Entry.last_change <= (datetime.datetime.now() - datetime.timedelta(1))).delete()
    db.commit()

def init_db(reinit=False):
    """
        Returns a SQLAlchemy Session() instance.
    """
    global db

    if not db == None and not reinit:
        return db

    db_uri = conf.get('ldap', 'auth_cache_uri')
    if db_uri == None:
        db_uri = 'sqlite:///%s/auth_cache.db' % (KOLAB_LIB_PATH)

        if reinit:
            import os
            if os.path.isfile('%s/auth_cache.db' % (KOLAB_LIB_PATH)):
                os.unlink('%s/auth_cache.db' % (KOLAB_LIB_PATH))

    echo = conf.debuglevel > 8
    engine = create_engine(db_uri, echo=echo)
    metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db = Session()
    purge_entries(db)

    return db
