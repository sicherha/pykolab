# -*- coding: utf-8 -*-
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

import os
import re
import tempfile
import time

from email import message_from_file
from email.encoders import encode_quopri

import modules
import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace/footer')
extra_log_params = {'qid': '-'}
log = pykolab.logger.LoggerAdapter(log, extra_log_params)
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/footer/'

def __init__():
    modules.register('footer', execute, description=description())

def description():
    return """Append a footer to messages."""

def append_footer(content, footer, position=None, isHtml=False):
    if (isHtml):
        append = "\n<!-- footer appended by Wallace -->\n" + footer + "\n<!-- footer end -->\n"
        if position == 'top':
            match = re.search('(<body[^>]*>)', content, re.IGNORECASE | re.DOTALL)
            if match:
                content = content.replace(match.group(0), match.group(0) + append)
            else:
                content = "<html><body>" + append + content + "</body></html>"
        else:
            match = re.search('(</body>)', content, re.IGNORECASE | re.DOTALL)
            if match:
                content = content.replace(match.group(0), append + match.group(0))
            else:
                content = "<html><body>" + content + append + "</body></html>"
    else:
        if position == 'top':
            content = footer + "\n\n" + content
        else:
            content += "\n\n-- \n" + footer

    return content

def set_part_content(part, content):
    # Reset old encoding and use quoted-printable (#5414)
    del part['Content-Transfer-Encoding']
    part.set_payload(content)
    encode_quopri(part)

    return True

def execute(*args, **kw):
    global extra_log_params

    # TODO: Test for correct call.
    filepath = args[0]

    extra_log_params['qid'] = os.path.basename(filepath)

    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT']:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    if 'stage' in kw:
        log.debug(_("Issuing callback after processing to stage %s") % (kw['stage']), level=8)
        log.debug(_("Testing cb_action_%s()") % (kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' % (kw['stage'])):
            log.debug(_("Attempting to execute cb_action_%s()") % (kw['stage']), level=8)
            exec('modules.cb_action_%s(%r, %r)' % (kw['stage'],'optout',filepath))
            return

    log.debug(_("Executing module footer for %r, %r") % (args, kw), level=8)

    new_filepath = os.path.join('/var/spool/pykolab/wallace/footer/incoming', os.path.basename(filepath))
    os.rename(filepath, new_filepath)
    filepath = new_filepath

    # parse message
    message = message_from_file(open(filepath, 'r'))

    # Possible footer answers are limited to ACCEPT only
    answers = [ 'ACCEPT' ]

    footer = {}

    footer_position = conf.get('wallace', 'footer_position')
    footer_html_file = conf.get('wallace', 'footer_html')
    footer_text_file = conf.get('wallace', 'footer_text')

    if not os.path.isfile(footer_text_file) and not os.path.isfile(footer_html_file):
        log.warning(_("No contents configured for footer module"))
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', filepath))
        return

    if os.path.isfile(footer_text_file):
        footer['plain'] = open(footer_text_file, 'r').read()

    if not os.path.isfile(footer_html_file):
        footer['html'] = '<p>' + footer['plain'] + '</p>'
    else:
        footer['html'] = open(footer_html_file, 'r').read()
        if footer['html'] == "":
            footer['html'] = '<p>' + footer['plain'] + '</p>'

    if footer['plain'] == "" and footer['html'] == "<p></p>":
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', filepath))
        return

    footer_added = False

    try:
        _footer_added = message.get("X-Wallace-Footer")
    except:
        pass

    if _footer_added == "YES":
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', filepath))
        return

    for part in message.walk():
        disposition = None

        try:
            content_type = part.get_content_type()
        except:
            continue

        try:
            disposition = part.get("Content-Disposition")
        except:
            pass

        log.debug("Walking message part: %s; disposition = %r" % (content_type, disposition), level=8)

        if disposition is not None:
            continue

        if content_type == "text/plain":
            content = part.get_payload(decode=True)
            content = append_footer(content, footer['plain'], footer_position, False)
            footer_added = set_part_content(part, content)

        elif content_type == "text/html":
            content = part.get_payload(decode=True)
            content = append_footer(content, footer['html'], footer_position, True)
            footer_added = set_part_content(part, content)

    if footer_added:
        log.debug("Footer attached.")
        message.add_header("X-Wallace-Footer", "YES")

    (fp, new_filepath) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/footer/ACCEPT")
    os.write(fp, message.as_string())
    os.close(fp)
    os.unlink(filepath)

    exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', new_filepath))
