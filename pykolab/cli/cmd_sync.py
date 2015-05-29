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

import commands

from distutils import version
import multiprocessing

import sys
import time

import pykolab

from pykolab import utils
from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

imap = None
pool = None

def __init__():
    commands.register('sync', execute, description="Synchronize Kolab Users with IMAP.")

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option(
            '--threads',
            dest    = "threads",
            action  = "store",
            default = 20,
            type    = int,
            help    = _("Synchronize LDAP and IMAP")
        )

    my_option_group.add_option(
            '--resync',
            dest    = "resync",
            action  = "store_true",
            default = False,
            help    = _("Resync from the beginning")
        )

def execute(*args, **kw):
    global imap, pool

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

    if version.StrictVersion(sys.version[:3]) >= version.StrictVersion("2.7"):
        pool = multiprocessing.Pool(conf.threads, worker_process, (), 1)
    else:
        pool = multiprocessing.Pool(conf.threads, worker_process, ())

    for primary_domain in list(set(domains.values())):
        log.debug(_("Running for domain %s") % (primary_domain), level=8)
        auth = Auth(primary_domain)
        auth.connect(primary_domain)
        start_time = time.time()
        auth.synchronize(mode='_paged_search', callback=queue_add)
        end_time = time.time()

        log.info(_("Synchronizing users for %s took %d seconds")
                % (primary_domain, (end_time-start_time))
            )

    while not pool._taskqueue.empty():
        time.sleep(1)

def queue_add(*args, **kw):
    global pool
    for dn, entry in kw['entry']:
        entry['dn'] = dn
        r = pool.apply_async(_synchronize, (), dict(**entry))
        r.wait()

def worker_process(*args, **kw):
    pass

def _synchronize(*args, **kw):
    log.info(_("Worker process %s handling %s") % (multiprocessing.current_process().name, kw['dn']))

    entry = utils.normalize(kw)

    if not entry.has_key('mail'):
        return

    if not 'kolabinetorgperson' in entry['objectclass']:
        return

    imap = IMAP()
    imap.connect()

    if not imap.user_mailbox_exists(entry['mail']):
        if entry.has_key('mailhost'):
            server = entry['mailhost']
        else:
            server = None

        imap.user_mailbox_create(entry['mail'], server=server)

    imap.disconnect()

