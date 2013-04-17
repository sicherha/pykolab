# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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

from pykolab import utils
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('add_domain', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option(
            '--alias-for',
            dest    = "parent_domain",
            action  = "store",
            default = None,
            help    = _("Add domain as alias for DOMAIN"),
            metavar = "DOMAIN",
        )

def description():
    return _("Add a new domain or domain alias.")

def execute(*args, **kw):
    from pykolab import wap_client

    # Use uber-administrative privileges
    username = conf.get('ldap', 'bind_dn')
    if username == None:
        log.error(_("Could not find credentials with sufficient permissions" + \
                "to add a domain name space."))

        sys.exit(1)

    wap_client.authenticate(username=username)
    domains = wap_client.domains_list()

    dna = conf.get('ldap', 'domain_name_attribute')

    if not conf.parent_domain == None:
        parent_found = False
        if isinstance(domains['list'], dict):
            for _domain in domains['list'].keys():
                if parent_found:
                    continue

                if isinstance(domains['list'][_domain][dna], basestring):
                    if conf.parent_domain == domains['list'][_domain][dna]:
                        parent_found = True
                elif isinstance(domains['list'][_domain], list):
                    if conf.parent_domain in domains['list'][_domain][dna]:
                        parent_found = True

        if not parent_found:
            log.error(_("Invalid parent domain"))
            sys.exit(1)

    try:
        domain = conf.cli_args.pop(0)
    except IndexError, errmsg:
        domain = utils.ask_question(_("Domain name"))

    wap_client.domain_add(domain, conf.parent_domain)
