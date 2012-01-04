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

import commands

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

auth = pykolab.auth
imap = pykolab.imap

def __init__():
    commands.register('list_domains', execute, description="List Kolab domains.")

def execute(*args, **kw):
    auth.connect()

    # Create the authentication object.
    # TODO: Binds with superuser credentials!
    domains = auth.list_domains()

    print "%-39s %-40s" %("Primary Domain Name Space","Secondary Domain Name Space(s)")

    # TODO: Take a hint in --quiet, and otherwise print out a nice table
    # with headers and such.
    for domain,domain_aliases in domains:
        if len(domain_aliases) > 0:
            print _("%-39s %-40s") %(
                    domain,
                    ', '.join(domain_aliases)
                )
        else:
            print _("%-39s") %(domain)

