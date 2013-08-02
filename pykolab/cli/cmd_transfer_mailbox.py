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

import pykolab

from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('transfer_mailbox', execute, description="Transfer a mailbox to another server.")

def execute(*args, **kw):
    """
        Transfer mailbox
    """

    if len(conf.cli_args) > 1:
        mailfolder = conf.cli_args.pop(0)
        target_server = conf.cli_args.pop(0)

    if len(conf.cli_args) > 0:
        target_partition = conf.cli_args.pop(0)

    imap = IMAP()
    imap.connect()

    mbox_parts = imap.parse_mailfolder(mailfolder)

    if mbox_parts['domain'] == None:
        domain = conf.get('kolab', 'primary_domain')
        user_identifier = mbox_parts['path_parts'][1]
    else:
        domain = mbox_parts['domain']
        user_identifier = "%s@%s" % (mbox_parts['path_parts'][1], mbox_parts['domain'])

    auth = Auth(domain=domain)
    auth.connect()

    user = auth.find_recipient(user_identifier)

    source_server = imap.user_mailbox_server(mailfolder)
    imap.connect(server=source_server)
    imap.imap.xfer(mailfolder, target_server)

    auth.set_entry_attributes(domain, user, {'mailhost': target_server})
