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

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('rename_mailbox', execute, description=description(), aliases=['rm'])

def description():
    return """Rename a mailbox or sub-folder."""

def execute(*args, **kw):
    """
        Rename mailbox
    """

    try:
        source_folder = conf.cli_args.pop(0)
        try:
            target_folder = conf.cli_args.pop(0)
            try:
                partition = conf.cli_args.pop(0)
            except IndexError, errmsg:
                partition = None
        except IndexError, errmsg:
            print >> sys.stderr, _("No target mailbox name specified")
    except IndexError, errmsg:
        print >> sys.stderr, _("No source mailbox name specified")
        sys.exit(1)

    if len(source_folder.split('@')) > 1:
        domain = source_folder.split('@')[1]
    else:
        domain = conf.get('kolab', 'primary_domain')

    imap = IMAP()
    imap.connect(domain=domain)

    if not imap.has_folder(source_folder):
        print >> sys.stderr, _("Source folder %r does not exist") % (source_folder)
        sys.exit(1)

    if imap.has_folder(target_folder):
        print >> sys.stderr, _("Target folder %r already exists") % (target_folder)
        sys.exit(1)

    imap.user_mailbox_rename(source_folder.replace('user/',''), target_folder.replace('user/',''), partition=partition)

