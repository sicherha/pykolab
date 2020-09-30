# Copyright 2010-2017 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
# Christian Mollekopf <mollekopf@kolabsys.com>
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
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy import MetaData
from sqlalchemy import Table

from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
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
from pykolab.translate import _

# pylint: disable=invalid-name
conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.auth.plesk')

metadata = MetaData()

##
## Classes
##

DeclarativeBase = declarative_base()

class Object(DeclarativeBase):
    __tablename__ = 'objects'

    id = Column(Integer, primary_key=True)
    object_type = Column(String(256), index=True, nullable=False)
    object_name = Column(String(256), index=True, nullable=False)

    params = relationship('ObjectParam')

class ObjectParam(DeclarativeBase):
    __tablename__ = 'object_params'

    id = Column(Integer, primary_key=True)
    object_id = Column(Integer, ForeignKey('objects.id', ondelete="CASCADE"), nullable=False)
    key = Column(String(256), index=True, nullable=False)
    value = Column(Text, nullable=False)

class Plesk(pykolab.base.Base):
    db = None

    def __init__(self, domain=None):
        self.domain = domain

    def connect(self):
        self.__init_db()

    def find_recipient(self, address="*", search_attrs=None):
        """
            Given an address string or list of addresses, find one or more valid
            recipients.
        """

        log.debug(_("Finding recipient with filter %r") % (address), level=8)

        _objects = self.db.query(Object).filter_by(object_name=address).all()
        return map(lambda _object: (str)(_object.id), _objects)

    def get_entry_attribute(self, entry_id, attribute):
        """
            Get an attribute for an entry.

            Return the attribute value if successful, or None if not.
        """

        entry_attrs = self.get_entry_attributes(entry_id, [attribute])

        if attribute in entry_attrs:
            return entry_attrs[attribute]
        elif attribute.lower() in entry_attrs:
            return entry_attrs[attribute.lower()]
        else:
            return None

    def get_entry_attributes(self, entry, attributes):
        print(entry, attributes)
        _object = None
        if isinstance(entry, dict):
            _object = self.db.query(Object).get((int)(entry['dn']))
        else:
            _object = self.db.query(Object).get((int)(entry))

        if _object is None:
            return None

        attrs = {'id': entry}

        attrs['mail'] = _object.object_name

        for param in _object.params:
            if param.key not in attrs:
                attrs[param.key] = []

            attrs[param.key].append(param.value)

        return attrs

    def _disconnect(self):
        self.db.close()

    def _find_user_dn(self, recipient_address, kolabuser=False):
        _object = self.db.query(Object).filter_by(object_name=recipient_address).first()

        if _object is None:
            return None

        return (str)(_object.id)

    def __init_db(self):
        if self.db is not None:
            return

        db_uri = conf.get('plesk', 'sql_uri')

        echo = conf.debuglevel > 8
        engine = create_engine(db_uri, echo=echo)
        Session = sessionmaker(bind=engine)
        self.db = Session()
