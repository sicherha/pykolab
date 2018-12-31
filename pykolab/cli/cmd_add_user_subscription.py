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

from pykolab.imap import IMAP
from pykolab.translate import _
from pykolab import utils

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register(
        'add_user_subscription',
        execute,
        aliases=['aus', 'subscribe'],
        description=description()
    )

def description():
    return _("Subscribe a user to a folder.")

def execute(*args, **kw):
    folder_pattern = "*"

    try:
        user = conf.cli_args.pop(0)
        try:
            folder_pattern = conf.cli_args.pop(0)
        except IndexError, errmsg:
            folder_pattern = utils.ask_question(_("Folder pattern"))

    except IndexError, errmsg:
        user = utils.ask_question(_("User ID"))
        folder_pattern = utils.ask_question(_("Folder pattern"))

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

    if not imap.has_folder(folder_pattern):
        print >> sys.stderr, \
                _("Cannot subscribe user to folder %r:") % (folder_pattern), \
                _("No such folder")
        sys.exit(1)

    _folders = imap.lm(folder_pattern)

    for _folder in _folders:
        imap.subscribe(_folder)

