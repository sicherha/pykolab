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

import os
import subprocess
import tempfile
import time

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register('mysql', execute, description=description())

def cli_options():
    ldap_group = conf.add_cli_parser_option_group(_("MySQL Options"))

    ldap_group.add_option(
            "--mysqlserver",
            dest    = "mysqlserver",
            action  = "store",
            help    = _("Specify whether to use an (existing) or (new) MySQL server.")
        )

def description():
    return _("Setup MySQL.")

def execute(*args, **kw):

    socket_paths = [
            "/var/lib/mysql/mysql.sock",
            "/var/run/mysqld/mysqld.sock",
            "/var/run/mysql/mysql.sock",
            "/var/run/mysqld/mysqld.pid"
        ]

    # on CentOS7, there is MariaDB instead of MySQL
    mysqlservice = 'mysqld.service'
    if os.path.isfile('/usr/lib/systemd/system/mariadb.service'):
        mysqlservice = 'mariadb.service'
    if os.path.isfile('/bin/systemctl') and not os.path.isfile('/usr/lib/systemd/system/' + mysqlservice):
        # on Debian Jessie, systemctl restart mysql
        mysqlservice = 'mysql'

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'restart', mysqlservice])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['/sbin/service', 'mysqld', 'restart'])
    elif os.path.isfile('/usr/sbin/service'):
        subprocess.call(['/usr/sbin/service','mysql','restart'])
    else:
        log.error(_("Could not start the MySQL database service."))

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'enable', mysqlservice])
    elif os.path.isfile('/sbin/chkconfig'):
        subprocess.call(['/sbin/chkconfig', 'mysqld', 'on'])
    elif os.path.isfile('/usr/sbin/update-rc.d'):
        subprocess.call(['/usr/sbin/update-rc.d', 'mysql', 'defaults'])
    else:
        log.error(_("Could not configure to start on boot, the " + \
                "MySQL database service."))

    log.info(_("Waiting for at most 30 seconds for MySQL/MariaDB to settle..."))
    max_wait = 30
    while max_wait > 0:
        for socket_path in socket_paths:
            if os.path.exists(socket_path):
                max_wait = 0

        if max_wait > 0:
            max_wait = max_wait - 1
            time.sleep(1)

    options = {
            1: "Existing MySQL server (with root password already set).",
            2: "New MySQL server (needs to be initialized)."
        }

    answer = 0
    if len([x for x in socket_paths if os.path.exists(x)]) > 0:
        if conf.mysqlserver:
            if conf.mysqlserver == 'existing':
                answer = 1
            elif conf.mysqlserver == 'new':
                answer = 2
        if answer == 0:
            answer = utils.ask_menu(_("What MySQL server are we setting up?"), options)

    if answer == "1" or answer == 1:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply the root password for MySQL, so we can set
                        up user accounts for other components that use MySQL.
                    """)
            )

        mysql_root_password = utils.ask_question(
                _("MySQL root password"),
                password=True
            )

    else:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply a root password for MySQL. This password
                        will be the administrative user for this MySQL server,
                        and it should be kept a secret. After this setup process
                        has completed, Kolab is going to discard and forget
                        about this password, but you will need it for
                        administrative tasks in MySQL.
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
    os.chmod('/tmp/kolab-setup-my.cnf', 0600)
    fp.write(data)
    fp.close()

    schema_file = None
    for root, directories, filenames in os.walk('/usr/share/doc/'):
        for filename in filenames:
            if filename.startswith('kolab_wap') and filename.endswith('.sql'):
                # Skip the Oracle file
                if filename.endswith('oracle.sql'):
                    continue

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
        conf.command_set('kolab_smtp_access_policy', 'cache_uri', 'mysql://kolab:%s@localhost/kolab' % (mysql_kolab_password))
    else:
        log.warning(_("Could not find the MySQL Kolab schema file"))

