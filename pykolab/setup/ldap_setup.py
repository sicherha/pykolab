# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
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

import logging
import os
import sys

try:
    import ldap
except ImportError, e:
    print >> sys.stderr, _("Cannot load Python LDAP libraries.")

import pykolab
from pykolab import constants
from pykolab import utils
from pykolab.setup import package
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup.ldap')
conf = pykolab.getConf()

def setup():
    """
        Setup LDAP from here.
    """

    (service, other_services) = utils.is_service([
            'dirsrv',
            'ldap',
            'slapd'
        ])

    for item in other_services:
        log.warning(_("Warning: LDAP Service '%s' is available on " + \
                            "this system as well.") %(item))

    if not service == None:
        log.info(_("Found system service %s.") %(service))
    else:
        package.Package('openldap-servers')

    standard_root_dn = utils.standard_root_dn(constants.domainname)

    root_dn = utils.ask_question("Root DN", standard_root_dn)
    manager_dn = utils.ask_question("Manager DN", "cn=manager")
    manager_pw = utils.ask_question("Manager Password", password=True)

