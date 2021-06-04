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

from __future__ import print_function

import sys

import commands

import pykolab

from pykolab.auth import Auth
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('add_alias', execute, description="Add alias.")

def execute(*args, **kw):

    try:
        primary_rcpt_address = conf.cli_args.pop(0)
        try:
            secondary_rcpt_address = conf.cli_args.pop(0)
        except:
            print(_("Specify the (new) alias address"), file=sys.stderr)
            sys.exit(1)
    except:
        print(_("Specify the existing recipient address"), file=sys.stderr)
        sys.exit(1)

    if len(primary_rcpt_address.split('@')) > 1:
        primary_rcpt_domain = primary_rcpt_address.split('@')[-1]
    else:
        primary_rcpt_domain = conf.get('kolab', 'primary_domain')

    auth = Auth(domain=primary_rcpt_domain)

    domains = auth.list_domains()

    #print domains

    if len(secondary_rcpt_address.split('@')) > 1:
        secondary_rcpt_domain = secondary_rcpt_address.split('@')[-1]
    else:
        secondary_rcpt_domain = conf.get('kolab', 'primary_domain')

    # Check if either is in fact a domain
    if not primary_rcpt_domain.lower() in domains.keys():
        print(_("Domain %r is not a local domain") % (primary_rcpt_domain), file=sys.stderr)
        sys.exit(1)

    if not secondary_rcpt_domain.lower() in domains.keys():
        print(_("Domain %r is not a local domain") % (secondary_rcpt_domain), file=sys.stderr)
        sys.exit(1)

    if not primary_rcpt_domain == secondary_rcpt_domain:
        if not domains[primary_rcpt_domain] == domains[secondary_rcpt_domain]:
            print(_("Primary and secondary domain do not have the same parent domain"), file=sys.stderr)
            sys.exit(1)

    primary_recipient_dn = auth.find_recipient(primary_rcpt_address)

    if primary_recipient_dn == [] or len(primary_recipient_dn) == 0:
        print(_("No such recipient %r") % (primary_rcpt_address), file=sys.stderr)
        sys.exit(1)

    secondary_recipient_dn = auth.find_recipient(secondary_rcpt_address)

    if not secondary_recipient_dn == [] and not len(secondary_recipient_dn) == 0:
        print(_("Recipient for alias %r already exists") % (secondary_rcpt_address), file=sys.stderr)
        sys.exit(1)

    rcpt_attrs = conf.get_list('ldap', 'mail_attributes')

    primary_rcpt_attr = rcpt_attrs[0]

    if len(rcpt_attrs) >= 2:
        secondary_rcpt_attr = rcpt_attrs[1]
    else:
        print(_("Environment is not configured for " + \
            "users to hold secondary mail attributes"), file=sys.stderr)

        sys.exit(1)

    primary_recipient = auth.get_entry_attributes(primary_rcpt_domain, primary_recipient_dn, rcpt_attrs)

    if not primary_recipient.has_key(primary_rcpt_attr):
        print(_("Recipient %r is not the primary recipient for address %r") % (primary_recipient, primary_rcpt_address), file=sys.stderr)
        sys.exit(1)

    if not primary_recipient.has_key(secondary_rcpt_attr):
        auth.set_entry_attributes(primary_rcpt_domain, primary_recipient_dn, {secondary_rcpt_attr: [ secondary_rcpt_address ] })
    else:
        if isinstance(primary_recipient[secondary_rcpt_attr], basestring):
            new_secondary_rcpt_attrs = [
                    primary_recipient[secondary_rcpt_attr],
                    secondary_rcpt_address
                ]

        else:
            new_secondary_rcpt_attrs = \
                    primary_recipient[secondary_rcpt_attr] + \
                    [ secondary_rcpt_address ]

        auth.set_entry_attributes(
                primary_rcpt_domain,
                primary_recipient_dn,
                {
                        secondary_rcpt_attr: new_secondary_rcpt_attrs
                    }
            )

