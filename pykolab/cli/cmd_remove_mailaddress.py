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

import sys

import commands

import pykolab

from pykolab.auth import Auth
from pykolab import utils
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('remove_mail', execute, description=description())

def description():
    return """Remove a recipient's mail address."""

def execute(*args, **kw):
    try:
        email_address = conf.cli_args.pop(0)
    except IndexError, errmsg:
        email_address = utils.ask_question("Email address to remove")

    # Get the domain from the email address
    if len(email_address.split('@')) > 1:
        domain = email_address.split('@')[1]
    else:
        log.error(_("Invalid or unqualified email address."))
        sys.exit(1)

    auth = Auth()
    auth.connect(domain=domain)
    recipients = auth.find_recipient(email_address)

    if len(recipients) == 0:
        log.error(_("No recipient found for email address %r") % (email_address))
        sys.exit(1)

    log.debug(_("Found the following recipient(s): %r") % (recipients), level=8)

    mail_attributes = conf.get_list(domain, 'mail_attributes')
    if mail_attributes == None or len(mail_attributes) < 1:
        mail_attributes = conf.get_list(conf.get('kolab', 'auth_mechanism'), 'mail_attributes')

    log.debug(_("Using the following mail attributes: %r") % (mail_attributes), level=8)

    if isinstance(recipients, basestring):
        recipient = recipients

        # Only a single recipient found, remove the address
        attributes = auth.get_entry_attributes(domain, recipient, mail_attributes)

        # See which attribute holds the value we're trying to remove
        for attribute in attributes.keys():
            if isinstance(attributes[attribute], list):
                if email_address in attributes[attribute]:
                    attributes[attribute].pop(attributes[attribute].index(email_address))
                    replace_attributes = {
                            attribute: attributes[attribute]
                        }

                    auth.set_entry_attributes(domain, recipient, replace_attributes)
            else:
                if email_address == attributes[attribute]:
                    auth.set_entry_attributes(domain, recipient, {attribute: None})
        pass

    else:
        print >> sys.stderr, _("Found the following recipients:")

        for recipient in recipients:
            print recipient
