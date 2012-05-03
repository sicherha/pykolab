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
    components.register('roundcube', execute, description=description(), after=['mysql','ldap'])

def description():
    return _("Setup Roundcube.")

def execute(*args, **kw):
    rc_settings = {
            'imap_admin_login': conf.get('cyrus-imapd', 'admin_login'),
            'imap_admin_password': conf.get('cyrus-imapd', 'admin_password'),
            'ldap_base_dn': conf.get('ldap', 'base_dn'),
            'ldap_group_base_dn': conf.get('ldap', 'group_base_dn'),
            'ldap_group_filter': conf.get('ldap', 'group_filter'),
            'ldap_ldap_uri': conf.get('ldap', 'ldap_uri'),
            'ldap_service_bind_dn': conf.get('ldap', 'service_bind_dn'),
            'ldap_service_bind_pw': conf.get('ldap', 'service_bind_pw'),
            'ldap_user_base_dn': conf.get('ldap', 'user_base_dn'),
            'ldap_user_filter': conf.get('ldap', 'user_filter'),
            'mysql_uri': 'mysqli://root@localhost/roundcube',
        }


    want_files = [
            'acl.inc.php',
            'calendar.inc.php',
            'compose_addressbook.inc.php',
            'db.inc.php',
            'kolab_auth.inc.php',
            'kolab_folders.inc.php',
            'kolab.inc.php',
            'main.inc.php',
            'managesieve.inc.php',
            'owncloud.inc.php',
            'password.inc.php',
            'recipient_to_contact.inc.php',
            'terms.html',
            'terms.inc.php'
        ]

    for want_file in want_files:
        template_file = None

        print "Going for", want_file

        if os.path.isfile('/etc/kolab/templates/roundcubemail/%s.tpl' % (want_file)):
            template_file = '/etc/kolab/templates/roundcubemail/%s.tpl' % (want_file)
        elif os.path.isfile('/usr/share/kolab/templates/roundcubemail/%s.tpl' % (want_file)):
            template_file = '/usr/share/kolab/templates/roundcubemail/%s.tpl' % (want_file)
        elif os.path.isfile(os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'roundcubemail', '%s.tpl' % (want_file)))):
            template_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'roundcubemail', '%s.tpl' % (want_file)))

        if not template_file == None:
            fp = open(template_file, 'r')
            template_definition = fp.read()
            fp.close()

            t = Template(template_definition, searchList=[rc_settings])
            fp = open('/etc/roundcubemail/%s' % (want_file), 'w')
            fp.write(t.__str__())
            fp.close()

    schema_files = []
    for root, directories, filenames in os.walk('/usr/share/doc/'):
        for filename in filenames:
            if filename.startswith('mysql.initial') and filename.endswith('.sql'):
                schema_files.append(os.path.join(root,filename))

    for root, directories, filenames in os.walk('/usr/share/roundcubemail/plugins/calendar/drivers/kolab/'):
        for filename in filenames:
            if filename.startswith('mysql') and filename.endswith('.sql'):
                schema_files.append(os.path.join(root,filename))

    subprocess.call(['service', 'mysqld', 'start'])
    p1 = subprocess.Popen(['echo', 'create database roundcube;'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['mysql'], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    for schema_file in schema_files:
        p1 = subprocess.Popen(['cat', schema_file], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql', 'roundcube'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

