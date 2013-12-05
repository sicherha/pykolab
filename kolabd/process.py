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

import multiprocessing
import os
import time

import pykolab
from pykolab.auth import Auth
from pykolab.translate import _

log = pykolab.getLogger('pykolab.daemon')
conf = pykolab.getConf()

class KolabdProcess(multiprocessing.Process):
    def __init__(self, domain):
        self.domain = domain
        log.debug(_("Process created for domain %s") % (domain), level=8)
        multiprocessing.Process.__init__(
                self,
                target=self.synchronize,
                args=(domain,),
                name="Kolab(%s)" % domain
            )

    def synchronize(self, domain):
        log.debug(_("Synchronizing for domain %s") % (domain), level=8)
        sync_interval = conf.get('kolab', 'sync_interval')

        if sync_interval == None or sync_interval == 0:
            sync_interval = 300
        else:
            sync_interval = (int)(sync_interval)

        while True:
            try:
                auth = Auth(domain)
                auth.connect(domain)
                auth.synchronize()
                time.sleep(sync_interval)
            except KeyboardInterrupt:
                break
            except Exception, errmsg:
                log.error(_("Error in process %r, terminating:\n\t%r") % (self.name, errmsg))
                import traceback
                traceback.print_exc()
                time.sleep(1)
