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

from pykolab.imap import IMAP
from pykolab.translate import _
from pykolab import utils

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('set_quota', execute, description=description(), aliases=['sq'])

def description():
    return """Configure quota for a folder."""

def execute(*args, **kw):
    try:
        folder = conf.cli_args.pop(0)
        try:
            quota = conf.cli_args.pop(0)
        except IndexError, errmsg:
            quota = utils.ask_question(_("New quota"))

    except IndexError, errmsg:
        folder = utils.ask_question(_("Folder name"))
        quota = utils.ask_question(_("New quota"))

    if len(folder.split('@')) > 1:
        domain = folder.split('@')[1]
    else:
        domain = conf.get('kolab', 'primary_domain')

    imap = IMAP()
    imap.connect(domain=domain)

    if not imap.has_folder(folder):
        print >> sys.stderr, _("No such folder %r") % (folder)

    else:
        imap.set_quota(folder, quota)

    # See if the folder is an INBOX folder
    # If yes, edit LDAP (through WAP client)
    # If no, edit IMAP

    # Verify the folder actually exists in IMAP
