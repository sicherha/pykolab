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

from Cheetah.Template import Template
import os
import subprocess
import sys

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register('freebusy', execute, description=description(), after=['mysql','ldap', 'roundcube'])

def description():
    return _("Setup Free/Busy.")

def execute(*args, **kw):
    if not os.path.isfile('/etc/kolab/freebusy/config.php'):
        log.error(_("Free/Busy is not installed on this system"))
        return

    if not hasattr(conf, 'mysql_roundcube_password'):
        conf.mysql_roundcube_password = utils.ask_question(
                _("MySQL roundcube password"),
                password=True
            )

    horde_settings = {
            'ldap_base_dn': conf.get('ldap', 'base_dn'),
            'ldap_ldap_uri': conf.get('ldap', 'ldap_uri'),
            'ldap_service_bind_dn': conf.get('ldap', 'service_bind_dn'),
            'ldap_service_bind_pw': conf.get('ldap', 'service_bind_pw'),
            'primary_domain': conf.get('kolab', 'primary_domain'),
            'roundcube_mysql_password': conf.mysql_roundcube_password
        }

    want_files = [
            'config.php',
        ]

    for want_file in want_files:
        template_file = None
        if os.path.isfile('/etc/kolab/templates/freebusy/%s.tpl' % (want_file)):
            template_file = '/etc/kolab/templates/freebusy/%s.tpl' % (want_file)
        elif os.path.isfile('/usr/share/kolab/templates/freebusy/%s.tpl' % (want_file)):
            template_file = '/usr/share/kolab/templates/freebusy/%s.tpl' % (want_file)
        elif os.path.isfile(os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'freebusy', '%s.tpl' % (want_file)))):
            template_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'freebusy', '%s.tpl' % (want_file)))

        if not template_file == None:
            log.debug(_("Using template file %r") % (template_file), level=8)
            fp = open(template_file, 'r')
            template_definition = fp.read()
            fp.close()

            t = Template(template_definition, searchList=[freebusy_settings])
            log.debug(
                    _("Successfully compiled template %r, writing out to %r") % (
                            template_file,
                            '/etc/kolab/freebusy/%s' % (want_file)
                        ),
                    level=8
                )

            fp = open('/etc/kolab/freebusy/%s' % (want_file), 'w')
            fp.write(t.__str__())
            fp.close()

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'restart', 'httpd.service'])
        subprocess.call(['/bin/systemctl', 'enable', 'httpd.service'])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['/sbin/service', 'httpd', 'restart'])
        subprocess.call(['/sbin/chkconfig', 'httpd', 'on'])
    else:
        log.error(_("Could not start and configure to start on boot, the " + \
                "webserver service."))

