# *-* encoding: utf-8 *-*
from email.header import Header
from email import message_from_string
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEImage import MIMEImage
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
import os
import smtplib
import time
import unittest

import pykolab
from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP

conf = pykolab.getConf()

class TestWallaceNonASCIIAddresses(unittest.TestCase):

    @classmethod
    def setup_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

        self.user = {
                'local': 'nikolaj.rimskij-korsakov',
                'domain': 'example.org'
            }

        self.send_to = 'nikolaj.rimskij-korsakov@example.org'
        self.send_from = 'nikolaj.rimskij-korsakov@example.org'

        self.message_to = '"Римский-Корсаков, Николай" <%s>' % (self.send_to)
        self.message_from = '"Римский-Корсаков, Николай" <%s>' % (self.send_from)

        from tests.functional.user_add import user_add
        user_add("Николай", "Римский-Корсаков", preferredlanguage='ru_RU')
        time.sleep(2)
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

#    @classmethod
#    def teardown_class(self, *args, **kw):
#        from tests.functional.purge_users import purge_users
#        purge_users()

    def check_message_delivered(self, subject):
        imap = IMAP()
        imap.connect()
        imap.set_acl("user/nikolaj.rimskij-korsakov@example.org", "cyrus-admin", "lrs")
        imap.imap.m.select("user/nikolaj.rimskij-korsakov@example.org")

        found = False
        max_tries = 20

        while not found and max_tries > 0:
            max_tries -= 1

            typ, data = imap.imap.m.search(None, 'ALL')
            for num in data[0].split():
                typ, msg = imap.imap.m.fetch(num, '(RFC822)')
                _msg = message_from_string(msg[0][1])
                if _msg['Subject'] == subject:
                    found = True

            time.sleep(1)

        return found

    def message_standard_params(self, subject, msg):
        msg['From'] = Header(self.message_from)
        msg['To'] = Header(self.message_to)

        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)

        return msg

    def send_message(self, msg, _to=None, _from=None):
        smtp = smtplib.SMTP('localhost', 10026)

        if _to == None:
            _to = self.send_to

        if _from == None:
            _from = self.send_from

        smtp.sendmail(_from, _to, msg.as_string())

    def test_001_inbox_created(self):
        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/%(local)s@%(domain)s' % (self.user))
        self.assertEqual(len(folders), 1)
        
    def test_002_send_nonascii_addresses(self):
        subject = Header(u"test_002_nonascii_addresses")
        body = "This is a test message"
        msg = MIMEBase("text", "plain")
        msg = self.message_standard_params(subject, msg)

        msg.set_payload(body)

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_003_send_nonascii_subject(self):
        subject = Header(u"test_003_nonascii_subject Тест")
        body = "This is a test message"
        msg = MIMEBase("text", "plain")
        msg = self.message_standard_params(subject, msg)

        msg.set_payload(body)

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

