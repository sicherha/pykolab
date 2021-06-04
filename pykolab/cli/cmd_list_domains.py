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

import commands

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_domains', execute, description="List Kolab domains.")

def execute(*args, **kw):
    from pykolab import wap_client
    # Create the authentication object.
    # TODO: Binds with superuser credentials!
    wap_client.authenticate()
    domains = wap_client.domains_list()

    dna = conf.get('ldap', 'domain_name_attribute')

    print("%-39s %-40s" % ("Primary Domain Name Space","Secondary Domain Name Space(s)"))

    # TODO: Take a hint in --quiet, and otherwise print out a nice table
    # with headers and such.
    if isinstance(domains['list'], dict):
        for domain_dn in domains['list'].keys():
            if isinstance(domains['list'][domain_dn][dna], list):
                print(domains['list'][domain_dn][dna][0])
                for domain_alias in domains['list'][domain_dn][dna][1:]:
                    print("%-39s %-40s" % ('', domain_alias))
            else:
                print(domains['list'][domain_dn][dna])
