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
import sys

import pykolab

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

to_execute = []

class Setup(object):
    def __init__(self):
        import components
        components.__init__()

        arg_num = 0
        for arg in sys.argv[1:]:
            arg_num += 1
            if not arg.startswith('-') and len(sys.argv) >= arg_num:
                if components.components.has_key(sys.argv[arg_num].replace('-','_')):
                    to_execute.append(sys.argv[arg_num].replace('-','_'))

    def run(self):
        components.execute('_'.join(to_execute))

        if os.path.exists('/tmp/kolab-setup-my.cnf'):
            os.unlink('/tmp/kolab-setup-my.cnf')

