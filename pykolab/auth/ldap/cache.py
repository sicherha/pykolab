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

from uuid import UUID

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

db = {}

##
## Classes
##

class Entry(object):
    def __init__(self, uniqueid, result_attr, last_change):
        self.uniqueid = uniqueid
        self.result_attribute = result_attr

        modifytimestamp_format = conf.get_raw('ldap', 'modifytimestamp_format').replace('%%', '%')
        if modifytimestamp_format == None:
            modifytimestamp_format = "%Y%m%d%H%M%SZ"

        self.last_change = datetime.datetime.strptime(
                last_change,
                modifytimestamp_format
            )

##
## Tables
##

entry_table = Table(
        'entry', metadata,
        Column('id', Integer, primary_key=True),
        Column('uniqueid', String(128), nullable=False),
        Column('result_attribute', String(128), nullable=False),
        Column('last_change', DateTime),
    )

##
## Table <-> Class Mappers
##

mapper(Entry, entry_table)

##
## Functions
##

def delete_entry(domain, entry):
    result_attribute = conf.get_raw('cyrus-sasl', 'result_attribute')

    db = init_db(domain)
    _entry = db.query(Entry).filter_by(uniqueid=entry['id']).first()

    if not _entry == None:
        db.delete(_entry)
        db.commit()

def get_entry(domain, entry, update=True):
    result_attribute = conf.get_raw('cyrus-sasl', 'result_attribute')

    _entry = None

    db = init_db(domain)

    try:
        _uniqueid = str(UUID(bytes_le=entry['id']))
        log.debug(_("Entry uniqueid was converted from binary form to string: %s") % _uniqueid, level=8)
    except ValueError:
        _uniqueid = entry['id']

    try:
        _entry = db.query(Entry).filter_by(uniqueid=_uniqueid).first()
    except sqlalchemy.exc.OperationalError, errmsg:
        db = init_db(domain,reinit=True)
    except sqlalchemy.exc.InvalidRequestError, errmsg:
        db = init_db(domain,reinit=True)
    finally:
        _entry = db.query(Entry).filter_by(uniqueid=_uniqueid).first()

    if not update:
        return _entry

    if _entry == None:
        log.debug(_("Inserting cache entry %r") % (_uniqueid), level=8)

        if not entry.has_key(result_attribute):
            entry[result_attribute] = ''

        db.add(
                Entry(
                        _uniqueid,
                        entry[result_attribute],
                        entry['modifytimestamp']
                    )
            )

        db.commit()
        _entry = db.query(Entry).filter_by(uniqueid=_uniqueid).first()
    else:
        modifytimestamp_format = conf.get_raw('ldap', 'modifytimestamp_format').replace('%%', '%')
        if modifytimestamp_format == None:
            modifytimestamp_format = "%Y%m%d%H%M%SZ"

        if not _entry.last_change.strftime(modifytimestamp_format) == entry['modifytimestamp']:
            log.debug(_("Updating timestamp for cache entry %r") % (_uniqueid), level=8)
            last_change = datetime.datetime.strptime(entry['modifytimestamp'], modifytimestamp_format)
            _entry.last_change = last_change
            db.commit()
            _entry = db.query(Entry).filter_by(uniqueid=_uniqueid).first()

        if entry.has_key(result_attribute):
            if not _entry.result_attribute == entry[result_attribute]:
                log.debug(_("Updating result_attribute for cache entry %r") % (_uniqueid), level=8)
                _entry.result_attribute = entry[result_attribute]
                db.commit()
                _entry = db.query(Entry).filter_by(uniqueid=_uniqueid).first()

    return _entry

def init_db(domain,reinit=False):
    """
        Returns a SQLAlchemy Session() instance.
    """
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
        metadata.create_all(engine)
    except:
        engine = create_engine('sqlite://')
        metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db[domain] = Session()

    return db[domain]

def last_modify_timestamp(domain):
    modifytimestamp_format = conf.get_raw('ldap', 'modifytimestamp_format').replace('%%', '%')
    if modifytimestamp_format == None:
        modifytimestamp_format = "%Y%m%d%H%M%SZ"

    try:
        db = init_db(domain)
        last_change = db.query(Entry).order_by(desc(Entry.last_change)).first()

        if not last_change == None:
            return last_change.last_change.strftime(modifytimestamp_format)
        else:
            return datetime.datetime(1900, 01, 01, 00, 00, 00).strftime(modifytimestamp_format)
    except:
        return datetime.datetime(1900, 01, 01, 00, 00, 00).strftime(modifytimestamp_format)
