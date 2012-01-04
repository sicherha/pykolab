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
    commands.register('list_mailboxes', execute, description="List mailboxes.\n" + \
        "%-28s" %('') + \
        "Use wildcards '*' and '%' for more control.\n")

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--raw',
                                dest    = "raw",
                                action  = "store_true",
                                default = False,
                                help    = _("Display raw UTF-7 folder names"))

def execute(*args, **kw):
    """
        List mailboxes
    """
    try:
        searches = [ conf.cli_args.pop(1) ]
    except IndexError, e:
        #searches = [ 'DELETED/*', 'shared/*', 'user/*' ]
        searches = [ '' ]

    imap.connect()

    folders = []

    for search in searches:
        folders.extend(imap.lm(search))

    for folder in folders:
        print folder
