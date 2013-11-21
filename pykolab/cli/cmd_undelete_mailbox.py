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

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('undelete_mailbox', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--dry-run',
                                dest    = "dry_run",
                                action  = "store_true",
                                default = False,
                                help    = _("Do not actually execute, but state what would have been executed."))

def description(*args, **kw):
    return _("Recover mailboxes previously deleted.")

def execute(*args, **kw):
    """
        Undelete mailbox
    """

    target_folder = None

    undelete_folder = conf.cli_args.pop(0)
    if len(conf.cli_args) > 0:
        target_folder = conf.cli_args.pop(0)

    imap = IMAP()
    imap.connect()
    imap.undelete_mailfolder(undelete_folder, target_folder)

