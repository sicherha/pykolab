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

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('delete_mailbox', execute, description=description(), aliases=['dm'])

def description():
    return """Delete a mailbox or sub-folder. Note that the mailbox or folder is removed recursively."""

def execute(*args, **kw):
    """
        Delete mailbox
    """

    try:
        delete_folder = conf.cli_args.pop(0)
    except IndexError, e:
        print >> sys.stderr, _("No mailbox specified")
        sys.exit(1)

    imap = IMAP()

    imap.connect()
    delete_folders = imap.lm(delete_folder)
    for delete_folder in delete_folders:
        imap.delete_mailfolder(delete_folder)

