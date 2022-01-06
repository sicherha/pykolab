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

from __future__ import print_function

import sys

import commands

import pykolab

from pykolab.imap import IMAP
from pykolab.translate import _
from pykolab import imap_utf7
from pykolab import utils

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('set_mailbox_metadata', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option(
                '--user',
                dest    = "user",
                action  = "store",
                default = None,
                metavar = "USER",
                help    = _("Set annotation as user USER")
            )

def description():
    return """Set an metadata entry on a folder."""

def execute(*args, **kw):
    try:
        folder = conf.cli_args.pop(0)
        try:
            metadata_path = conf.cli_args.pop(0)
            try:
                metadata_value = conf.cli_args.pop(0)
            except IndexError:
                metadata_value = utils.ask_question(_("Metadata value"))

        except IndexError:
            metadata_path = utils.ask_question(_("Metadata path"))
            metadata_value = utils.ask_question(_("Metadata value"))

    except IndexError:
        folder = utils.ask_question(_("Folder name"))
        metadata_path = utils.ask_question(_("Metadata path"))
        metadata_value = utils.ask_question(_("Metadata value"))

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
        print(_("No such folder %r") % (folder), file=sys.stderr)

    else:
        folders = imap.lm(imap_utf7.encode(folder))
        for folder in folders:
            imap.set_metadata(imap_utf7.decode(folder), metadata_path, metadata_value)
