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
    commands.register('server_info', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--server',
                                dest    = "connect_server",
                                action  = "store",
                                default = None,
                                metavar = "SERVER",
                                help    = _("List mailboxes on server SERVER only."))


def description():
    return "Display server info.\n"

def execute(*args, **kw):
    """
        List mailboxes
    """

    imap = IMAP()

    if not conf.connect_server == None:
        imap.connect(server=conf.connect_server)
    else:
        imap.connect()

    print imap.get_metadata("")
