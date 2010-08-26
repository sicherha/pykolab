# -*- coding: utf-8 -*-
# Copyright 2010 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 only
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

import socket
import sys

from pykolab.translate import _

domain = 'pykolab'

epilog = _( "PyKolab is a Kolab Systems product. For more information " + \
            "about Kolab or PyKolab, visit http://www.kolabsys.com")

COMPONENTS = [
        'imap',
        'ldap',
        'mta'
    ]

hostname = socket.gethostname()
fqdn = socket.getfqdn()
try:
    domain_parts = fqdn.split('.')
    if len(domain_parts) < 3:
        print >> sys.stderr, _("WARNING") + ": " + _("The Fully Qualified " + \
                "Domain Name or FQDN for this system is incorrect. Falling " + \
                "back to 'localdomain'.")
        domainname = "localdomain"
    else:
        domainname = '.'.join(domain_parts[1:])
except IndexError:
    domainname = "localdomain"

# The system RC directory
RC_DIR = "/etc/rc.d/init.d/"

# Service map;
#
# Convert names of registered system services to their type. For example,
# on Red Hat, OpenLDAP is 'slapd', whereas on Debian, OpenLDAP is 'ldap'.
#
SERVICE_MAP = {
        'dirsrv': {
                'type':         '389ds',
                'description':  _('389 Directory Server or Red Hat Directory Server')
            },
        'ldap': {
                'type':         'openldap',
                'description':  _('OpenLDAP or compatible')
            },
        'slapd': {
                'type':         'openldap',
                'description':  _('OpenLDAP or compatible')
            },
    }