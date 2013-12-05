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

import pykolab

from pykolab import imap_utf7
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_mailboxes', execute, description=description(), aliases='lm')

def description():
    return "List mailboxes.\n" + \
        "%-28s" % ('') + \
        "Use wildcards '*' and '%' for more control.\n"

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--raw',
                                dest    = "raw",
                                action  = "store_true",
                                default = False,
                                help    = _("Display raw IMAP UTF-7 folder names"))

    my_option_group.add_option( '--server',
                                dest    = "connect_server",
                                action  = "store",
                                default = None,
                                metavar = "SERVER",
                                help    = _("List mailboxes on server SERVER only."))

def execute(*args, **kw):
    """
        List mailboxes
    """

    searches = []

    # See if conf.cli_args components make sense.
    for arg in conf.cli_args:
        if arg == '*':
            searches.append(arg)
        if arg.startswith('user'):
            searches.append(arg)
        if arg.startswith('shared'):
            searches.append(arg)
        if arg.startswith('DELETED'):
            searches.append(arg)
        if arg.startswith('news'):
            searches.append(arg)

    if len(searches) == 0:
        searches = [ '' ]

    imap = IMAP()

    if not conf.connect_server == None:
        imap.connect(server=conf.connect_server)
    else:
        imap.connect()

    folders = []

    for search in searches:
        log.debug(_("Appending folder search for %r") % (search), level=8)
        folders.extend(imap.lm(imap_utf7.encode(search)))

    for folder in folders:
        if not conf.raw:
            print imap_utf7.decode(folder).encode('utf-8')
        else:
            print folder
