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

    myaugeas = Augeas()

    setting_base = '/files/etc/php.ini/'

    setting = os.path.join(setting_base, 'Date', 'date.timezone')
    current_value = myaugeas.get(setting)

    if current_value == None:
        insert_paths = myaugeas.match('/files/etc/php.ini/Date/*')
        insert_path = insert_paths[(len(insert_paths)-1)]
        myaugeas.insert(insert_path, 'date.timezone', False)

    log.debug(_("Setting key %r to %r") % ('Date/date.timezone', conf.timezone), level=8)
    myaugeas.set(setting, conf.timezone)

    myaugeas.save()

