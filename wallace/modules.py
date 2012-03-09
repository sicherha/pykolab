# -*- coding: utf-8 -*-
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
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

import os
import sys
import time

from email import message_from_file
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.message import MIMEMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE
from email.utils import formatdate
from email.utils import formataddr
from email.utils import getaddresses
from email.utils import parsedate_tz

import smtplib

import pykolab
from pykolab import constants
from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

modules = {}

def __init__():
    # We only want the base path
    modules_base_path = os.path.dirname(__file__)

    for modules_path, dirnames, filenames in os.walk(modules_base_path):
        if not modules_path == modules_base_path:
            continue

        for filename in filenames:
            if filename.startswith('module_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                name = module_name.replace('module_', '')
                #print "exec(\"from %s import __init__ as %s_register\"" % (module_name,name)
                exec("from %s import __init__ as %s_register" % (module_name, name))
                exec("%s_register()" % (name))

        for dirname in dirnames:
            register_group(modules_path, dirname)

def list_modules(*args, **kw):
    """
        List modules
    """

    __modules = {}

    for module in modules.keys():
        if isinstance(module, tuple):
            module_group, module = module
            __modules[module_group] = {
                    module: modules[(module_group,module)]
                }
        else:
            __modules[module] = modules[module]

    _modules = __modules.keys()
    _modules.sort()

    for _module in _modules:
        if __modules[_module].has_key('function'):
            # This is a top-level module
            if not __modules[_module]['description'] == None:
                print "%-25s - %s" % (_module.replace('_','-'),__modules[_module]['description'])
            else:
                print "%-25s" % (_module.replace('_','-'))

    for _module in _modules:
        if not __modules[_module].has_key('function'):
            # This is a nested module
            print "\n" + _("Module Group: %s") % (_module) + "\n"
            ___modules = __modules[_module].keys()
            ___modules.sort()
            for __module in ___modules:
                if not __modules[_module][__module]['description'] == None:
                    print "%-4s%-21s - %s" % ('',__module.replace('_','-'),__modules[_module][__module]['description'])
                else:
                    print "%-4s%-21s" % ('',__module.replace('_','-'))

def execute(name, *args, **kw):
    if not modules.has_key(name):
        log.error(_("No such module."))
        sys.exit(1)

    if not modules[name].has_key('function') and \
        not modules[name].has_key('group'):
        log.error(_("No such module."))
        sys.exit(1)

    modules[name]['function'](*args, **kw)

def cb_action_HOLD(module, filepath):
    log.info(_("Holding message in queue for manual review (%s by %s)") % (filepath, module))

def cb_action_DEFER(module, filepath):
    log.info(_("Deferring message in %s (by module %s)") % (filepath, module))
    message = message_from_file(open(filepath, 'r'))

    internal_time = parsedate_tz(message.__getitem__('Date'))
    internal_time = time.mktime(internal_time[:9]) + internal_time[9]

    now_time = time.time()

    delta = now_time - internal_time

    log.debug(_("The time when the message was sent: %r") % (internal_time), level=8)
    log.debug(_("The time now: %r") % (now_time), level=8)
    log.debug(_("The time delta: %r") % (delta), level=8)

    if delta > 432000:
        # TODO: Send NDR back to user
        log.debug(_("Message in file %s older then 5 days, deleting") % (filepath), level=8)
        os.unlink(filepath)

    # Alternative method is file age.
    #Date sent(/var/spool/pykolab/wallace/optout/DEFER/tmpIv7pDl): 'Thu, 08 Mar 2012 11:51:03 +0000'
    #(2012, 3, 8, 11, 51, 3, 0, 1, -1)
    # YYYY M D H m s weekday, yearday

    #log.debug(datetime.datetime(*), level=8)

    #import os
    #stat = os.stat(filepath)

    #fileage = datetime.datetime.fromtimestamp(stat.st_mtime)
    #now = datetime.datetime.now()
    #delta = now - fileage

    #print "file:", filepath, "fileage:", fileage, "now:", now, "delta(seconds):", delta.seconds

    #if delta.seconds > 1800:
        ## TODO: Send NDR back to user
        #log.debug(_("Message in file %s older then 1800 seconds, deleting") % (filepath), level=8)
        #os.unlink(filepath)

def cb_action_REJECT(module, filepath):
    log.info(_("Rejecting message in %s (by module %s)") % (filepath, module))

    message = message_from_file(open(filepath, 'r'))
    envelope_sender = getaddresses(message.get_all('From', []))

    recipients = getaddresses(message.get_all('To', [])) + \
            getaddresses(message.get_all('Cc', []))

    _recipients = []

    for recipient in recipients:
        if not recipient[0] == '':
            _recipients.append('%s <%s>' % (recipient[0], recipient[1]))
        else:
            _recipients.append('%s' % (recipient[1]))

    # TODO: Find the preferredLanguage for the envelope_sender user.
    ndr_message_subject = "Undelivered Mail Returned to Sender"
    ndr_message_text = _("""This is the email system Wallace at %s.

I'm sorry to inform you we could not deliver the attached message
to the following recipients:

- %s

Your message is being delivered to any other recipients you may have
sent your message to. There is no need to resend the message to those
recipients.
""") % (
        constants.fqdn,
        "\n- ".join(_recipients)
        )

    diagnostics = _("""X-Wallace-Module: %s
X-Wallace-Result: REJECT
""") % (
            module
        )

    msg = MIMEMultipart("report")
    msg['From'] = "MAILER-DAEMON@%s" % (constants.fqdn)
    msg['To'] = formataddr(envelope_sender)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = ndr_message_subject

    msg.preamble = "This is a MIME-encapsulated message."

    part = MIMEText(ndr_message_text)
    part.add_header("Content-Description", "Notification")
    msg.attach(part)

    _diag_message = Message()
    _diag_message.set_payload(diagnostics)
    part = MIMEMessage(_diag_message, "delivery-status")
    part.add_header("Content-Description", "Delivery Report")
    msg.attach(part)

    part = MIMEMessage(message)
    part.add_header("Content-Description", "Undelivered Message")
    msg.attach(part)

    smtp = smtplib.SMTP("localhost", 10027)

    try:
        smtp.sendmail(
                "MAILER-DAEMON@%s" % (constants.fqdn),
                [formataddr(envelope_sender)],
                msg.as_string()
            )
    except smtplib.SMTPDataError, errmsg:
        # DEFER
        pass
    except smtplib.SMTPHeloError, errmsg:
        # DEFER
        pass
    except smtplib.SMTPRecipientsRefused, errmsg:
        # REJECT, send NDR
        pass
    except smtplib.SMTPSenderRefused, errmsg:
        # REJECT, send NDR
        pass
    finally:
        os.unlink(filepath)

def cb_action_ACCEPT(module, filepath):
    log.info(_("Accepting message in %s (by module %s)") % (filepath, module))
    message = message_from_file(open(filepath, 'r'))
    envelope_sender = getaddresses(message.get_all('From', []))

    recipients = getaddresses(message.get_all('To', [])) + \
            getaddresses(message.get_all('Cc', []))

    smtp = smtplib.SMTP("localhost", 10027)

    try:
        smtp.sendmail(
                formataddr(envelope_sender),
                COMMASPACE.join(
                        [formataddr(recipient) for recipient in recipients]
                    ),
                message.as_string()
            )
    except smtplib.SMTPDataError, errmsg:
        # DEFER
        pass
    except smtplib.SMTPHeloError, errmsg:
        # DEFER
        pass
    except smtplib.SMTPRecipientsRefused, errmsg:
        # DEFER
        pass
    except smtplib.SMTPSenderRefused, errmsg:
        # DEFER
        pass
    finally:
        os.unlink(filepath)

def register_group(dirname, module):
    modules_base_path = os.path.join(os.path.dirname(__file__), module)

    modules[module] = {}

    for modules_path, dirnames, filenames in os.walk(modules_base_path):
        if not modules_path == modules_base_path:
            continue

        for filename in filenames:
            if filename.startswith('module_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                name = module_name.replace('module_', '')
                #print "exec(\"from %s.%s import __init__ as %s_%s_register\"" % (module,module_name,module,name)
                exec("from %s.%s import __init__ as %s_%s_register" % (module,module_name,module,name))
                exec("%s_%s_register()" % (module,name))

def register(name, func, group=None, description=None, aliases=[]):
    if not group == None:
        module = "%s_%s" % (group,name)
    else:
        module = name

    if isinstance(aliases, basestring):
        aliases = [aliases]

    if modules.has_key(module):
        log.fatal(_("Module '%s' already registered") % (module))
        sys.exit(1)

    if callable(func):
        if group == None:
            modules[name] = {
                    'function': func,
                    'description': description
                }
        else:
            modules[group][name] = {
                    'function': func,
                    'description': description
                }

            modules[module] = modules[group][name]
            modules[module]['group'] = group
            modules[module]['name'] = name

        for alias in aliases:
            modules[alias] = {
                    'function': func,
                    'description': _("Alias for %s") % (name)
                }

