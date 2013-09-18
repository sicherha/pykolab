# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 or, at your option, any later version
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
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
    def __init__(self, uniqueid, result_attr, last_change):
        self.uniqueid = uniqueid
        self.result_attribute = result_attr

        modifytimestamp_format = conf.get('ldap', 'modifytimestamp_format')
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
    result_attribute = conf.get('cyrus-sasl', 'result_attribute')

    db = init_db(domain)
    _entry = db.query(Entry).filter_by(uniqueid=entry['id']).first()

    if not _entry == None:
        db.delete(_entry)
        db.commit()

def get_entry(domain, entry, update=True):
    result_attribute = conf.get('cyrus-sasl', 'result_attribute')

    db = init_db(domain)
    _entry = db.query(Entry).filter_by(uniqueid=entry['id']).first()

    if not update:
        return _entry

    if _entry == None:
        log.debug(_("Inserting cache entry %r") % (entry['id']), level=8)

        if not entry.has_key(result_attribute):
            entry[result_attribute] = ''

        db.add(
                Entry(
                        entry['id'],
                        entry[result_attribute],
                        entry['modifytimestamp']
                    )
            )

        db.commit()
        _entry = db.query(Entry).filter_by(uniqueid=entry['id']).first()
    else:
        modifytimestamp_format = conf.get('ldap', 'modifytimestamp_format')
        if modifytimestamp_format == None:
            modifytimestamp_format = "%Y%m%d%H%M%SZ"

        if not _entry.last_change.strftime(modifytimestamp_format) == entry['modifytimestamp']:
            log.debug(_("Updating timestamp for cache entry %r") % (entry['id']), level=8)
            last_change = datetime.datetime.strptime(entry['modifytimestamp'], modifytimestamp_format)
            _entry.last_change = last_change
            db.commit()
            _entry = db.query(Entry).filter_by(uniqueid=entry['id']).first()

        if not _entry.result_attribute == entry[result_attribute]:
            log.debug(_("Updating result_attribute for cache entry %r") % (entry['id']), level=8)
            _entry.result_attribute = entry[result_attribute]
            db.commit()
            _entry = db.query(Entry).filter_by(uniqueid=entry['id']).first()

    return _entry

def init_db(domain):
    """
        Returns a SQLAlchemy Session() instance.
    """
    global db

    if not db == None:
        return db

    db_uri = 'sqlite:///%s/%s.db' % (KOLAB_LIB_PATH, domain)
    echo = conf.debuglevel > 8
    engine = create_engine(db_uri, echo=echo)

    metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    return db

def last_modify_timestamp(domain):
    db = init_db(domain)
    last_change = db.query(Entry).order_by(desc(Entry.last_change)).first()

    modifytimestamp_format = conf.get('ldap', 'modifytimestamp_format')
    if modifytimestamp_format == None:
        modifytimestamp_format = "%Y%m%d%H%M%SZ"

    if not last_change == None:
        return last_change.last_change.strftime(modifytimestamp_format)

    return datetime.datetime(1900, 01, 01, 00, 00, 00).strftime(modifytimestamp_format)
