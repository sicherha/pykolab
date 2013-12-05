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
from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_domain_mailboxes', execute)

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
        List deleted mailboxes
    """

    try:
        domain = conf.cli_args.pop(0)
    except:
        domain = utils.ask_question(_("Domain"))

    imap = IMAP()
    imap.connect()

    auth = Auth()
    auth.connect()

    domains = auth.list_domains()

    folders = []
    for primary,secondaries in domains:
        if not domain == primary and not domain in secondaries:
            continue

        folders.extend(imap.lm("user/%%@%s" % (primary)))
        for secondary in secondaries:
            folders.extend(imap.lm("user/%%@%s" % (secondary)))

    print "Deleted folders:"

    for folder in folders:
        if not conf.raw:
            print imap_utf7.decode(folder)
        else:
            print folder
