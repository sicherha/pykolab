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

import commands

import pykolab

from pykolab import imap_utf7
from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('sync_mailhost_attrs', execute, description=description())

def description():
    return "Synchronize mailHost attribute values with the actual mailserver in a Cyrus IMAP Murder.\n"

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--delete',
                                dest    = "delete",
                                action  = "store_true",
                                default = False,
                                help    = _("Delete mailboxes for recipients that do not appear to exist in LDAP."))

    my_option_group.add_option( '--dry-run',
                                dest    = "dry_run",
                                action  = "store_true",
                                default = False,
                                help    = _("Display changes, do not apply them."))

    my_option_group.add_option( '--server',
                                dest    = "connect_server",
                                action  = "store",
                                default = None,
                                metavar = "SERVER",
                                help    = _("List mailboxes on server SERVER only."))

def execute(*args, **kw):
    """
        Synchronize or display changes
    """

    imap = IMAP()

    if not conf.connect_server == None:
        imap.connect(server=conf.connect_server)
    else:
        imap.connect()

    auth = Auth()
    auth.connect()

    domains = auth.list_domains()

    for primary,secondaries in domains:
        folders = []

        folders.extend(imap.lm('shared/%%@%s' % (primary)))
        folders.extend(imap.lm('user/%%@%s' % (primary)))

        for secondary in secondaries:
            folders.extend(imap.lm('shared/%%@%s' % (secondary)))
            folders.extend(imap.lm('user/%%@%s' % (secondary)))

        auth = Auth(domain=primary)
        auth.connect()

        for folder in folders:
            server = imap.user_mailbox_server(folder)
            recipient = auth.find_recipient('/'.join(folder.split('/')[1:]))
            if (isinstance(recipient, list)):
                if len(recipient) > 1:
                    log.warning(_("Multiple recipients for '%s'!") % ('/'.join(folder.split('/')[1:])))
                    continue
                elif len(recipient) == 0:
                    if conf.delete:
                        if conf.dry_run:
                            if not folder.split('/')[0] == 'shared':
                                log.warning(_("No recipients for '%s' (would have deleted the mailbox if not for --dry-run)!") % ('/'.join(folder.split('/')[1:])))
                            else:
                                continue
                        else:
                            if not '/'.join(folder.split('/')[0]) == 'shared':
                                log.info(_("Deleting mailbox '%s' because it has no recipients") % (folder))
                                imap.dm(folder)
                            else:
                                log.info(_("Not automatically deleting shared folder '%s'") % (folder))
                    else:
                        log.warning(_("No recipients for '%s' (use --delete to delete)!") % ('/'.join(folder.split('/')[1:])))

                    continue
            else:
                mailhost = auth.get_entry_attribute(primary, recipient, 'mailhost')

            if not server == mailhost:
                if conf.dry_run:
                    print folder, server, mailhost
                else:
                    auth.set_entry_attribute(primary, recipient, 'mailhost', server)

    folders = []
    folders.extend(imap.lm("shared/%%"))
    folders.extend(imap.lm("user/%%"))

    auth = Auth()
    auth.connect()

    for folder in folders:
        server = imap.user_mailbox_server(folder)
        recipient = auth.find_recipient('/'.join(folder.split('/')[1:]))

        print folder, server, recipient
