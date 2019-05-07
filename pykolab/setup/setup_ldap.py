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

import ldap
import ldap.modlist
import os
import pwd
import shutil
import subprocess
import tempfile
import time

import components

import pykolab

from pykolab import utils
from pykolab.auth import Auth
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register('ldap', execute, description=description())

def cli_options():
    ldap_group = conf.add_cli_parser_option_group(_("LDAP Options"))

    ldap_group.add_option(
            "--fqdn",
            dest    = "fqdn",
            action  = "store",
            default = fqdn,
            help    = _("Specify FQDN (overriding defaults).")
        )

    ldap_group.add_option(
            "--allow-anonymous",
            dest    = "anonymous",
            action  = "store_true",
            default = False,
            help    = _("Allow anonymous binds (default: no).")
        )

    ldap_group.add_option(
            "--without-ldap",
            dest    = "without_ldap",
            action  = "store_true",
            default = False,
            help    = _("Skip setting up the LDAP server.")
        )

    ldap_group.add_option(
            "--with-openldap",
            dest    = "with_openldap",
            action  = "store_true",
            default = False,
            help    = _("Setup configuration for OpenLDAP compatibility.")
        )

    ldap_group.add_option(
            "--with-ad",
            dest    = "with_ad",
            action  = "store_true",
            default = False,
            help    = _("Setup configuration for Active Directory compatibility.")
        )

    ldap_group.add_option(
            "--directory-manager-pwd",
            dest    = "directory_manager_pwd",
            action  = "store",
            default = None,
            help    = _("Specify password for the Domain Manager.")
        )

def description():
    return _("Setup LDAP.")

def execute(*args, **kw):
    ask_questions = True

    if not conf.config_file == conf.defaults.config_file:
        ask_questions = False

    if conf.without_ldap:
        print >> sys.stderr, _("Skipping setup of LDAP, as specified")
        return

    _input = {}

    if conf.with_openldap and not conf.with_ad:

        conf.command_set('ldap', 'unique_attribute', 'entryuuid')

        fp = open(conf.defaults.config_file, "w+")
        conf.cfg_parser.write(fp)
        fp.close()

        return

    elif conf.with_ad and not conf.with_openldap:
        conf.command_set('ldap', 'auth_attributes', 'samaccountname')
        conf.command_set('ldap', 'modifytimestamp_format', '%%Y%%m%%d%%H%%M%%S.0Z')
        conf.command_set('ldap', 'unique_attribute', 'userprincipalname')

        # TODO: These attributes need to be checked
        conf.command_set('ldap', 'mail_attributes', 'mail')
        conf.command_set('ldap', 'mailserver_attributes', 'mailhost')
        conf.command_set('ldap', 'quota_attribute', 'mailquota')

        return

    elif conf.with_ad and conf.with_openldap:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        You can not configure Kolab to run against OpenLDAP
                        and Active Directory simultaneously.
                    """)
            )

        sys.exit(1)

    # Pre-execution checks
    for path, directories, files in os.walk('/etc/dirsrv/'):
        for direct in directories:
            if direct.startswith('slapd-'):
                print >> sys.stderr, utils.multiline_message(
                        _("""
                                It seems 389 Directory Server has an existing
                                instance configured. This setup script does not
                                intend to destroy or overwrite your data. Please
                                make sure /etc/dirsrv/ and /var/lib/dirsrv/ are
                                clean so that this setup does not have to worry.
                            """)
                    )

                sys.exit(1)

    _input = {}

    if ask_questions:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply a password for the LDAP administrator user
                        'admin', used to login to the graphical console of 389
                        Directory server.
                    """)
            )

        _input['admin_pass'] = utils.ask_question(
                _("Administrator password"),
                default=utils.generate_password(),
                password=True,
                confirm=True
            )

        if conf.directory_manager_pwd is not None:
            _input['dirmgr_pass'] = conf.directory_manager_pwd
        else:
            print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply a password for the LDAP Directory Manager
                        user, which is the administrator user you will be using
                        to at least initially log in to the Web Admin, and that
                        Kolab uses to perform administrative tasks.
                    """)
            )

            _input['dirmgr_pass'] = utils.ask_question(
                _("Directory Manager password"),
                default=utils.generate_password(),
                password=True,
                confirm=True
            )

        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please choose the system user and group the service
                        should use to run under. These should be existing,
                        unprivileged, local system POSIX accounts with no shell.
                    """)
            )

        try:
            pw = pwd.getpwnam("dirsrv")
        except:
            _input['userid'] = utils.ask_question(_("User"), default="nobody")
            _input['group'] = utils.ask_question(_("Group"), default="nobody")
        else:
            _input['userid'] = utils.ask_question(_("User"), default="dirsrv")
            _input['group'] = utils.ask_question(_("Group"), default="dirsrv")

    else:
        _input['admin_pass'] = conf.get('ldap', 'bind_pw')
        _input['dirmgr_pass'] = conf.get('ldap', 'bind_pw')
        try:
            pw = pwd.getpwnam("dirsrv")
        except:
            _input['userid'] = "nobody"
            _input['group'] = "nobody"
        else:
            _input['userid'] = "dirsrv"
            _input['group'] = "dirsrv"

    # TODO: Verify the user and group exist.

    # TODO: This takes the system fqdn, domainname and hostname, rather then
    # the desired fqdn, domainname and hostname.
    #
    # TODO^2: This should be confirmed.

    if conf.fqdn:
        _input['fqdn'] = conf.fqdn
        _input['hostname'] = conf.fqdn.split('.')[0]
        _input['domain'] = '.'.join(conf.fqdn.split('.')[1:])
    else:
        _input['fqdn'] = fqdn
        _input['hostname'] = hostname.split('.')[0]
        _input['domain'] = domainname
    _input['nodotdomain'] = _input['domain'].replace('.','_')

    _input['rootdn'] = utils.standard_root_dn(_input['domain'])

    if ask_questions:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        This setup procedure plans to set up Kolab Groupware for
                        the following domain name space. This domain name is
                        obtained from the reverse DNS entry on your network
                        interface. Please confirm this is the appropriate domain
                        name space.
                    """)
            )

        answer = utils.ask_confirmation("%s" % (_input['domain']))

        if not answer:
            positive_answer = False
            while not positive_answer:
                _input['domain'] = utils.ask_question(_("Domain name to use"))
                if not _input['domain'] == None and not _input['domain'] == "":
                    positive_answer = True
                else:
                    print >> sys.stderr, utils.multiline_message(
                            _("""
                                    Invalid input. Please try again.
                                """)
                        )

        _input['nodotdomain'] = _input['domain'].replace('.','_')
        _input['rootdn'] = utils.standard_root_dn(_input['domain'])

        print >> sys.stderr, utils.multiline_message(
                _("""
                        The standard root dn we composed for you follows. Please
                        confirm this is the root dn you wish to use.
                    """)
            )

        answer = utils.ask_confirmation("%s" % (_input['rootdn']))

        if not answer:
            positive_answer = False
            while not positive_answer:
                _input['rootdn'] = utils.ask_question(_("Root DN to use"))
                if not _input['rootdn'] == None and not _input['rootdn'] == "":
                    positive_answer = True
                else:
                    print >> sys.stderr, utils.multiline_message(
                            _("""
                                    Invalid input. Please try again.
                                """)
                        )

    # TODO: Loudly complain if the fqdn does not resolve back to this system.

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

    if os.path.isfile("/usr/sbin/setup-ds-admin.pl"):
        setup_ds_admin = "/usr/sbin/setup-ds-admin.pl"
    elif os.path.isfile("/usr/sbin/setup-ds-admin"):
        setup_ds_admin = "/usr/sbin/setup-ds-admin"
    elif os.path.isfile("/usr/sbin/setup-ds.pl"):
        setup_ds_admin = "/usr/sbin/setup-ds.pl"
    elif os.path.isfile("/usr/sbin/setup-ds"):
        setup_ds_admin = "/usr/sbin/setup-ds"
    else:
        log.error(_("No directory server setup tool available."))
        sys.exit(1)

    command = [
            setup_ds_admin,
            '--debug',
            '--silent',
            '--force',
            '--file=%s' % (filename)
        ]

    print >> sys.stderr, utils.multiline_message(
            _("""
                    Setup is now going to set up the 389 Directory Server. This
                    may take a little while (during which period there is no
                    output and no progress indication).
                """)
        )

    log.info(_("Setting up 389 Directory Server"))

    setup_389 = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    (stdoutdata, stderrdata) = setup_389.communicate()

    if not setup_389.returncode == 0:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        An error was detected in the setup procedure for 389
                        Directory Server. This setup will write out stderr and
                        stdout to /var/log/kolab/setup.error.log and
                        /var/log/kolab/setup.out.log respectively, before it
                        exits.
                    """)
            )

        fp = open('/var/log/kolab/setup.error.log', 'w')
        fp.write(stderrdata)
        fp.close()

        fp = open('/var/log/kolab/setup.out.log', 'w')
        fp.write(stdoutdata)
        fp.close()

    log.debug(_("Setup DS stdout:"), level=8)
    log.debug(stdoutdata, level=8)

    log.debug(_("Setup DS stderr:"), level=8)
    log.debug(stderrdata, level=8)

    if not setup_389.returncode == 0:
        sys.exit(1)

    # Find the kolab schema. It's installed as %doc in the kolab-schema package.
    # TODO: Chown nobody, nobody, chmod 440
    schema_file = None
    for root, directories, filenames in os.walk('/usr/share/doc/'):
        for filename in filenames:
            if filename.startswith('kolab') and filename.endswith('.ldif') and schema_file == None:
                schema_file = os.path.join(root,filename)

    if not schema_file == None:
        try:
            shutil.copy(
                    schema_file,
                    '/etc/dirsrv/slapd-%s/schema/99%s' % (
                            _input['hostname'],
                            os.path.basename(schema_file)
                        )
                )

            schema_error = False
        except:
            log.error(_("Could not copy the LDAP extensions for Kolab"))
            schema_error = True
    else:
        log.error(_("Could not find the ldap Kolab schema file"))
        schema_error = True

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'restart', 'dirsrv@' + _input['hostname']])
        time.sleep(20)
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['/sbin/service', 'dirsrv', 'restart'])
    elif os.path.isfile('/usr/sbin/service'):
        subprocess.call(['/usr/sbin/service','dirsrv','stop'])
        time.sleep(20)
        subprocess.call(['/usr/sbin/service','dirsrv','start'])
    else:
        log.error(_("Could not start the directory server service."))

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'enable', 'dirsrv@' + _input['hostname']])
    elif os.path.isfile('/sbin/chkconfig'):
        subprocess.call(['/sbin/chkconfig', 'dirsrv', 'on'])
    elif os.path.isfile('/usr/sbin/update-rc.d'):
        subprocess.call(['/usr/sbin/update-rc.d', 'dirsrv', 'defaults'])
    else:
        log.error(_("Could not configure to start on boot, the " + \
                "directory server service."))

    if ask_questions:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply a Cyrus Administrator password. This
                        password is used by Kolab to execute administrative
                        tasks in Cyrus IMAP. You may also need the password
                        yourself to troubleshoot Cyrus IMAP and/or perform
                        other administrative tasks against Cyrus IMAP directly.
                    """)
            )

        _input['cyrus_admin_pass'] = utils.ask_question(
                _("Cyrus Administrator password"),
                default=utils.generate_password(),
                password=True,
                confirm=True
            )

        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply a Kolab Service account password. This
                        account is used by various services such as Postfix,
                        and Roundcube, as anonymous binds to the LDAP server
                        will not be allowed.
                    """)
            )

        _input['kolab_service_pass'] = utils.ask_question(
                _("Kolab Service password"),
                default=utils.generate_password(),
                password=True,
                confirm=True
            )

    else:
        _input['cyrus_admin_pass'] = conf.get('cyrus-imap', 'admin_password')
        _input['kolab_service_pass'] = conf.get('ldap', 'service_bind_pw')

    log.info(_("Writing out configuration to kolab.conf"))

    # Write out kolab configuration
    conf.command_set('kolab', 'primary_domain', _input['domain'])
    conf.command_set('ldap', 'base_dn', _input['rootdn'])
    conf.command_set('ldap', 'bind_dn', 'cn=Directory Manager')
    conf.command_set('ldap', 'bind_pw', _input['dirmgr_pass'])
    conf.command_set('ldap', 'service_bind_dn', 'uid=kolab-service,ou=Special Users,%s' % (_input['rootdn']))
    conf.command_set('ldap', 'service_bind_pw', _input['kolab_service_pass'])

    fp = open(conf.defaults.config_file, "w+")
    conf.cfg_parser.write(fp)
    fp.close()

    log.info(_("Inserting service users into LDAP."))

    # Insert service users
    auth = Auth(_input['domain'])
    auth.connect()
    auth._auth.connect()
    auth._auth._bind(bind_dn='cn=Directory Manager', bind_pw=_input['dirmgr_pass'])

    dn = 'uid=%s,ou=Special Users,%s' % (conf.get('cyrus-imap', 'admin_login'), _input['rootdn'])

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectclass'] = ['top','person','inetorgperson','organizationalperson']
    attrs['uid'] = conf.get('cyrus-imap', 'admin_login')
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
    attrs['nslookthroughlimit'] = '-1'
    attrs['nssizelimit'] = '-1'
    attrs['nstimelimit'] = '-1'
    attrs['nsidletimeout'] = '-1'

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = ldap.modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    auth._auth.ldap.add_s(dn, ldif)

    dn = 'ou=Resources,%s' % (_input['rootdn'])

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectclass'] = ['top','organizationalunit']
    attrs['ou'] = "Resources"

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = ldap.modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    auth._auth.ldap.add_s(dn, ldif)

    dn = 'ou=Shared Folders,%s' % (_input['rootdn'])

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectclass'] = ['top','organizationalunit']
    attrs['ou'] = "Shared Folders"

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = ldap.modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    auth._auth.ldap.add_s(dn, ldif)

    log.info(_("Writing out cn=kolab,cn=config"))

    dn = 'cn=kolab,cn=config'

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectclass'] = ['top','extensibleobject']
    attrs['cn'] = "kolab"
    attrs['aci'] = '(targetattr = "*") (version 3.0;acl "Kolab Services";allow (read,compare,search)(userdn = "ldap:///uid=kolab-service,ou=Special Users,%s");)' % (_input['rootdn'])

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = ldap.modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    auth._auth.ldap.add_s(dn, ldif)

    log.info(_("Adding domain %s to list of domains for this deployment") % (_input['domain']))
    dn = "associateddomain=%s,cn=kolab,cn=config" % (_input['domain'])
    attrs = {}
    attrs['objectclass'] = ['top','domainrelatedobject']
    attrs['associateddomain'] = [
            '%s' % (_input['domain']),
            '%s' % (_input['fqdn']),
            'localhost.localdomain',
            'localhost'
        ]

    # De-duplicate attribute values before attempting to insert the object (#2205)
    attrs['associateddomain'] = list(set(attrs['associateddomain']))
    attrs['associateddomain'].pop(attrs['associateddomain'].index(_input['domain']))
    attrs['associateddomain'] = [ _input['domain'] ] + attrs['associateddomain']

    attrs['aci'] = '(targetattr = "*") (version 3.0;acl "Read Access for %(domain)s Users";allow (read,compare,search)(userdn = "ldap:///%(rootdn)s??sub?(objectclass=*)");)' % (_input)

    # Add inetdomainbasedn in case the configured root dn is not the same as the
    # standard root dn for the domain name configured
    if not _input['rootdn'] == utils.standard_root_dn(_input['domain']):
        attrs['objectclass'].append('inetdomain')
        attrs['inetdomainbasedn'] = _input['rootdn']

    ldif = ldap.modlist.addModlist(attrs)
    auth._auth.ldap.add_s(dn, ldif)

    if not conf.anonymous:
        log.info(_("Disabling anonymous binds"))
        dn = "cn=config"
        modlist = []
        modlist.append((ldap.MOD_REPLACE, "nsslapd-allow-anonymous-access", "off"))
        auth._auth.ldap.modify_s(dn, modlist)

    # TODO: Ensure the uid attribute is unique
    # TODO^2: Consider renaming the general "attribute uniqueness to "uid attribute uniqueness"
    log.info(_("Enabling attribute uniqueness plugin"))
    dn = "cn=attribute uniqueness,cn=plugins,cn=config"
    modlist = []
    modlist.append((ldap.MOD_REPLACE, "nsslapd-pluginEnabled", "on"))
    auth._auth.ldap.modify_s(dn, modlist)

    log.info(_("Enabling referential integrity plugin"))
    dn = "cn=referential integrity postoperation,cn=plugins,cn=config"
    modlist = []
    modlist.append((ldap.MOD_REPLACE, "nsslapd-pluginEnabled", "on"))
    auth._auth.ldap.modify_s(dn, modlist)

    log.info(_("Enabling and configuring account policy plugin"))
    dn = "cn=Account Policy Plugin,cn=plugins,cn=config"
    modlist = []
    modlist.append((ldap.MOD_REPLACE, "nsslapd-pluginEnabled", "on"))
    modlist.append((ldap.MOD_ADD, "nsslapd-pluginarg0", "cn=config,cn=Account Policy Plugin,cn=plugins,cn=config"))
    auth._auth.ldap.modify_s(dn, modlist)

    dn = "cn=config,cn=Account Policy Plugin,cn=plugins,cn=config"
    modlist = []
    modlist.append((ldap.MOD_REPLACE, "alwaysrecordlogin", "yes"))
    modlist.append((ldap.MOD_ADD, "stateattrname", "lastLoginTime"))
    modlist.append((ldap.MOD_ADD, "altstateattrname", "createTimestamp"))
    auth._auth.ldap.modify_s(dn, modlist)

    # Add kolab-admin role
    log.info(_("Adding the kolab-admin role"))
    dn = "cn=kolab-admin,%s" % (_input['rootdn'])
    attrs = {}
    attrs['description'] = "Kolab Administrator"
    attrs['objectClass'] = ['top','ldapsubentry','nsroledefinition','nssimpleroledefinition','nsmanagedroledefinition']
    attrs['cn'] = "kolab-admin"
    ldif = ldap.modlist.addModlist(attrs)

    auth._auth.ldap.add_s(dn, ldif)

    # User writeable attributes on root_dn
    log.info(_("Setting access control to %s") % (_input['rootdn']))
    dn = _input['rootdn']
    aci = []

    if schema_error:
        aci.append('(targetattr = "carLicense || description || displayName || facsimileTelephoneNumber || homePhone || homePostalAddress || initials || jpegPhoto || l || labeledURI || mobile || o || pager || photo || postOfficeBox || postalAddress || postalCode || preferredDeliveryMethod || preferredLanguage || registeredAddress || roomNumber || secretary || seeAlso || st || street || telephoneNumber || telexNumber || title || userCertificate || userPassword || userSMIMECertificate || x500UniqueIdentifier") (version 3.0; acl "Enable self write for common attributes"; allow (read,compare,search,write)(userdn = "ldap:///self");)')
    else:
        aci.append('(targetattr = "carLicense || description || displayName || facsimileTelephoneNumber || homePhone || homePostalAddress || initials || jpegPhoto || l || labeledURI || mobile || o || pager || photo || postOfficeBox || postalAddress || postalCode || preferredDeliveryMethod || preferredLanguage || registeredAddress || roomNumber || secretary || seeAlso || st || street || telephoneNumber || telexNumber || title || userCertificate || userPassword || userSMIMECertificate || x500UniqueIdentifier || kolabDelegate || kolabInvitationPolicy || kolabAllowSMTPSender") (version 3.0; acl "Enable self write for common attributes"; allow (read,compare,search,write)(userdn = "ldap:///self");)')

    aci.append('(targetattr = "*") (version 3.0;acl "Directory Administrators Group";allow (all)(groupdn = "ldap:///cn=Directory Administrators,%(rootdn)s" or roledn = "ldap:///cn=kolab-admin,%(rootdn)s");)' % (_input))
    aci.append('(targetattr="*")(version 3.0; acl "Configuration Administrators Group"; allow (all) groupdn="ldap:///cn=Configuration Administrators,ou=Groups,ou=TopologyManagement,o=NetscapeRoot";)')
    aci.append('(targetattr="*")(version 3.0; acl "Configuration Administrator"; allow (all) userdn="ldap:///uid=admin,ou=Administrators,ou=TopologyManagement,o=NetscapeRoot";)')
    aci.append('(targetattr = "*")(version 3.0; acl "SIE Group"; allow (all) groupdn = "ldap:///cn=slapd-%(hostname)s,cn=389 Directory Server,cn=Server Group,cn=%(fqdn)s,ou=%(domain)s,o=NetscapeRoot";)' % (_input))
    aci.append('(targetattr != "userPassword") (version 3.0;acl "Search Access";allow (read,compare,search)(userdn = "ldap:///all");)')
    modlist = []
    modlist.append((ldap.MOD_REPLACE, "aci", aci))
    auth._auth.ldap.modify_s(dn, modlist)

    if os.path.isfile('/bin/systemctl'):
        if not os.path.isfile('/usr/lib/systemd/system/dirsrv-admin.service'):
            log.info(_("directory server admin service not available"))
        else:
            subprocess.call(['/bin/systemctl', 'enable', 'dirsrv-admin.service'])
    elif os.path.isfile('/sbin/chkconfig'):
        subprocess.call(['/sbin/chkconfig', 'dirsrv-admin', 'on'])
    elif os.path.isfile('/usr/sbin/update-rc.d'):
        subprocess.call(['/usr/sbin/update-rc.d', 'dirsrv-admin', 'defaults'])
    else:
        log.error(_("Could not start and configure to start on boot, the " + \
                "directory server admin service."))
