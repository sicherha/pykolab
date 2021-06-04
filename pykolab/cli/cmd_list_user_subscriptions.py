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
from pykolab import utils

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_user_subscriptions', execute, aliases='lus', description=description())

def cli_options(*args, **kw):
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--raw',
                                dest    = "raw",
                                action  = "store_true",
                                default = False,
                                help    = _("Display raw IMAP UTF-7 folder names"))

    my_option_group.add_option( '--unsubscribed',
                                dest    = "unsubscribed",
                                action  = "store_true",
                                default = False,
                                help    = _("List unsubscribed folders"))

def description():
    return _("List the folders a user is subscribed to.")

def execute(*args, **kw):
    folder_pattern = "*"

    try:
        user = conf.cli_args.pop(0)
        try:
            folder_pattern = conf.cli_args.pop(0)
        except IndexError, errmsg:
            pass

    except IndexError, errmsg:
        user = utils.ask_question(_("User ID"))

    if len(user.split('@')) > 1:
        domain = user.split('@')[1]
    else:
        domain = conf.get('kolab', 'primary_domain')

    imap = IMAP()
    imap.connect(domain=domain, login=False)

    backend = conf.get(domain, 'imap_backend')
    if backend == None:
        backend = conf.get('kolab', 'imap_backend')

    admin_login = conf.get(backend, 'admin_login')
    admin_password = conf.get(backend, 'admin_password')

    imap.login_plain(admin_login, admin_password, user)

    subscribed_folders = imap.lsub(folder_pattern)

    if conf.unsubscribed:
        unsubscribed_folders = []
        all_folders = imap.lm(folder_pattern)

        for folder in all_folders:
            if not folder in subscribed_folders:
                unsubscribed_folders.append(folder)

        if len(unsubscribed_folders) > 0:
            if not conf.raw:
                print("\n".join([imap_utf7.decode(x) for x in unsubscribed_folders]))
            else:
                print("\n".join(unsubscribed_folders))
        else:
            print(_("No unsubscribed folders for user %s") % (user))

    else:
        if not conf.raw:
            print("\n".join([imap_utf7.decode(x) for x in subscribed_folders]))
        else:
            print("\n".join(subscribed_folders))
