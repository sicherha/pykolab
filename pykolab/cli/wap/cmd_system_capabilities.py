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

import pykolab
from pykolab.cli import commands

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('system_capabilities', execute, group='wap', description="Display the system capabilities.")

def execute(*args, **kw):
    from pykolab import wap_client
    # Create the authentication object.
    # TODO: Binds with superuser credentials!
    wap_client.authenticate()
    system_capabilities = wap_client.system_capabilities()

    if system_capabilities['count'] < 1:
        print "No system capabilities"
        sys.exit(1)

    for domain in system_capabilities['list'].keys():
        print "Domain capabilities for %s" % (domain)

        domain_capabilities = system_capabilities['list'][domain]

        for service in domain_capabilities['actions'].keys():
            print "  %-15s - %r" % (service, domain_capabilities['actions'][service]['type'])
