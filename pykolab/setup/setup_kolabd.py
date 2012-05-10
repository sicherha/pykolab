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
    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['systemctl', 'restart', 'kolabd.service'])
        subprocess.call(['systemctl', 'enable', 'kolabd.service'])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['service', 'kolabd', 'restart'])
        subprocess.call(['chkconfig', 'kolabd', 'on'])
