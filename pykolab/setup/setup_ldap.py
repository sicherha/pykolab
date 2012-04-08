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

import ldap
import ldap.modlist
import os
import shutil
import subprocess
import tempfile

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

    _input['admin_pass'] = utils.ask_question(
            _("Administrator password"),
            default=utils.generate_password(),
            password=True
        )

    _input['dirmgr_pass'] = utils.ask_question(
            _("Directory Manager password"),
            default=utils.generate_password(),
            password=True
        )

    _input['userid'] = utils.ask_question(_("User"), default="nobody")
    _input['group'] = utils.ask_question(_("Group"), default="nobody")

    _input['fqdn'] = fqdn
    _input['hostname'] = hostname.split('.')[0]
    _input['domain'] = domainname

    _input['nodotdomain'] = domainname.replace('.','_')

    _input['rootdn'] = utils.standard_root_dn(domainname)

    data = """
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
Suffix = %(rootdn)s
RootDN = cn=Directory Manager
RootDNPwd = %(dirmgr_pass)s
ds_bename = %(nodotdomain)s
AddSampleEntries = No

[admin]
Port = 9830
ServerAdminID = admin
ServerAdminPwd = %(admin_pass)s
""" % (_input)

    (fp, filename) = tempfile.mkstemp(dir="/tmp/")
    os.write(fp, data)
    os.close(fp)

    command = [
            '/usr/sbin/setup-ds-admin.pl',
            '--silent',
            '--file=%s' % (filename)
        ]

    setup_389 = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    (stdoutdata, stderrdata) = setup_389.communicate()

    # Copy in kolab schema
    #
    shutil.copy(
            '/usr/share/doc/kolab-schema-3.0/kolab2.ldif',
            '/etc/dirsrv/slapd-%s/schema/99kolab2.ldif' % (_input['hostname'])
        )

    subprocess.call(['service', 'dirsrv@%s' % (_input['hostname']), 'restart'])

    # Write out kolab configuration
    conf.command_set('kolab', 'primary_domain', _input['domain'])
    conf.command_set('ldap', 'base_dn', _input['rootdn'])
    conf.command_set('ldap', 'bind_dn', 'cn=Directory Manager')
    conf.command_set('ldap', 'bind_pw', _input['dirmgr_pass'])

    _input['cyrus_admin_pass'] = utils.ask_question(
            _("Cyrus Administrator password"),
            default=utils.generate_password(),
            password=True
        )

    _input['kolab_service_pass'] = utils.ask_question(
            _("Kolab Service password"),
            default=utils.generate_password(),
            password=True
        )

    # Insert service users
    auth = pykolab.auth
    auth.connect()
    auth._auth._connect()
    auth._auth._bind()

    dn = 'uid=cyrus-admin,ou=Special Users,%s' % (_input['rootdn'])

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectclass'] = ['top','person','inetorgperson','organizationalperson']
    attrs['uid'] = "cyrus-admin"
    attrs['givenname'] = "Cyrus"
    attrs['surname'] = "Administrator"
    attrs['cn'] = "Cyrus Administrator"
    attrs['userPassword'] = _input['cyrus_admin_pass']

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = ldap.modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    auth._auth.ldap.add_s(dn, ldif)

    conf.command_set('cyrus-imap', 'admin_password', _input['cyrus_admin_pass'])

    dn = 'uid=kolab-service,ou=Special Users,%s' % (_input['rootdn'])

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectclass'] = ['top','person','inetorgperson','organizationalperson']
    attrs['uid'] = "kolab-service"
    attrs['givenname'] = "Kolab"
    attrs['surname'] = "Service"
    attrs['cn'] = "Kolab Service"
    attrs['userPassword'] = _input['kolab_service_pass']

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = ldap.modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    auth._auth.ldap.add_s(dn, ldif)

    #dn: cn=kolab,cn=config
    #objectClass: top
    #objectClass: extensibleObject
    #cn: kolab

    dn = 'cn=kolab,cn=config'

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectclass'] = ['top','extensibleobject']
    attrs['cn'] = "kolab"

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = ldap.modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    auth._auth.ldap.add_s(dn, ldif)

    auth._auth._set_user_attribute(
            dn,
            'aci',
            '(targetattr = "*") (version 3.0;acl "Kolab Services";allow (read,compare,search)(userdn = "ldap:///%s");)' % ('uid=kolab-service,ou=Special Users,%s' % (_input['rootdn']))
        )

    # TODO: Add the primary domain to cn=kolab,cn=config
    # TODO: Make sure 'uid' is unique
    # TODO: Enable referential integrity plugin
