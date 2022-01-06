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
from pykolab import utils

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('set_mailbox_acl', execute, description=description(), aliases=['sam'])

def description():
    return """Set an ACL for a identifier on a folder."""

def execute(*args, **kw):
    try:
        folder = conf.cli_args.pop(0)
        try:
            identifier = conf.cli_args.pop(0)
            try:
                acl = conf.cli_args.pop(0)
            except IndexError:
                acl = utils.ask_question(_("ACI Permissions"))

        except IndexError:
            identifier = utils.ask_question(_("ACI Subject"))
            acl = utils.ask_question(_("ACI Permissions"))

    except IndexError:
        folder = utils.ask_question(_("Folder name"))
        identifier = utils.ask_question(_("ACI Subject"))
        acl = utils.ask_question(_("ACI Permissions"))

    if len(folder.split('@')) > 1:
        domain = folder.split('@')[1]
    else:
        domain = conf.get('kolab', 'primary_domain')

    imap = IMAP()
    imap.connect(domain=domain)

    if not imap.has_folder(folder):
        print(_("No such folder %r") % (folder), file=sys.stderr)

    else:
        folders = imap.list_folders(folder)
        for folder in folders:
            imap.set_acl(folder, identifier, acl)
