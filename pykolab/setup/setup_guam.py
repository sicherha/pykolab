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

import os
import shutil
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
    components.register('guam', execute, description=description())

def description():
    return _("Setup Guam.")

def execute(*args, **kw):
    if not os.path.isfile('/etc/guam/sys.config'):
        log.error(_("Guam is not installed on this system"))
        return

    if os.path.isfile('/etc/kolab/templates/guam.sys.config.tpl'):
        template = '/etc/kolab/templates/guam.sys.config.tpl'
    else:
        template = '/usr/share/kolab/templates/guam.sys.config.tpl'

    shutil.copyfile(template, '/etc/guam/sys.config')

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'restart', 'guam'])
    else:
        log.error(_("Could not start the guam service."))

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'enable', 'guam'])
    else:
        log.error(_("Could not configure the guam service to start on boot"))

