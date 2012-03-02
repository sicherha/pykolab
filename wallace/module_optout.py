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
import random
import tempfile
import time

import modules

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/optout/'

def __init__():
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    modules.register('optout', execute, description=description())

def description():
    return """Consult the opt-out service."""

def execute(*args, **kw):
    filepath = args[0]

    if kw.has_key('stage'):
        log.debug(_("Issuing callback after processing to stage %s") %(kw['stage']), level=8)
        log.debug(_("Testing cb_action_%s()") %(kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' %(kw['stage'])):
            log.debug(_("Attempting to execute cb_action_%s()") %(kw['stage']), level=8)
            exec('modules.cb_action_%s(%r, %r)' %(kw['stage'],'optout',filepath))
            return

        #modules.next_module('optout')

    log.debug(_("Consulting opt-out service for %r, %r") %(args, kw), level=8)


    import email
    message = email.message_from_file(open(filepath, 'r'))
    envelope_sender = email.utils.getaddresses(message.get_all('From', []))

    recipients = {
            "To": email.utils.getaddresses(message.get_all('To', [])),
            "Cc": email.utils.getaddresses(message.get_all('Cc', []))
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

    for recipient_type in recipients.keys():
        for recipient in recipients[recipient_type]:
            log.debug(
                    _("Running opt-out consult from envelope sender '%s " + \
                        "<%s>' to recipient %s <%s>") %(
                            envelope_sender[0][0],
                            envelope_sender[0][1],
                            recipient[0],
                            recipient[1]
                        ),
                    level=8
                )

            optout_answer = answers[random.randint(0,(len(answers)-1))]
            # Let's pretend it takes two seconds to get an answer, shall we?
            time.sleep(2)

            _recipients[optout_answer][recipient_type].append(recipient)

    #print _recipients

    ##
    ## TODO
    ##
    ## If one of them all is DEFER, DEFER the entire message and discard the
    ## other results.
    ##

    for answer in answers:
        if not os.path.isdir(os.path.join(mybasepath, answer)):
            os.makedirs(os.path.join(mybasepath, answer))

        # Consider using a new mktemp()-like call
        new_filepath = os.path.join(mybasepath, answer, os.path.basename(filepath))

        # Write out a message file representing the new contents for the message
        # use email.formataddr(recipient)
        _message = email.message_from_file(open(filepath, 'r'))

        use_this = False

        for recipient_type in _recipients[answer].keys():
            _message.__delitem__(recipient_type)
            if not len(_recipients[answer][recipient_type]) == 0:
                _message.__setitem__(recipient_type, ',\n'.join([email.utils.formataddr(x) for x in _recipients[answer][recipient_type]]))

                use_this = True

        if use_this:
            # TODO: Do not set items with an empty list.
            (fp, filename) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/optout/%s" %(answer))
            os.write(fp, _message.__str__())
            os.close(fp)

            # Callback with new filename
            if hasattr(modules, 'cb_action_%s' %(answer)):
                log.debug(_("Attempting to execute cb_action_%s()") %(answer), level=8)
                exec('modules.cb_action_%s(%r, %r)' %(answer,'optout', filename))

    os.unlink(filepath)

    #print "Moving filepath %s to new_filepath %s" %(filepath, new_filepath)
    #os.rename(filepath, new_filepath)

    #if hasattr(modules, 'cb_action_%s' %(optout_answer)):
        #log.debug(_("Attempting to execute cb_action_%s()") %(optout_answer), level=8)
        #exec('modules.cb_action_%s(%r, %r)' %(optout_answer,'optout', new_filepath))
        #return
