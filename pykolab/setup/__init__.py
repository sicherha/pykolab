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
from pykolab.translate import _

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
                if sys.argv[arg_num].replace('-','_') in components.components:
                    to_execute.append(sys.argv[arg_num].replace('-','_'))

    def run(self):
        if os.path.isfile('/sys/fs/selinux/enforce'):
            if os.access('/sys/fs/selinux/enforce', os.R_OK):
                # Set a gentle default because strictly speaking,
                # setup won't fail (run-time does)
                enforce = "0"

                with open('/sys/fs/selinux/enforce', 'r') as f:
                    enforce = f.read()

                if enforce.strip() == "1":
                    log.fatal(
                            _("SELinux currently enforcing. Read " + \
                            "https://git.kolab.org/u/1")
                        )

                    sys.exit(1)

        if os.path.isfile('/etc/selinux/config'):
            if os.access('/etc/selinux/config', os.R_OK):
                with open('/etc/selinux/config', 'r') as f:
                    for line in f:
                        if line.strip() == "SELINUX=enforcing":
                            log.fatal(
                                    _("SELinux configured to enforce a " + \
                                    "policy on startup. Read " + \
                                    "https://git.kolab.org/u/1")
                                )

                            sys.exit(1)

        components.execute('_'.join(to_execute))

        if os.path.exists('/tmp/kolab-setup-my.cnf'):
            os.unlink('/tmp/kolab-setup-my.cnf')

