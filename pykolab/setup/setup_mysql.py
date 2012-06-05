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

import os
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
    components.register('mysql', execute, description=description())

def description():
    return _("Setup MySQL.")

def execute(*args, **kw):
    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'start', 'mysqld.service'])
        subprocess.call(['/bin/systemctl', 'enable', 'mysqld.service'])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['/sbin/service', 'mysqld', 'start'])
        subprocess.call(['/sbin/chkconfig', 'mysqld', 'on'])
    else:
        log.error(_("Could not start and configure to start on boot, the " + \
                "MySQL database service."))

    print >> sys.stderr, utils.multiline_message(
            _("""
                    Please supply a root password for MySQL. This password will
                    be the administrative user for this MySQL server, and it
                    should be kept a secret. After this setup process has
                    completed, Kolab is going to discard and forget about this
                    password, but you will need it for administrative tasks in
                    MySQL.
                """)
        )

    mysql_root_password = utils.ask_question(
            _("MySQL root password"),
            default=utils.generate_password(),
            password=True,
            confirm=True
        )

    p1 = subprocess.Popen(['echo', 'UPDATE mysql.user SET Password=PASSWORD(\'%s\') WHERE User=\'root\';' % (mysql_root_password)], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['mysql'], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    p1 = subprocess.Popen(['echo', 'FLUSH PRIVILEGES;'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['mysql'], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    data = """
[mysql]
user=root
password='%s'
""" % (mysql_root_password)

    fp = open('/tmp/kolab-setup-my.cnf', 'w')
    fp.write(data)
    fp.close()

    schema_file = None
    for root, directories, filenames in os.walk('/usr/share/doc/'):
        for filename in filenames:
            if filename.startswith('kolab_wap') and filename.endswith('.sql'):
                schema_file = os.path.join(root,filename)

    if not schema_file == None:
        p1 = subprocess.Popen(['echo', 'create database kolab;'], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply a password for the MySQL user 'kolab'.
                        This password will be used by Kolab services, such as
                        the Web Administration Panel.
                    """)
            )

        mysql_kolab_password = utils.ask_question(
                _("MySQL kolab password"),
                default=utils.generate_password(),
                password=True,
                confirm=True
            )

        p1 = subprocess.Popen(['echo', 'GRANT ALL PRIVILEGES ON kolab.* TO \'kolab\'@\'localhost\' IDENTIFIED BY \'%s\';' % (mysql_kolab_password)], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

        p1 = subprocess.Popen(['cat', schema_file], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf', 'kolab'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

        conf.command_set('kolab_wap', 'sql_uri', 'mysql://kolab:%s@localhost/kolab' % (mysql_kolab_password))
    else:
        log.warning(_("Could not find the Kolab schema file"))

