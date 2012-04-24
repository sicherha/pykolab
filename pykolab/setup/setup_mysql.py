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
    components.register('mysql', execute, description=description())

def description():
    return _("Setup MySQL.")

def execute(*args, **kw):
    schema_file = None
    for root, directories, filenames in os.walk('/usr/share/doc/'):
        for filename in filenames:
            if filename.startswith('kolab_wap') and filename.endswith('.sql'):
                schema_file = os.path.join(root,filename)

    if not schema_file == None:
        subprocess.call(['service', 'mysqld', 'start'])
        p1 = subprocess.Popen(['echo', 'create database kolab;'], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

        p1 = subprocess.Popen(['cat', schema_file], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql', 'kolab'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()
    else:
        log.warning(_("Could not find the Kolab schema file"))

