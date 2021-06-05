# -*- coding: utf-8 -*-
# Copyright 2014 Kolab Systems AG (http://www.kolabsys.com)
#
# Thomas Bruederli (Kolab Systems) <bruederli(a)kolabsys.com>
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
import pykolab
import subprocess

from pykolab.translate import _

log = pykolab.getLogger('pykolab.plugins.roundcubedb')
conf = pykolab.getConf()

class KolabRoundcubedb(object):
    """
        Pykolab plugin to update Roundcube's database on Kolab users db changes
    """

    def __init__(self):
        pass

    def add_options(self, *args,  **kw):
        pass

    def user_delete(self, *args, **kw):
        """
            The arguments passed to the 'user_delete' hook:

            user - full user entry from LDAP
            domain - domain name
        """

        log.debug(_("user_delete: %r") % (kw), level=8)

        if os.path.isdir('/usr/share/roundcubemail'):
            rcpath = '/usr/share/roundcubemail/'
        elif os.path.isdir('/usr/share/roundcube'):
            rcpath = '/usr/share/roundcube/'
        else:
            log.error(_("Roundcube installation path not found."))
            return False

        result_attribute = conf.get('cyrus-sasl', 'result_attribute')

        # execute Roundcube's bin/deluser.sh script to do the work
        if 'user' in kw and result_attribute in kw['user'] and os.path.exists(rcpath + 'bin/deluser.sh'):
            proc = subprocess.Popen([ 'sudo -u apache', rcpath + 'bin/deluser.sh', kw['user'][result_attribute] ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            procout, procerr = proc.communicate()
            if proc.returncode != 0:
                log.error(rcpath + "bin/deluser.sh exited with error %d: %r" % (proc.returncode, procerr))
            else:
                log.debug(rcpath + "bin/deluser.sh success: %r; %r" % (procout, procerr), level=8)

        return None
