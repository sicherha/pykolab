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

import sys

import commands

import pykolab

from pykolab import imap_utf7
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_messages', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option(
            '--deleted',
            dest    = "list_deleted",
            action  = "store_true",
            default = False,
            help    = _("Include messages flagged as \Deleted")
        )

def description():
    return _("List messages in a folder")

def execute(*args, **kw):
    """
        List messages in a folder
    """

    try:
        folder = conf.cli_args.pop(0)

    except:
        log.error(_("Specify a folder"))
        sys.exit(1)

    imap = IMAP()
    imap.connect()

    _folder = imap.lm(imap_utf7.encode(folder))

    if _folder == None or _folder == []:
        log.error(_("No such folder"))
        sys.exit(1)

    imap.set_acl(folder, 'cyrus-admin', 'lrs')

    imap.select(imap_utf7.encode(folder))

    if conf.list_deleted:
        typ, data = imap.search(None, 'ALL')
    else:
        typ, data = imap.search(None, '(ALL UNDELETED)')

    num_messages = len(data[0].split())

    for num in data[0].split():
        typ, flags = imap.fetch(num, 'FLAGS')
        flags = flags[0].split()
        if len(flags) >= 3:
            # Any flags are set
            if flags[2] == '(\\Deleted))':
                print num, '\Deleted'
            elif flags[2] == '(\\Deleted':
                print num, '\Deleted'
            elif '\\Deleted' in flags[3:]:
                print num, '\Deleted'
            elif '\\Deleted))' in flags[3:]:
                print num, '\Deleted'
            else:
                print num
        else:
            print num

    imap.set_acl(folder, 'cyrus-admin', '')
