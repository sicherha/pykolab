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

from augeas import Augeas
import os
import shutil
import subprocess
import tempfile

import components

import pykolab

from pykolab import utils
from pykolab.auth import Auth
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register('php', execute, description=description())

def cli_options():
    php_group = conf.add_cli_parser_option_group(_("PHP Options"))

    php_group.add_option(
            "--timezone",
            dest    = "timezone",
            action  = "store",
            default = None,
            help    = _("Specify the timezone for PHP.")
        )

    php_group.add_option(
            "--with-php-ini",
            dest    = "php_ini_path",
            action  = "store",
            default = None,
            help    = _("Specify the path to the php.ini file used with the webserver.")
        )

def description():
    return _("Setup PHP.")

def execute(*args, **kw):
    if conf.timezone == None:
        print >> sys.stderr, utils.multiline_message(
                _("""
                        Please supply the timezone PHP should be using.
                        You have to use a Continent or Country / City locality name
                        like 'Europe/Berlin', but not just 'CEST'.
                    """)
            )

        conf.timezone = utils.ask_question(
                _("Timezone ID"),
                default="UTC"
            )

    if not conf.php_ini_path == None:
        if not os.path.isfile(conf.php_ini_path):
            log.error(_("Cannot configure PHP through %r (No such file or directory)") % (conf.php_ini_path))
            return
        php_ini = conf.php_ini_path

    else:
        # Search and destroy
        php_ini = "/etc/php.ini"

        if not os.path.isfile(php_ini):
            php_ini = "/etc/php/7.2/apache2/php.ini"

        if not os.path.isfile(php_ini):
            php_ini = "/etc/php/7.0/apache2/php.ini"

        if not os.path.isfile(php_ini):
            php_ini = "/etc/php5/apache2/php.ini"

        if not os.path.isfile(php_ini):
            log.error(_("Could not find PHP configuration file php.ini"))
            return

    myaugeas = Augeas()

    setting_base = '/files%s/' % (php_ini)

    setting = os.path.join(setting_base, 'Date', 'date.timezone')
    current_value = myaugeas.get(setting)

    if current_value == None:
        insert_paths = myaugeas.match('/files%s/Date/*' % (php_ini))
        insert_path = insert_paths[(len(insert_paths)-1)]
        myaugeas.insert(insert_path, 'date.timezone', False)

    log.debug(_("Setting key %r to %r") % ('Date/date.timezone', conf.timezone), level=8)
    myaugeas.set(setting, conf.timezone)

    myaugeas.save()

