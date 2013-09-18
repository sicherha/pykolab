# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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

from ConfigParser import RawConfigParser
import os
import sys
import time

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

    freebusy_settings = {
            'directory "kolab-ldap"': {
                    'host': conf.get('ldap', 'ldap_uri'),
                    'base_dn': conf.get('ldap', 'base_dn'),
                    'bind_dn': conf.get('ldap', 'service_bind_dn'),
                    'bind_pw': conf.get('ldap', 'service_bind_pw'),
                    'fbsource': 'file:/var/lib/kolab-freebusy/%mail.ifb',
                },
            'httpauth': {
                }
        }

    cfg_parser = RawConfigParser()
    cfg_parser.read('/etc/kolab-freebusy/config.ini')

    for section in freebusy_settings.keys():
        if len(freebusy_settings[section].keys()) < 1:
            cfg_parser.remove_section(section)
            continue

        for key in freebusy_settings[section].keys():
            cfg_parser.set(section, key, freebusy_settings[section][key])

    fp = open('/etc/kolab-freebusy/config.ini', "w+")
    cfg_parser.write(fp)
    fp.close()

