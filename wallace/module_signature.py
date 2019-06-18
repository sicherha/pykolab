# -*- coding: utf-8 -*-
# Copyright 2010-2019 Kolab Systems AG (http://www.kolabsys.com)
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

import json
import os
import re
import tempfile

from email.encoders import encode_quopri
from email.parser import Parser
from email.utils import getaddresses

import modules
import pykolab

from pykolab.auth import Auth
from pykolab.translate import _

# pylint: disable=invalid-name
log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/signature/'


def __init__():
    modules.register('signature', execute, description=description())


def description():
    return """Append a signature to messages."""


def set_part_content(part, content):
    # Reset old encoding and use quoted-printable (#5414)
    del part['Content-Transfer-Encoding']
    part.set_payload(content)
    encode_quopri(part)

    return True


def attr_resolve(sender_info, attr):
    try:
        attr, attr_val = attr.split(':')
    except ValueError:
        return None

    auth = Auth()
    auth.connect()

    values = []

    if not isinstance(sender_info[attr], list):
        sender_info[attr] = [sender_info[attr]]

    for sender_attr_val in sender_info[attr]:
        values.append(auth.get_entry_attribute(None, sender_attr_val, attr_val))

    return ", ".join(values)


# pylint: disable=too-many-branches,too-many-locals,too-many-statements
def execute(*args, **kw):  # noqa: C901
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT']:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    # TODO: Test for correct call.
    filepath = args[0]

    if 'stage' in kw:
        log.debug(_("Issuing callback after processing to stage %s") % (kw['stage']), level=8)
        log.debug(_("Testing cb_action_%s()") % (kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' % (kw['stage'])):
            log.debug(_("Attempting to execute cb_action_%s()") % (kw['stage']), level=8)
            exec('modules.cb_action_%s(%r, %r)' % (kw['stage'], 'signature', filepath))
            return

    log.debug(_("Executing module signature for %r, %r") % (args, kw), level=8)

    new_filepath = os.path.join(
        '/var/spool/pykolab/wallace/signature/incoming',
        os.path.basename(filepath)
    )

    os.rename(filepath, new_filepath)
    filepath = new_filepath

    # parse message
    message = Parser().parse(open(filepath, 'r'))

    sender_address = [
        address for displayname, address in getaddresses(message.get_all('X-Kolab-From'))
    ][0]

    auth = Auth()
    auth.connect()

    sender_dn = auth.find_recipient(sender_address)
    if not sender_dn:
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT', 'signature', filepath))
        return

    sender_info = auth.get_entry_attributes(None, sender_dn, ['*', 'entrydn', 'manager'])

    log.debug("Sender info: %r" % (sender_info), level=7)

    signature_rules = conf.get_raw('wallace', 'signature_rules')

    if signature_rules:
        signature_rules = json.loads(signature_rules)

    log.debug("Signature rules: %r" % (signature_rules), level=7)

    signature_html = None
    signature_text = None

    sig_html_conf = conf.get_raw('wallace', 'signature_file_html')
    sig_text_conf = conf.get_raw('wallace', 'signature_file_text')

    if sig_html_conf and sig_text_conf:
        _sig_html_conf = sig_html_conf % sender_info
        _sig_text_conf = sig_text_conf % sender_info

        if not os.path.exists(_sig_html_conf):
            _sig_html_conf = '/etc/kolab/signature.d/default.html'

        if not os.path.exists(_sig_text_conf):
            _sig_text_conf = '/etc/kolab/signature.d/default.txt'

        if os.path.exists(_sig_html_conf):
            signature_html = open(_sig_html_conf, 'r').read()

        if os.path.exists(_sig_text_conf):
            signature_text = open(_sig_text_conf, 'r').read()

    if not signature_html and not signature_text:
        for signature_rule in signature_rules:
            try:
                for attr, regex in signature_rule.iteritems():
                    if attr == "html":
                        if not os.path.exists(signature_rule['html']):
                            raise ValueError
                        continue

                    if attr == "text":
                        if not os.path.exists(signature_rule['text']):
                            raise ValueError
                        continue

                    if attr in sender_info and re.match(regex, sender_info[attr], flags=re.IGNORECASE):
                        success = False

                        while not success:
                            try:
                                signature_html = open(signature_rule['html'], 'r').read() % sender_info
                                signature_text = open(signature_rule['text'], 'r').read() % sender_info

                                success = True

                            except KeyError as errmsg:
                                sender_info[errmsg] = attr_resolve(sender_info, errmsg)
            except ValueError:
                continue

    if signature_html is None and signature_text is None:
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT', 'signature', filepath))
        return

    signature_added = False

    try:
        _signature_added = message.get("X-Wallace-Signature")

    # pylint: disable=broad-except
    except Exception:
        pass

    if _signature_added == "YES":
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','signature', filepath))
        return

    for part in message.walk():
        disposition = None

        try:
            content_type = part.get_content_type()

        # pylint: disable=broad-except
        except Exception:
            continue

        try:
            disposition = part.get("Content-Disposition")

        # pylint: disable=broad-except
        except Exception:
            pass

        log.debug("Walking message part: %s; disposition = %r" % (content_type, disposition), level=8)

        if disposition is not None:
            continue

        if content_type == "text/plain":
            content = part.get_payload(decode=True)
            content += "\n\n-- \n%s" % (signature_text)
            signature_added = set_part_content(part, content)

        elif content_type == "text/html":
            content = part.get_payload(decode=True)
            append = "\n<!-- signature appended by Wallace -->\n" + signature_html
            if "</body>" in content:
                content = content.replace("</body>", append + "</body>")
            else:
                content = "<html><body>" + content + append + "</body></html>"
            signature_added = set_part_content(part, content)

    if signature_added:
        log.debug("Signature attached.", level=8)
        message.add_header("X-Wallace-Signature", "YES")

    (fp, new_filepath) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/signature/ACCEPT")
    os.write(fp, message.as_string())
    os.close(fp)
    os.unlink(filepath)

    exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','signature', new_filepath))
