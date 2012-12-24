
from email import message_from_string

import time
import unittest

import pykolab
from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP

conf = pykolab.getConf()

class TestUserAdd(unittest.TestCase):

    @classmethod
    def setup_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

        self.john = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

        self.jane = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        user_add("Jane", "Doe")
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    @classmethod
    def teardown_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

    def test_001_inbox_created(self):
        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/%(local)s@%(domain)s' % (self.john))
        self.assertEqual(len(folders), 1)
        
        folders = imap.lm('user/%(local)s@%(domain)s' % (self.jane))
        self.assertEqual(len(folders), 1)

    def test_002_send_forwarded_email(self):
        import smtplib
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase
        from email.MIMEText import MIMEText
        from email.Utils import COMMASPACE, formatdate
        from email import Encoders

        smtp = smtplib.SMTP('localhost', 10026)
        subject = "%s" % (time.time())
        body = "This is a test message"
        msg = MIMEMultipart()
        msg['From'] = '"Doe, Jane" <jane.doe@example.org>'
        msg['To'] = '"Doe, John" <john.doe@example.org>'
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        msg.attach(MIMEText(body))

        send_to = 'jane.doe@example.org'
        send_from = 'john.doe@example.org'

        smtp.sendmail(send_from, send_to, msg.as_string())

        imap = IMAP()
        imap.connect()
        imap.set_acl("user/jane.doe@example.org", "cyrus-admin", "lrs")
        imap.imap.m.select("user/jane.doe@example.org")

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

        if not found:
            raise Exception
