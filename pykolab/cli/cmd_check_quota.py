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
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('check_quota', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))

    my_option_group.add_option(
            '--dry-run',
            dest    = "dryrun",
            action  = "store",
            default = False,
            help    = _("Do not apply any changes.")
        )

    my_option_group.add_option(
            '--server',
            dest    = "connect_server",
            action  = "store",
            default = None,
            metavar = "SERVER",
            help    = _("List mailboxes on server SERVER only.")
        )

def description():
    return _("Compare existing IMAP quota with LDAP quota.")

def execute(*args, **kw):
    """
        List mailboxes
    """

    imap = IMAP()
    imap.connect(server=conf.connect_server)

    auth = Auth()
    auth.connect()

    domains = auth.list_domains()

    folders = []
    for domain in domains:
        folders = imap.lm("user/%%@%s" % (domain))

        domain_auth = Auth(domain=domain)
        domain_auth.connect(domain=domain)

        for folder in folders:
            login = folder.split('/')[1]
            user_dn = domain_auth.find_recipient(login)

            if user_dn == None:
                print(_("No such user %s") % (login), file=sys.stderr)
                continue

            if len(login.split('@')) > 1:
                domain = login.split('@')[1]
            else:
                domain = conf.get('kolab', 'primary_domain')

            try:
                user_quota = auth.get_entry_attribute(domain, user_dn, 'mailquota')
            except:
                user_quota = None

            if user_quota == None:
                print(_("No quota for user %s") % (login), file=sys.stderr)
                continue

            try:
                (used, quota) = imap.get_quota(folder)

                if not (int)(quota) == (int)(user_quota):
                    print(_("user quota does not match for %s (IMAP: %d, LDAP: %d)") % (login, (int)(quota), (int)(user_quota)), file=sys.stderr)
                
            except:
                pass
