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

import datetime

import commands

import pykolab

from pykolab import imap_utf7
from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('count_domain_mailboxes', execute)

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
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
    imap = IMAP()
    imap.connect()

    auth = Auth()
    auth.connect()

    domains = auth.list_domains()

    folders = []
    for primary,secondaries in domains:
        print "%s: %d" % (primary,len(imap.lm("user/%%@%s" % (primary))))
        for secondary in secondaries:
            print "%s: %d" % (secondary,len(imap.lm("user/%%@%s" % (secondary))))

    null_realm = len(imap.lm("user/%%"))

    if null_realm > 0:
        print "null: %d" % (null_realm)

