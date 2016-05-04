import time
import datetime
import pykolab
import pytz
import uuid
import string
import random

from pykolab.xml import Event
from pykolab.xml import Attendee
from pykolab.imap import IMAP

from wallace import module_resources
from twisted.trial import unittest

from tests.functional import resource_func as funcs
from tests.functional.synchronize import synchronize_once

conf = pykolab.getConf()


class TestWallacePerformance(unittest.TestCase):

    rooms = None

    @classmethod
    def setUp(self):
        """ Compatibility for twisted.trial.unittest
        """
        if not self.rooms:
            self.setup_class()

    @classmethod
    def setup_class(self, *args, **kw):
        funcs.purge_resources()
        self.room1 = funcs.resource_add("confroom", "Room 101")
        self.room2 = funcs.resource_add("confroom", "Conference Room B-222")
        self.rooms = funcs.resource_add("collection", "Rooms", [self.room1['dn'], self.room2['dn']])

        time.sleep(1)
        synchronize_once()

        module_resources.imap = IMAP()
        module_resources.imap.connect()

    def purge_mailbox(self, mailbox):
        imap = IMAP()
        imap.connect()
        imap.set_acl(mailbox, "cyrus-admin", "lrwcdest")
        imap.imap.m.select(imap.folder_quote(mailbox))

        typ, data = imap.imap.m.search(None, 'ALL')
        for num in data[0].split():
            imap.imap.m.store(num, '+FLAGS', '\\Deleted')

        imap.imap.m.expunge()
        imap.disconnect()

    def populate_calendar(self, resource, num=10, date=None):
        if date is None:
            date = datetime.datetime.now(pytz.timezone("Europe/London"))

        i = 0
        while i < num:
            offset = random.randint(-3200, 3200) * 10
            duration = random.randint(3, 72) * 10
            summary = ''.join(random.sample((string.ascii_uppercase + string.digits) * 12, random.randint(6, 18)))
            start = date + datetime.timedelta(minutes=offset)

            event = Event()
            event.set_summary(summary)
            event.set_start(start)
            event.set_end(start + datetime.timedelta(minutes=duration))
            saved = module_resources.save_resource_event(dict(xml=event), resource)
            i += 1

    def test_001_save_resource_event(self):
        event = Event()
        event.set_summary("test")

        date = datetime.datetime.now(pytz.timezone("Europe/London"))
        event.set_start(date)
        event.set_end(date + datetime.timedelta(hours=2))

        saved = module_resources.save_resource_event(dict(xml=event), self.room1)
        self.assertTrue(saved)

    def test_002_read_resource_calendar(self):
        self.purge_mailbox(self.room1['kolabtargetfolder'])

        event = Event()
        event.set_summary("test")
        event.set_start(datetime.datetime(2014, 4, 1, 12, 0, 0, tzinfo=pytz.timezone("Europe/London")))
        event.set_end(datetime.datetime(2014, 4, 1, 14, 0, 0, tzinfo=pytz.timezone("Europe/London")))
        saved = module_resources.save_resource_event(dict(xml=event), self.room1)
        self.assertTrue(saved)
        uid = event.get_uid()

        itip = dict(
            uid=str(uuid.uuid4()),
            sequence=0,
            start=datetime.datetime(2014, 4, 1, 13, 0, 0, tzinfo=pytz.timezone("Europe/London")),
            end=datetime.datetime(2014, 4, 1, 14, 30, 0, tzinfo=pytz.timezone("Europe/London"))
        )

        event.set_uid(itip['uid'])
        event.set_start(itip['start'])
        event.set_end(itip['end'])
        itip['xml'] = event

        res = module_resources.read_resource_calendar(self.room1, [itip])
        self.assertEqual(res, 1)
        self.assertTrue(self.room1['conflict'])
        self.assertIn(uid, self.room1['conflicting_events'])

    def test_003_read_time(self):
        self.purge_mailbox(self.room1['kolabtargetfolder'])

        # populate 5K random events
        num = 5000
        date = datetime.datetime.now(pytz.timezone("Europe/London")).replace(hour=10, minute=0, second=0, microsecond=0)
        self.populate_calendar(self.room1, num, date)

        itip = dict(
            uid=str(uuid.uuid4()),
            sequence=0,
            start=date,
            end=date + datetime.timedelta(minutes=90)
        )

        event = Event()
        event.set_uid(itip['uid'])
        event.set_start(itip['start'])
        event.set_end(itip['end'])
        itip['xml'] = event

        start = time.time()
        res = module_resources.read_resource_calendar(self.room1, [itip])
        self.assertEqual(res, num)

        print "\nREAD TIME:", time.time() - start
        print "CONFLICTS:", self.room1['conflicting_events']
