# coding: utf8

import unittest

import datetime
import os

from pykolab.auth.ldap import auth_cache
import pykolab
conf = pykolab.getConf()
conf.finalize_conf()

import sqlalchemy

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text

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

metadata = MetaData()

##
## Classes
##

DeclarativeBase = declarative_base()

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

engine = create_engine('sqlite:////tmp/%s.db' % (os.getpid()), echo=False, echo_pool=False)
DeclarativeBase.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
db = Session()

auth_cache.db = db

class TestAuthCache(unittest.TestCase):
    def test_001_plain_insert(self):
        auth_cache.set_entry(
                'somekey',
                'ou=People,dc=example,dc=org'
            )

        result = auth_cache.get_entry('somekey')
        self.assertEqual(result, 'ou=People,dc=example,dc=org')

    def test_002_plain_encoding_insert(self):
        auth_cache.set_entry(
                'somekey2',
                'ou=Geschäftsbereich,ou=People,dc=example,dc=org'
            )

        result = auth_cache.get_entry('somekey2')
        self.assertEqual(result, 'ou=Gesch\xc3\xa4ftsbereich,ou=People,dc=example,dc=org')

    def test_003_unicode_insert(self):
        auth_cache.set_entry(
                'somekey3',
                u'ou=Geschäftsbereich,ou=People,dc=example,dc=org'
            )

        result = auth_cache.get_entry('somekey3')
        self.assertEqual(result, 'ou=Gesch\xc3\xa4ftsbereich,ou=People,dc=example,dc=org')

    @unittest.skip("Double encoding or decoding")
    def test_004_unicode_escape(self):
        auth_cache.set_entry(
                'somekey4',
                u'ou=Gesch\xc3\xa4ftsbereich,ou=People,dc=example,dc=org'
            )

        result = auth_cache.get_entry('somekey4')
        self.assertEqual(result, u'ou=Gesch\xc3\xa4ftsbereich,ou=People,dc=example,dc=org')

    def test_005_longkey(self):
        auth_cache.set_entry(
                'v' + 'e'*512 + 'rylongkey',
                'v' + 'e'*512 + 'rylongvalue'
            )

        result = auth_cache.get_entry('v' + 'e'*512 + 'rylongkey')
        self.assertEqual(result, 'v' + 'e'*512 + 'rylongvalue')
