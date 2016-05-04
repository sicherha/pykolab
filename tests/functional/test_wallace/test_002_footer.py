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


class TestWallaceFooter(unittest.TestCase):
    user = None

    @classmethod
    def setUp(self):
        """ Compatibility for twisted.trial.unittest
        """
        if not self.user:
            self.setup_class()

    @classmethod
    def setup_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

        self.user = {
                'local': 'john.doe',
                'domain': 'example.org'
            }

        self.footer = {}

        footer_html_file = conf.get('wallace', 'footer_html')
        footer_text_file = conf.get('wallace', 'footer_text')

        if os.path.isfile(footer_text_file):
            self.footer['plain'] = open(footer_text_file, 'r').read()

        if not os.path.isfile(footer_html_file):
            self.footer['html'] = '<p>' + self.footer['plain'] + '</p>'
        else:
            self.footer['html'] = open(footer_html_file, 'r').read()

        self.send_to = 'john.doe@example.org'
        self.send_from = 'john.doe@example.org'

        self.message_to = '"Doe, John" <%s>' % (self.send_to)
        self.message_from = '"Doe, John" <%s>' % (self.send_from)

        from tests.functional.user_add import user_add
        user_add("John", "Doe")
        time.sleep(2)
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    @classmethod
    def teardown_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

    def check_message_delivered(self, subject):
        imap = IMAP()
        imap.connect()
        imap.set_acl("user/john.doe@example.org", "cyrus-admin", "lrs")
        imap.imap.m.select("user/john.doe@example.org")

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

    def html_attachment(self):
        html_body = "<html><body><p>This is an HTML attachment</p></body></html>"
        html_part = MIMEBase("text", "html")
        html_part.add_header("Content-Disposition", "attachment", filename="html_attachment.html")
        html_part.set_payload(html_body)
        return html_part

    def image_attachment(self):
        image_file = '/usr/share/kolab-webadmin/public_html/skins/default/images/logo_kolab.png'
        image_part = MIMEImage(open(image_file, 'r').read())
        image_part.add_header("Content-Disposition", "attachment", filename=os.path.basename(image_file))
        return image_part

    def message_standard_params(self, subject, msg):
        msg['From'] = self.message_from
        msg['To'] = self.message_to

        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)

        return msg

    def send_message(self, msg, _to=None, _from=None):
        smtp = smtplib.SMTP('localhost', 10026)

        if _to is None:
            _to = self.send_to

        if _from is None:
            _from = self.send_from

        smtp.sendmail(_from, _to, msg.as_string())

    def test_001_inbox_created(self):
        imap = IMAP()
        imap.connect()

        folders = imap.lm('user/%(local)s@%(domain)s' % (self.user))
        self.assertEqual(len(folders), 1)

    def test_002_send_plaintext(self):
        subject = "test_002_send_plaintext"
        body = "This is a test message"
        msg = MIMEBase("text", "plain")
        msg = self.message_standard_params(subject, msg)

        msg.set_payload(body)

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_003_send_plaintext_with_attachment(self):
        subject = "test_003_send_plaintext_with_attachment"
        body = "This is a test message"
        msg = MIMEMultipart()
        msg = self.message_standard_params(subject, msg)

        msg.attach(MIMEText(body))
        msg.attach(self.image_attachment())

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_004_send_html(self):
        subject = "test_004_send_html"
        body = "<html><body><p>This is a test message</p></body></html>"
        msg = MIMEBase("text", "html")
        msg = self.message_standard_params(subject, msg)
        msg.set_payload(body)

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_005_send_html_with_plaintext_alternative(self):
        subject = "test_005_send_html_with_plaintext_alternative"
        html_body = "<html><body><p>This is the HTML part</p></body></html>"
        plain_body = "This is the plaintext part"

        msg = MIMEMultipart("alternative")
        msg = self.message_standard_params(subject, msg)

        html_part = MIMEBase("text", "html")
        html_part.set_payload(html_body)
        msg.attach(html_part)

        plain_part = MIMEText(plain_body)
        msg.attach(plain_part)

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_006_send_html_with_attachment(self):
        subject = "test_006_send_html_with_attachment"
        html_body = "<html><body><p>This is the HTML part</p></body></html>"
        plain_body = "This is the plaintext part"

        msg = MIMEMultipart()
        msg = self.message_standard_params(subject, msg)

        html_part = MIMEBase("text", "html")
        html_part.set_payload(html_body)
        msg.attach(html_part)

        msg.attach(self.image_attachment())

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_007_send_html_with_plaintext_alternative_and_attachment(self):
        subject = "test_007_send_html_with_plaintext_alternative_and_attachment"
        html_body = "<html><body><p>This is the HTML part</p></body></html>"
        plain_body = "This is the plaintext part"

        msg = MIMEMultipart("mixed")
        msg = self.message_standard_params(subject, msg)

        message_part = MIMEMultipart("alternative")

        html_part = MIMEBase("text", "html")
        html_part.set_payload(html_body)
        message_part.attach(html_part)

        plain_part = MIMEText(plain_body)
        message_part.attach(plain_part)

        msg.attach(message_part)

        msg.attach(self.image_attachment())

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_008_send_plaintext_with_html_attachment(self):
        subject = "test_008_send_plaintext_with_html_attachment"
        body = "This is a plaintext message"
        msg = MIMEMultipart()
        msg = self.message_standard_params(subject, msg)

        msg.attach(MIMEText(body))

        msg.attach(self.html_attachment())

        self.send_message(msg)

        if not self.check_message_delivered(subject):
            raise Exception

    def test_009_send_plaintext_forwarded(self):
        subject = "test_009_send_plaintext_forwarded"
        body = "This is a plaintext message"

        from tests.functional.user_add import user_add
        user_add("Jane", "Doe")

        from tests.functional.synchronize import synchronize_once
        synchronize_once()

        admin_login = conf.get('cyrus-imap', 'admin_login')
        admin_password = conf.get('cyrus-imap', 'admin_password')

        import sievelib.factory
        script = sievelib.factory.FiltersSet("test_wallace_test_009_forward")
        script.require("copy")
        script.addfilter("forward", ["true"], [("redirect", ":copy", "john.doe@example.org")])

        import sievelib.managesieve
        sieveclient = sievelib.managesieve.Client('localhost', 4190, True)
        sieveclient.connect(None, None, True)
        sieveclient._plain_authentication(admin_login, admin_password, 'jane.doe@example.org')
        sieveclient.authenticated = True

        script_str = script.__str__()

        print script_str

        sieveclient.putscript("test_wallace_test_009_forward", script_str)

        sieveclient.setactive("test_wallace_test_009_forward")

        msg = MIMEText(body)
        msg['From'] = self.message_from
        msg['To'] = '"Doe, Jane" <jane.doe@example.org>'

        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)

        self.send_message(msg, _to='jane.doe@example.org', _from='john.doe@example.org')

        raise Exception
