# -*- coding: utf-8 -*-
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

import commands

import time
import pykolab

from pykolab.auth import Auth
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('sync', execute, description="Synchronize Kolab Users with IMAP.")

def execute(*args, **kw):
    auth = Auth()
    log.debug(_("Listing domains..."), level=5)
    start_time = time.time()
    domains = auth.list_domains()
    end_time = time.time()
    log.debug(
            _("Found %d domains in %d seconds") % (
                    len(domains),
                    (end_time-start_time)
                ),
            level=8
        )

    all_folders = []

    for primary_domain in list(set(domains.values())):
        log.debug(_("Running for domain %s") % (primary_domain), level=8)
        auth = Auth(primary_domain)
        auth.connect(primary_domain)
        start_time = time.time()
        auth.synchronize(mode='_paged_search')
        end_time = time.time()

        log.info(_("Synchronizing users for %s took %d seconds")
                % (primary_domain, (end_time-start_time))
            )

