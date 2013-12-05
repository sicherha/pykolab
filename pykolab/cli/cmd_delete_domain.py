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

import sys

import commands

import pykolab

from pykolab import utils
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('delete_domain', execute, description=description())

def description():
    return _("Delete a domain.")

def execute(*args, **kw):
    from pykolab import wap_client

    # Use uber-administrative privileges
    username = conf.get('ldap', 'bind_dn')
    if username == None:
        log.error(_("Could not find credentials with sufficient permissions" + \
                "to add a domain name space."))

        sys.exit(1)

    wap_client.authenticate(username=username)

    dna = conf.get('ldap', 'domain_name_attribute')

    try:
        domain = conf.cli_args.pop(0)
    except IndexError, errmsg:
        domain = utils.ask_question(_("Domain name"))

    wap_client.domain_delete(domain)
