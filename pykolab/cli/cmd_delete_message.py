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

import sys

import commands

import pykolab

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('delete_message', execute, description=description())

def description():
    return _("Delete a message from a folder")

def execute(*args, **kw):
    """
        Delete a message from a mail folder
    """

    try:
        folder = conf.cli_args.pop(0)

        try:
            uid = conf.cli_args.pop(0)
        except:
            log.error(_("Specify a UID"))
            sys.exit(1)
    except:
        log.error(_("Specify a folder"))
        sys.exit(1)

    imap = IMAP()
    imap.connect()

    _folder = imap.lm(folder)

    if _folder == None or _folder == []:
        log.error(_("No such folder"))
        sys.exit(1)

    imap.set_acl(folder, 'cyrus-admin', 'lrswt')

    imap.select(folder)

    imap.store(uid, '+FLAGS', '\\Deleted')

