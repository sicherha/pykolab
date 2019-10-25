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

from uuid import UUID

import sqlalchemy

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String

from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import sessionmaker

import pykolab

from pykolab.constants import KOLAB_LIB_PATH
from pykolab.translate import _

# pylint: disable=invalid-name
conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.cache')

metadata = MetaData()

db = {}

#
# Classes
#

DeclarativeBase = declarative_base()


# pylint: disable=too-few-public-methods
class Entry(DeclarativeBase):
    __tablename__ = 'entries'

    last_change = None

    id = Column(Integer, primary_key=True)
    uniqueid = Column(String(128), nullable=False)
    result_attribute = Column(String(128), nullable=False)
    last_change = Column(DateTime, nullable=False, default=datetime.datetime.now())

    def __init__(self, uniqueid, result_attr, last_change):
        self.uniqueid = uniqueid
        self.result_attribute = result_attr

        modifytimestamp_format = conf.get_raw(
            'ldap',
            'modifytimestamp_format',
            default="%Y%m%d%H%M%SZ"
        ).replace('%%', '%')

        self.last_change = datetime.datetime.strptime(
            last_change,
            modifytimestamp_format
        )


#
# Functions
#


def delete_entry(domain, entry):
    _db = init_db(domain)
    _entry = _db.query(Entry).filter_by(uniqueid=entry['id']).first()

    if _entry is not None:
        _db.delete(_entry)
        _db.commit()


def get_entry(domain, entry, update=True):
    result_attribute = conf.get_raw('cyrus-sasl', 'result_attribute')

    _entry = None

    _db = init_db(domain)

    try:
        _uniqueid = str(UUID(bytes_le=entry['id']))
        log.debug(
            _("Entry uniqueid was converted from binary form to string: %s") % _uniqueid,
            level=8
        )

    except ValueError:
        _uniqueid = entry['id']

    try:
        _entry = _db.query(Entry).filter_by(uniqueid=_uniqueid).first()
    except sqlalchemy.exc.OperationalError:
        _db = init_db(domain, reinit=True)
    except sqlalchemy.exc.InvalidRequestError:
        _db = init_db(domain, reinit=True)
    finally:
        _entry = _db.query(Entry).filter_by(uniqueid=_uniqueid).first()

    if not update:
        return _entry

    if _entry is None:
        log.debug(_("Inserting cache entry %r") % (_uniqueid), level=8)

        if result_attribute not in entry:
            entry[result_attribute] = ''

        _db.add(Entry(_uniqueid, entry[result_attribute], entry['modifytimestamp']))

        _db.commit()
        _entry = _db.query(Entry).filter_by(uniqueid=_uniqueid).first()
    else:
        modifytimestamp_format = conf.get_raw(
            'ldap',
            'modifytimestamp_format',
            default="%Y%m%d%H%M%SZ"
        ).replace('%%', '%')

        if not _entry.last_change.strftime(modifytimestamp_format) == entry['modifytimestamp']:
            log.debug(_("Updating timestamp for cache entry %r") % (_uniqueid), level=8)
            last_change = datetime.datetime.strptime(
                entry['modifytimestamp'],
                modifytimestamp_format
            )

            _entry.last_change = last_change
            _db.commit()
            _entry = _db.query(Entry).filter_by(uniqueid=_uniqueid).first()

        if result_attribute in entry:
            if not _entry.result_attribute == entry[result_attribute]:
                log.debug(_("Updating result_attribute for cache entry %r") % (_uniqueid), level=8)
                _entry.result_attribute = entry[result_attribute]
                _db.commit()
                _entry = _db.query(Entry).filter_by(uniqueid=_uniqueid).first()

    return _entry


def init_db(domain, reinit=False):
    """
        Returns a SQLAlchemy Session() instance.
    """
    # pylint: disable=global-statement
    global db

    if domain in db and not reinit:
        return db[domain]

    if reinit:
        import os
        if os.path.isfile('sqlite:///%s/%s.db' % (KOLAB_LIB_PATH, domain)):
            os.unlink('sqlite:///%s/%s.db' % (KOLAB_LIB_PATH, domain))

    db_uri = 'sqlite:///%s/%s.db' % (KOLAB_LIB_PATH, domain)
    echo = conf.debuglevel > 8

    try:
        engine = create_engine(db_uri, echo=echo)
        DeclarativeBase.metadata.create_all(engine)
    except Exception:
        engine = create_engine('sqlite://')
        DeclarativeBase.metadata.create_all(engine)
        metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db[domain] = Session()

    return db[domain]


def last_modify_timestamp(domain):
    modifytimestamp_format = conf.get_raw(
        'ldap',
        'modifytimestamp_format',
        "%Y%m%d%H%M%SZ"
    ).replace('%%', '%')

    try:
        _db = init_db(domain)
        last_change = _db.query(Entry).order_by(desc(Entry.last_change)).first()

        if last_change is not None:
            return last_change.last_change.strftime(modifytimestamp_format)

        return datetime.datetime(1900, 1, 1, 00, 00, 00).strftime(modifytimestamp_format)

    except Exception:
        return datetime.datetime(1900, 1, 1, 00, 00, 00).strftime(modifytimestamp_format)
