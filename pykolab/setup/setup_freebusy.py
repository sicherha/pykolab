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

from ConfigParser import RawConfigParser
import os
import sys
import time
from urlparse import urlparse

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register(
            'freebusy',
            execute,
            description=description(),
            after=['ldap']
        )

def description():
    return _("Setup Free/Busy.")

def execute(*args, **kw):
    if not os.path.isfile('/etc/kolab-freebusy/config.ini') and not os.path.isfile('/etc/kolab-freebusy/config.ini.sample'):
        log.error(_("Free/Busy is not installed on this system"))
        return

    if not os.path.isfile('/etc/kolab-freebusy/config.ini'):
        os.rename('/etc/kolab-freebusy/config.ini.sample', '/etc/kolab-freebusy/config.ini')

    imap_backend = conf.get('kolab', 'imap_backend')
    admin_login = conf.get(imap_backend, 'admin_login')
    admin_password = conf.get(imap_backend, 'admin_password')
    imap_uri = conf.get(imap_backend, 'imap_uri')
    if imap_uri == None:
        imap_uri = conf.get(imap_backend, 'uri')

    scheme = None
    hostname = None
    port = None

    result = urlparse(imap_uri)

    if hasattr(result, 'hostname'):
        hostname = result.hostname
    else:
        scheme = imap_uri.split(':')[0]
        (hostname, port) = imap_uri.split('/')[2].split(':')

    if port == None:
        port = 993

    if scheme == None or scheme == "":
        scheme = 'imaps'

    if scheme == "imaps" and port == 993:
        scheme = "imap"
        port = 143

    resources_imap_uri = '%s://%s:%s@%s:%s/%%kolabtargetfolder?acl=lrs' % (scheme, admin_login, admin_password, hostname, port)
    users_imap_uri = '%s://%%s:%s@%s:%s/?proxy_auth=%s' % (scheme, admin_password, hostname, port, admin_login)

    freebusy_settings = {
            'directory "local"': {
                    'type': 'static',
                    'fbsource': 'file:/var/lib/kolab-freebusy/%s.ifb',
                },
            'directory "local-cache"': {
                    'type': 'static',
                    'fbsource': 'file:/var/cache/kolab-freebusy/%s.ifb',
                    'expires': '15m'
                },
            'directory "kolab-people"': {
                    'type': 'ldap',
                    'host': conf.get('ldap', 'ldap_uri'),
                    'base_dn': conf.get('ldap', 'base_dn'),
                    'bind_dn': conf.get('ldap', 'service_bind_dn'),
                    'bind_pw': conf.get('ldap', 'service_bind_pw'),
                    'filter': '(&(objectClass=kolabInetOrgPerson)(|(mail=%s)(alias=%s)))',
                    'attributes': 'mail',
                    'lc_attributes': 'mail',
                    'primary_domain': conf.get('kolab', 'primary_domain'),
                    'fbsource': users_imap_uri,
                    'cacheto': '/var/cache/kolab-freebusy/%s.ifb',
                    'expires': '15m',
                    'loglevel': 300,
                },
            'directory "kolab-resources"': {
                    'type': 'ldap',
                    'host': conf.get('ldap', 'ldap_uri'),
                    'base_dn': conf.get('ldap', 'resource_base_dn'),
                    'bind_dn': conf.get('ldap', 'service_bind_dn'),
                    'bind_pw': conf.get('ldap', 'service_bind_pw'),
                    'attributes': 'mail, kolabtargetfolder',
                    'filter': '(&(objectClass=kolabsharedfolder)(kolabfoldertype=event)(mail=%s))',
                    'primary_domain': conf.get('kolab', 'primary_domain'),
                    'fbsource': resources_imap_uri,
                    'cacheto': '/var/cache/kolab-freebusy/%s.ifb',
                    'expires': '15m',
                    'loglevel': 300,
                },
            'directory "kolab-resource-collections"': {
                    'type': 'ldap',
                    'host': conf.get('ldap', 'ldap_uri'),
                    'base_dn': conf.get('ldap', 'resource_base_dn'),
                    'bind_dn': conf.get('ldap', 'service_bind_dn'),
                    'bind_pw': conf.get('ldap', 'service_bind_pw'),
                    'filter': '(&(objectClass=kolabgroupofuniquenames)(mail=%s))',
                    'attributes': 'uniquemember', 'mail'
                    'resolve_dn': 'uniquemember',
                    'resolve_attribute': 'mail',
                    'primary_domain': conf.get('kolab', 'primary_domain'),
                    'fbsource': 'aggregate://%uniquemember'
                    'directories': 'kolab-resources',
                    'cacheto': '/var/cache/kolab-freebusy/%mail.ifb',
                    'expires': '15m',
                    'loglevel': 200,
                },
        }

    cfg_parser = RawConfigParser()
    cfg_parser.read('/etc/kolab-freebusy/config.ini')

    for section in freebusy_settings.keys():
        if len(freebusy_settings[section].keys()) < 1:
            cfg_parser.remove_section(section)
            continue

        for key in freebusy_settings[section].keys():
            if not cfg_parser.has_section(section):
                cfg_parser.add_section(section)

            cfg_parser.set(section, key, freebusy_settings[section][key])

    fp = open('/etc/kolab-freebusy/config.ini', "w+")
    cfg_parser.write(fp)
    fp.close()

