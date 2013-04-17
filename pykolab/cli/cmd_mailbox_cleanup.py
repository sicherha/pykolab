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

import sys

import commands

import pykolab

from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('mailbox_cleanup', execute, description=description())

def description():
    return _("Clean up mailboxes that do no longer have an owner.")

def execute(*args, **kw):
    """
        List mailboxes
    """

    auth = Auth()
    domains = auth.list_domains()

    imap = IMAP()
    imap.connect()

    folders = []

    for domain,aliases in domains:
        folders.extend(imap.lm("user/%%@%s" % (domain)))

    for folder in folders:
        user = folder.replace('user/','')

        recipient = auth.find_recipient(user)

        if len(recipient) == 0 or recipient == []:
            log.info(_("Deleting folder 'user/%s'") % (user))
            try:
                imap.dm(folder)
            except:
                pass