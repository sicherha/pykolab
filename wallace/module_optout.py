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

import json
import os
import random
import tempfile
import time
from urlparse import urlparse
import urllib

from email import message_from_file
from email.utils import formataddr
from email.utils import getaddresses

import modules

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace/optout')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/optout/'

def __init__():
    modules.register('optout', execute, description=description())

def description():
    return """Consult the opt-out service."""

def execute(*args, **kw):
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT', 'REJECT', 'HOLD', 'DEFER' ]:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    # TODO: Test for correct call.
    filepath = args[0]

    if kw.has_key('stage'):
        log.debug(_("Issuing callback after processing to stage %s") % (kw['stage']), level=8)
        log.debug(_("Testing cb_action_%s()") % (kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' % (kw['stage'])):
            log.debug(_("Attempting to execute cb_action_%s()") % (kw['stage']), level=8)
            exec('modules.cb_action_%s(%r, %r)' % (kw['stage'],'optout',filepath))
            return

        #modules.next_module('optout')

    log.debug(_("Consulting opt-out service for %r, %r") % (args, kw), level=8)

    message = message_from_file(open(filepath, 'r'))
    envelope_sender = getaddresses(message.get_all('From', []))

    recipients = {
            "To": getaddresses(message.get_all('To', [])),
            "Cc": getaddresses(message.get_all('Cc', []))
            # TODO: Are those all recipient addresses?
        }

    # optout answers are ACCEPT, REJECT, HOLD or DEFER
    answers = [ 'ACCEPT', 'REJECT', 'HOLD', 'DEFER' ]

    # Initialize our results placeholders.
    _recipients = {}

    for answer in answers:
        _recipients[answer] = {
                "To": [],
                "Cc": []
            }

    for recipient_type in recipients:
        for recipient in recipients[recipient_type]:
            log.debug(
                    _("Running opt-out consult from envelope sender '%s " + \
                        "<%s>' to recipient %s <%s>") % (
                            envelope_sender[0][0],
                            envelope_sender[0][1],
                            recipient[0],
                            recipient[1]
                        ),
                    level=8
                )

            optout_answer = request(
                    {
                            'unique-message-id': 'bogus',
                            'envelope_sender': envelope_sender[0][1],
                            'recipient': recipient[1]
                        }
                )

            _recipients[optout_answer][recipient_type].append(recipient)

    #print _recipients

    ##
    ## TODO
    ##
    ## If one of them all is DEFER, DEFER the entire message and discard the
    ## other results.
    ##

    for answer in answers:
        # Create the directory for the answer
        if not os.path.isdir(os.path.join(mybasepath, answer)):
            os.makedirs(os.path.join(mybasepath, answer))

        # Consider using a new mktemp()-like call
        new_filepath = os.path.join(mybasepath, answer, os.path.basename(filepath))

        # Write out a message file representing the new contents for the message
        # use formataddr(recipient)
        _message = message_from_file(open(filepath, 'r'))

        use_this = False

        for recipient_type in _recipients[answer]:
            _message.__delitem__(recipient_type)
            if not len(_recipients[answer][recipient_type]) == 0:
                _message.__setitem__(
                        recipient_type,
                        ',\n  '.join(
                                [formataddr(x) for x in _recipients[answer][recipient_type]]
                            )
                    )

                use_this = True

        if use_this:
            # TODO: Do not set items with an empty list.

            (fp, filename) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/optout/%s" % (answer))
            os.write(fp, _message.__str__())
            os.close(fp)

            # Callback with new filename
            if hasattr(modules, 'cb_action_%s' % (answer)):
                log.debug(_("Attempting to execute cb_action_%s(%r, %r)") % (answer, 'optout', filename), level=8)
                exec('modules.cb_action_%s(%r, %r)' % (answer,'optout', filename))

    os.unlink(filepath)

    #print "Moving filepath %s to new_filepath %s" % (filepath, new_filepath)
    #os.rename(filepath, new_filepath)

    #if hasattr(modules, 'cb_action_%s' % (optout_answer)):
        #log.debug(_("Attempting to execute cb_action_%s()") % (optout_answer), level=8)
        #exec('modules.cb_action_%s(%r, %r)' % (optout_answer,'optout', new_filepath))
        #return

def request(params=None):
    params = json.dumps(params)

    optout_url = conf.get('wallace_optout', 'optout_url')

    try:
        f = urllib.urlopen(optout_url, params)
    except Exception:
        log.error(_("Could not send request to optout_url %s") % (optout_url))
        return "DEFER"

    response = f.read()

    try:
        response_data = json.loads(response)
    except ValueError:
        # Some data is not JSON
        print("Response data is not JSON")

    return response_data['result']
