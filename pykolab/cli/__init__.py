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

import ldap
import ldif
import logging
import traceback
import shutil
import sys
import time

from ldap.modlist import addModlist

import pykolab
import pykolab.plugins

from pykolab import utils
from pykolab import conf
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

class Cli(object):
    def __init__(self):
        import commands
        commands.__init__()

        to_execute = []

        arg_num = 0
        for arg in sys.argv[1:]:
            arg_num += 1
            if not arg.startswith('-') and len(sys.argv) >= arg_num:
                if commands.commands.has_key(sys.argv[arg_num].replace('-','_')):
                    to_execute.append(sys.argv[arg_num].replace('-','_'))
                    
                if commands.commands.has_key("%s_%s" % (
                        '_'.join(to_execute),sys.argv[arg_num].replace('-','_')
                    )):

                    to_execute.append(sys.argv[arg_num].replace('-','_'))

        for cmd_component in to_execute:
            sys.argv.pop(sys.argv.index(cmd_component))

        commands.execute('_'.join(to_execute))

    def run(self):
        pass
