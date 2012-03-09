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

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register('ldap', execute, description=description())

def description():
    return _("Setup LDAP.")

def execute(*args, **kw):
    _input = {}

    _input['admin_pass'] = utils.ask_question(_("Administrator password"), password=True)
    _input['dirmgr_pass'] = utils.ask_question(_("Directory Manager password"), password=True)

    _input['userid'] = utils.ask_question(_("User"), default="nobody")
    _input['group'] = utils.ask_question(_("Group"), default="nobody")

    _input['fqdn'] = fqdn
    _input['hostname'] = hostname
    _input['domain'] = domainname

    _input['nodotdomain'] = domainname.replace('.','_')

    _input['rootdn'] = utils.standard_root_dn(domainname)

    print """
[General]
FullMachineName = %(fqdn)s
SuiteSpotUserID = %(userid)s
SuiteSpotGroup = %(group)s
AdminDomain = %(domain)s
ConfigDirectoryLdapURL = ldap://%(fqdn)s:389/o=NetscapeRoot
ConfigDirectoryAdminID = admin
ConfigDirectoryAdminPwd = %(admin_pass)s

[slapd]
SlapdConfigForMC = Yes
UseExistingMC = 0
ServerPort = 389
ServerIdentifier = %(hostname)s
Suffix = dc=test90,dc=kolabsys,dc=com
RootDN = cn=Directory Manager
RootDNPwd = %(dirmgr_pass)s
ds_bename = %(nodotdomain)s
AddSampleEntries = No

[admin]
Port = 9830
ServerAdminID = admin
ServerAdminPwd = %(admin_pass)s
""" % (_input)
