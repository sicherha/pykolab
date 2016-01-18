# -*- coding: utf-8 -*-
# Copyright 2010-2016 Kolab Systems AG (http://www.kolabsys.com)
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

from Cheetah.Template import Template
import hashlib
import os
import random
import re
import subprocess
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
    components.register('manticore', execute, description=description(), after=['ldap','roundcube'])

def description():
    return _("Setup Manticore.")

def execute(*args, **kw):
    if not os.path.isfile('/etc/manticore/local.env.js'):
        log.error(_("Manticore is not installed on this system"))
        return

    manticore_settings = {
            'fqdn': hostname + '.' + domainname,
            'secret': re.sub(
                    r'[^a-zA-Z0-9]',
                    "",
                    "%s%s" % (
                            hashlib.md5("%s" % random.random()).digest().encode("base64"),
                            hashlib.md5("%s" % random.random()).digest().encode("base64")
                        )
                )[:24],
            'server_host': utils.parse_ldap_uri(conf.get('ldap', 'ldap_uri'))[1],
            'auth_key': re.sub(
                    r'[^a-zA-Z0-9]',
                    "",
                    "%s%s" % (
                            hashlib.md5("%s" % random.random()).digest().encode("base64"),
                            hashlib.md5("%s" % random.random()).digest().encode("base64")
                        )
                )[:24],
            'service_bind_dn': conf.get('ldap', 'service_bind_dn'),
            'service_bind_pw': conf.get('ldap', 'service_bind_pw'),
            'user_base_dn': conf.get('ldap', 'user_base_dn')
        }

    if os.path.isfile('/etc/kolab/templates/manticore.js.tpl'):
        fp = open('/etc/kolab/templates/manticore.js.tpl','r')
    else:
        fp = open('/usr/share/kolab/templates/manticore.js.tpl', 'r')

    template_definition = fp.read()
    fp.close()

    t = Template(template_definition, searchList=[manticore_settings])

    fp = open('/etc/manticore/local.env.js', 'w')
    fp.write(t.__str__())
    fp.close()

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'restart', 'mongod'])
        time.sleep(5)
        subprocess.call(['/bin/systemctl', 'restart', 'manticore'])
    else:
        log.error(_("Could not start the manticore service."))

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'enable', 'mongod'])
        subprocess.call(['/bin/systemctl', 'enable', 'manticore'])
    else:
        log.error(_("Could not configure the manticore service to start on boot"))

