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

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register(
            'kolabd',
            execute,
            description=description(),
            after=['ldap','imap']
        )

def description():
    return _("Setup the Kolab daemon.")

def execute(*args, **kw):
    if conf.has_section('example.org'):
        primary_domain = conf.get('kolab', 'primary_domain')

        if not primary_domain == 'example.org':
            utils.multiline_message(
                    _("""
                            Copying the configuration section for 'example.org' over to
                            a section applicable to your domain '%s'.
                        """) % (primary_domain)
                )

            conf.cfg_parser._sections[primary_domain] = \
                    conf.cfg_parser._sections['example.org']
            conf.cfg_parser._sections.pop('example.org')

            fp = open(conf.cli_keywords.config_file, "w+")
            conf.cfg_parser.write(fp)
            fp.close()

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'restart', 'kolabd.service'])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['/sbin/service', 'kolabd', 'restart'])
    elif os.path.isfile('/usr/sbin/service'):
        subprocess.call(['/usr/sbin/service','kolab-server','restart'])
    else:
        log.error(_("Could not start the kolab server service."))

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'enable', 'kolabd.service'])
    elif os.path.isfile('/sbin/chkconfig'):
        subprocess.call(['/sbin/chkconfig', 'kolabd', 'on'])
    elif os.path.isfile('/usr/sbin/update-rc.d'):
        subprocess.call(['/usr/sbin/update-rc.d', 'kolab-server', 'defaults'])
    else:
        log.error(_("Could not configure to start on boot, the " + \
                "kolab server service."))
