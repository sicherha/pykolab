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
from Cheetah.Template import Template
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
    components.register('mta', execute, description=description(), after=['ldap'])

def description():
    return _("Setup MTA.")

def execute(*args, **kw):

    group_filter = conf.get('ldap','kolab_group_filter')
    if group_filter == None:
        group_filter = conf.get('ldap','group_filter')

    user_filter = conf.get('ldap','kolab_user_filter')
    if user_filter == None:
        user_filter = conf.get('ldap','user_filter')

    files = {
            "/etc/postfix/ldap/local_recipient_maps.cf": """
server_host = localhost
server_port = 389
version = 3
search_base = %(base_dn)s
scope = sub

domain = ldap:/etc/postfix/ldap/mydestination.cf

bind_dn = %(service_bind_dn)s
bind_pw = %(service_bind_pw)s

query_filter = (&(|(mail=%%s)(alias=%%s))(|%(kolab_user_filter)s%(kolab_group_filter)s))
result_attribute = mail
""" % {
                        "base_dn": conf.get('ldap', 'base_dn'),
                        "service_bind_dn": conf.get('ldap', 'service_bind_dn'),
                        "service_bind_pw": conf.get('ldap', 'service_bind_pw'),
                        "kolab_user_filter": user_filter,
                        "kolab_group_filter": group_filter,
                    },
            "/etc/postfix/ldap/mydestination.cf": """
server_host = localhost
server_port = 389
version = 3
search_base = %(domain_base_dn)s
scope = sub

bind_dn = %(service_bind_dn)s
bind_pw = %(service_bind_pw)s

query_filter = %(domain_filter)s
result_attribute = %(domain_name_attribute)s
""" % {
                        "domain_base_dn": conf.get('ldap', 'domain_base_dn'),
                        "domain_filter": conf.get('ldap', 'domain_filter').replace('*', '%s'),
                        "domain_name_attribute": conf.get('ldap', 'domain_name_attribute'),
                        "service_bind_dn": conf.get('ldap', 'service_bind_dn'),
                        "service_bind_pw": conf.get('ldap', 'service_bind_pw'),
                    },
            "/etc/postfix/ldap/mailenabled_distgroups.cf": """
server_host = localhost
server_port = 389
version = 3
search_base = %(group_base_dn)s
scope = sub

domain = ldap:/etc/postfix/ldap/mydestination.cf

bind_dn = %(service_bind_dn)s
bind_pw = %(service_bind_pw)s

# This finds the mail enabled distribution group LDAP entry
query_filter = (&(mail=%%s)(objectClass=kolabgroupofuniquenames)(objectclass=groupofuniquenames))
# From this type of group, get all uniqueMember DNs
special_result_attribute = uniqueMember
# Only from those DNs, get the mail
result_attribute =
leaf_result_attribute = mail
""" % {
                        "group_base_dn": conf.get('ldap', 'group_base_dn'),
                        "service_bind_dn": conf.get('ldap', 'service_bind_dn'),
                        "service_bind_pw": conf.get('ldap', 'service_bind_pw'),
                    },
            "/etc/postfix/ldap/mailenabled_dynamic_distgroups.cf": """
server_host = localhost
server_port = 389
version = 3
search_base = %(group_base_dn)s
scope = sub

domain = ldap:/etc/postfix/ldap/mydestination.cf

bind_dn = %(service_bind_dn)s
bind_pw = %(service_bind_pw)s

# This finds the mail enabled dynamic distribution group LDAP entry
query_filter = (&(mail=%%s)(objectClass=kolabgroupofuniquenames)(objectClass=groupOfURLs))
# From this type of group, get all memberURL searches/references
special_result_attribute = memberURL
# Only from those DNs, get the mail
result_attribute =
leaf_result_attribute = mail
""" % {
                        "group_base_dn": conf.get('ldap', 'group_base_dn'),
                        "service_bind_dn": conf.get('ldap', 'service_bind_dn'),
                        "service_bind_pw": conf.get('ldap', 'service_bind_pw'),
                    },
            "/etc/postfix/ldap/transport_maps.cf": """
server_host = localhost
server_port = 389
version = 3
search_base = %(base_dn)s
scope = sub

domain = ldap:/etc/postfix/ldap/mydestination.cf

bind_dn = %(service_bind_dn)s
bind_pw = %(service_bind_pw)s

query_filter = (&(|(mailAlternateAddress=%%s)(alias=%%s)(mail=%%s))(objectclass=kolabinetorgperson))
result_attribute = mail
result_format = lmtp:unix:/var/lib/imap/socket/lmtp
""" % {
                        "base_dn": conf.get('ldap', 'base_dn'),
                        "service_bind_dn": conf.get('ldap', 'service_bind_dn'),
                        "service_bind_pw": conf.get('ldap', 'service_bind_pw'),
                    },
            "/etc/postfix/ldap/virtual_alias_maps.cf": """
server_host = localhost
server_port = 389
version = 3
search_base = %(base_dn)s
scope = sub

domain = ldap:/etc/postfix/ldap/mydestination.cf

bind_dn = %(service_bind_dn)s
bind_pw = %(service_bind_pw)s

search_filter = (&(|(mail=%%s)(alias=%%s))(objectclass=kolabinetorgperson))
result_attribute = mail
""" % {
                        "base_dn": conf.get('ldap', 'base_dn'),
                        "service_bind_dn": conf.get('ldap', 'service_bind_dn'),
                        "service_bind_pw": conf.get('ldap', 'service_bind_pw'),
                    },
        }

    if not os.path.isdir('/etc/postfix/ldap'):
        os.mkdir('/etc/postfix/ldap/', 0770)

    for filename in files.keys():
        fp = open(filename, 'w')
        fp.write(files[filename])
        fp.close()

    postfix_main_settings = {
            "inet_interfaces": "all",
            "local_recipient_maps": "ldap:/etc/postfix/ldap/local_recipient_maps.cf",
            "mydestination": "ldap:/etc/postfix/ldap/mydestination.cf",
            "transport_maps": "ldap:/etc/postfix/ldap/transport_maps.cf",
            "virtual_alias_maps": "$alias_maps, ldap:/etc/postfix/ldap/virtual_alias_maps.cf, ldap:/etc/postfix/ldap/mailenabled_distgroups.cf, ldap:/etc/postfix/ldap/mailenabled_dynamic_distgroups.cf",
            "smtpd_tls_auth_only": "yes",
            "smtpd_tls_cert_file": "/etc/pki/tls/private/localhost.pem",
            "smtpd_tls_key_file": "/etc/pki/tls/private/localhost.pem",
            "smtpd_recipient_restrictions": "permit_mynetworks, reject_unauth_pipelining, reject_rbl_client zen.spamhaus.org, reject_non_fqdn_recipient, reject_invalid_helo_hostname, reject_unknown_recipient_domain, reject_unauth_destination, check_policy_service unix:private/recipient_policy_incoming, permit",
            "smtpd_sender_restrictions": "permit_mynetworks, check_policy_service unix:private/sender_policy_incoming",
            "submission_recipient_restrictions": "check_policy_service unix:private/submission_policy, permit_sasl_authenticated, reject",
            "submission_sender_restrictions": "reject_non_fqdn_sender, check_policy_service unix:private/submission_policy, permit_sasl_authenticated, reject",
            "submission_data_restrictions": "check_policy_service unix:private/submission_policy",
            "content_filter": "smtp-amavis:[127.0.0.1]:10024"

        }

    myaugeas = Augeas()

    setting_base = '/files/etc/postfix/main.cf/'

    for setting_key in postfix_main_settings.keys():
        setting = os.path.join(setting_base,setting_key)
        current_value = myaugeas.get(setting)

        if current_value == None:
            insert_paths = myaugeas.match('/files/etc/postfix/main.cf/*')
            insert_path = insert_paths[(len(insert_paths)-1)]
            myaugeas.insert(insert_path, setting_key, False)

        log.debug(_("Setting key %r to %r") % (setting_key, postfix_main_settings[setting_key]), level=8)
        myaugeas.set(setting, postfix_main_settings[setting_key])

    myaugeas.save()

    postfix_master_settings = {
        }

    template_file = None

    if os.path.isfile('/etc/kolab/templates/master.cf.tpl'):
        template_file = '/etc/kolab/templates/master.cf.tpl'
    elif os.path.isfile('/usr/share/kolab/templates/master.cf.tpl'):
        template_file = '/usr/share/kolab/templates/master.cf.tpl'
    elif os.path.isfile(os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'master.cf.tpl'))):
        template_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'master.cf.tpl'))

    if not template_file == None:
        fp = open(template_file, 'r')
        template_definition = fp.read()
        fp.close()

        t = Template(template_definition, searchList=[postfix_master_settings])
        fp = open('/etc/postfix/master.cf', 'w')
        fp.write(t.__str__())
        fp.close()

    else:
        log.error(_("Could not write out Postfix configuration file /etc/postfix/master.cf"))
        return

    subprocess.call(['/etc/pki/tls/certs/make-dummy-cert', '/etc/pki/tls/private/localhost.pem'])

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['systemctl', 'restart', 'postfix.service'])
        subprocess.call(['systemctl', 'enable', 'postfix.service'])
        subprocess.call(['systemctl', 'restart', 'amavisd.service'])
        subprocess.call(['systemctl', 'enable', 'amavisd.service'])
        subprocess.call(['systemctl', 'restart', 'clamd.amavisd.service'])
        subprocess.call(['systemctl', 'enable', 'clamd.amavisd.service'])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['service', 'postfix', 'restart'])
        subprocess.call(['chkconfig', 'postfix', 'on'])
        subprocess.call(['service', 'amavisd', 'restart'])
        subprocess.call(['chkconfig', 'amavisd', 'on'])
        subprocess.call(['service', 'clamd.amavisd', 'restart'])
        subprocess.call(['chkconfig', 'clamd.amavisd', 'on'])
    else:
        log.error(_("Could not start and configure to start on boot, the " + \
                "postfix, clamav.amavisd and amavisd services."))

