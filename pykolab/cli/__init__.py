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

import ldap
import ldif
import logging
import traceback
import shutil
import sys
import time
import codecs
import locale

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
            sys.argv.pop(sys.argv.index(cmd_component.replace('_','-')))

        # force default encoding to match the locale encoding (T249)
        reload(sys)
        sys.setdefaultencoding(locale.getpreferredencoding() or 'utf-8')

        # wrap sys.stdout in a locale-aware StreamWriter (#3983)
        sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

        commands.execute('_'.join(to_execute))

    def run(self):
        pass
