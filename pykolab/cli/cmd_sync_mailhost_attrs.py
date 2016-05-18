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

    folders = imap.lm()

    imap_domains_not_domains = []

    for folder in folders:
        if len(folder.split('@')) > 1 and not folder.startswith('DELETED'):
            _folder_domain = folder.split('@')[-1]
            if not _folder_domain in list(set(domains.keys() + domains.values())):
                imap_domains_not_domains.append(folder.split('@')[-1])

    imap_domains_not_domains = list(set(imap_domains_not_domains))

    log.debug(_("Domains in IMAP not in LDAP: %r") % (imap_domains_not_domains), level=8)

    if len(imap_domains_not_domains) > 0:
        for domain in imap_domains_not_domains:
            folders = []

            folders.extend(imap.lm('shared/%%@%s' % (domain)))
            folders.extend(imap.lm('user/%%@%s' % (domain)))

            for folder in folders:
                r_folder = folder
                if not folder.startswith('shared/'):
                    r_folder = '/'.join(folder.split('/')[1:])

                if conf.delete:
                    if conf.dry_run:
                        if not folder.startswith('shared/'):
                            log.warning(_("No recipients for '%s' (would have deleted the mailbox if not for --dry-run)!") % (r_folder))
                        else:
                            continue
                    else:
                        if not folder.startswith('shared/'):
                            log.info(_("Deleting mailbox '%s' because it has no recipients") % (folder))
                            try:
                                imap.dm(folder)
                            except Exception, errmsg:
                                log.error(_("An error occurred removing mailbox %r: %r") % (folder, errmsg))
                        else:
                            log.info(_("Not automatically deleting shared folder '%s'") % (folder))
                else:
                    log.warning(_("No recipients for '%s' (use --delete to delete)!") % (r_folder))

    for primary in list(set(domains.values())):
        secondaries = [x for x in domains.keys() if domains[x] == primary]

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
            r_folder = folder

            if folder.startswith('shared/'):
                recipient = auth.find_folder_resource(folder)
            else:
                r_folder = '/'.join(folder.split('/')[1:])
                recipient = auth.find_recipient(r_folder)

            if (isinstance(recipient, list)):
                if len(recipient) > 1:
                    log.warning(_("Multiple recipients for '%s'!") % (r_folder))
                    continue
                elif len(recipient) == 0:
                    if conf.delete:
                        if conf.dry_run:
                            if not folder.startswith('shared/'):
                                log.warning(_("No recipients for '%s' (would have deleted the mailbox if not for --dry-run)!") % (r_folder))
                            else:
                                continue
                        else:
                            if not folder.startswith('shared/'):
                                log.info(_("Deleting mailbox '%s' because it has no recipients") % (folder))
                                try:
                                    imap.dm(folder)
                                except Exception, errmsg:
                                    log.error(_("An error occurred removing mailbox %r: %r") % (folder, errmsg))
                            else:
                                log.info(_("Not automatically deleting shared folder '%s'") % (folder))
                    else:
                        log.warning(_("No recipients for '%s' (use --delete to delete)!") % (r_folder))

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

        if folder.startswith('shared/'):
            recipient = auth.find_folder_resource(folder)
        else:
            recipient = auth.find_recipient('/'.join(folder.split('/')[1:]))

        print folder, server, recipient
