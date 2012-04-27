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

from augeas import Augeas
import os
import subprocess

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register('imap', execute, description=description(), after=['ldap'])

def description():
    return _("Setup IMAP.")

def execute(*args, **kw):
    """
        Apply the necessary settings to /etc/imapd.conf
    """

    imapd_settings = {
            "sasl_pwcheck_method": "auxprop saslauthd",
            "sasl_mech_list": "PLAIN LOGIN",
            "auth_mech": "pts",
            "pts_module": "ldap",
            "ldap_servers": conf.get('ldap', 'ldap_uri'),
            "ldap_sasl": "0",
            "ldap_base": conf.get('ldap', 'base_dn'),
            "ldap_bind_dn": conf.get('ldap', 'service_bind_dn'),
            "ldap_password": conf.get('ldap', 'service_bind_pw'),
            "ldap_filter": '(|(&(|(uid=%s)(uid=cyrus-murder))(uid=%%U))(&(|(uid=%%U)(mail=%%U@%%d)(mail=%%U@%%r))(objectclass=kolabinetorgperson)))' % (conf.get('cyrus-imap', 'admin_login')),
            "ldap_user_attribute": conf.get('cyrus-sasl', 'result_attribute'),
            "ldap_group_base": conf.get('ldap', 'base_dn'),
            "ldap_group_filter": "(&(cn=%u)(objectclass=ldapsubentry)(objectclass=nsroledefinition))",
            "ldap_group_scope": "one",
            "ldap_member_base": conf.get('ldap','user_base_dn'),
            "ldap_member_method": "attribute",
            "ldap_member_attribute": "nsrole",
            "ldap_restart": "1",
            "ldap_timeout": "10",
            "ldap_time_limit": "10",
            "unixhierarchysep": "1",
            "virt_domains": "userid",
            "admins": conf.get('cyrus-imap', 'admin_login'),
            "annotation_definitions": "/etc/imapd.annotations.conf",
            "sieve_extensions": "fileinto reject vacation imapflags notify envelope include relational regex subaddress copy",
            "allowallsubscribe": "0",
            "allowusermoves": "1",
            "altnamespace": "1",
            "hashimapspool": "1",
            "anysievefolder": "1",
            "fulldirhash": "0",
            "sieveusehomedir": "0",
            "sieve_allowreferrals": "0",
            "lmtp_downcase_rcpt": "1",
            "lmtp_fuzzy_mailbox_match": "1",
            "username_tolower": "1",
            #"normalizeuid": "1",
            "deletedprefix": "DELETED",
            "delete_mode": "delayed",
            "expunge_mode": "delayed",
            "flushseenstate": "1",
            "virtdomains": "userid",
        }

    myaugeas = Augeas()

    setting_base = '/files/etc/imapd.conf/'
    for setting_key in imapd_settings.keys():
        setting = os.path.join(setting_base,setting_key)
        current_value = myaugeas.get(setting)

        if current_value == None:
            insert_paths = myaugeas.match('/files/etc/imapd.conf/*')
            insert_path = insert_paths[(len(insert_paths)-1)]
            myaugeas.insert(insert_path, setting_key, False)

        log.debug(_("Setting key %r to %r") % (setting_key, imapd_settings[setting_key]), level=8)
        myaugeas.set(setting, imapd_settings[setting_key])

    myaugeas.save()

    annotations = [
            "/vendor/horde/share-params,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/color,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/folder-test,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/folder-type,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/incidences-for,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/pxfb-readable-for,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/h-share-attr-desc,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/activesync,mailbox,string,backend,value.priv,r",
            "/vendor/x-toltec/test,mailbox,string,backend,value.shared value.priv,a",
        ]

    fp = open('/etc/imapd.annotations.conf', 'w')
    fp.write("\n".join(annotations))
    fp.close()

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['systemctl', 'restart', 'cyrus-imapd.service'])
        subprocess.call(['systemctl', 'enable', 'cyrus-imapd.service'])
        subprocess.call(['systemctl', 'restart', 'kolab-saslauthd.service'])
        subprocess.call(['systemctl', 'enable', 'kolab-saslauthd.service'])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['service', 'cyrus-imapd', 'restart'])
        subprocess.call(['chkconfig', 'cyrus-imapd', 'on'])
        subprocess.call(['service', 'kolab-saslauthd', 'restart'])
        subprocess.call(['chkconfig', 'kolab-saslauthd', 'on'])
    else:
        log.error(_("Could not start and configure to start on boot, the " + \
                "cyrus-imapd and kolab-saslauthd services."))
