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
from pykolab import utils

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_mailbox_metadata', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option(
                '--user',
                dest    = "user",
                action  = "store",
                default = None,
                metavar = "USER",
                help    = _("List annotations as user USER")
            )

def description():
    return """Obtain a list of metadata entries on a folder."""

def execute(*args, **kw):
    try:
        folder = conf.cli_args.pop(0)
    except IndexError, errmsg:
        folder = utils.ask_question(_("Folder name"))

    if len(folder.split('@')) > 1:
        domain = folder.split('@')[1]
    elif not conf.user == None and len(conf.user.split('@')) > 1:
        domain = conf.user.split('@')[1]
    else:
        domain = conf.get('kolab', 'primary_domain')

    imap = IMAP()

    if not conf.user == None:
        imap.connect(domain=domain, login=False)

        backend = conf.get(domain, 'imap_backend')
        if backend == None:
            backend = conf.get('kolab', 'imap_backend')

        admin_login = conf.get(backend, 'admin_login')
        admin_password = conf.get(backend, 'admin_password')

        imap.login_plain(admin_login, admin_password, conf.user)
    else:
        imap.connect(domain=domain)

    if not imap.has_folder(folder):
        print >> sys.stderr, _("No such folder %r") % (folder)

    else:
        metadata = []
        folders = imap.list_folders(folder)
        for folder in folders:
            print "Folder", folder.encode('utf-8')

            metadata = imap.get_metadata(folder)

            if metadata.has_key(folder):
                for annotation in metadata[folder].keys():
                    print "  %-49s %s" % (
                            annotation,
                            metadata[folder][annotation]
                        )
