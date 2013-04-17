# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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
        multiprocessing.Process.__init__(
                self,
                target=self.synchronize,
                args=(domain,),
                name="Kolab(%s)" % domain
            )

    def synchronize(self, domain):
        while True:
            try:
                auth = Auth(domain)
                auth.connect(domain)
                auth.synchronize()
            except KeyboardInterrupt:
                break
            except Exception, errmsg:
                log.error(_("Error in process %r, terminating:\n\t%r") % (self.name, errmsg))
                import traceback
                traceback.print_exc()
                time.sleep(1)
