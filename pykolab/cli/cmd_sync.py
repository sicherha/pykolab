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

import commands

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

auth = pykolab.auth
imap = pykolab.imap

def __init__():
    commands.register('sync', execute, description="Synchronize Kolab Users with IMAP.")

def execute(*args, **kw):
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

    for primary_domain,secondary_domains in domains:
        log.debug(_("Running for domain %s") % (primary_domain), level=8)
        auth.connect(primary_domain)
        start_time = time.time()
        auth.synchronize(primary_domain, secondary_domains)
        end_time = time.time()

        log.info(_("Synchronizing users for %s took %d seconds")
                % (primary_domain, (end_time-start_time))
            )

