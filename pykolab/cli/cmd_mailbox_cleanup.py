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

import ldap
import sys

import commands

import pykolab

from pykolab import imap_utf7
from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('mailbox_cleanup', execute, description=description())

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option(
            '--dry-run',
            dest    = "dryrun",
            action  = "store_true",
            default = False,
            help    = _("Do not actually delete mailboxes, but report what mailboxes would have been deleted.")
        )

def description():
    return _("Clean up mailboxes that do no longer have an owner.")

def execute(*args, **kw):
    """
        List mailboxes
    """

    auth = Auth()
    domains = auth.list_domains()

    imap = IMAP()
    imap.connect()

    domain_folders = {}

    subjects = []
    # Placeholder for subjects that would have already been deleted
    subjects_deleted = []

    for domain in domains.keys():
        domain_folders[domain] = imap.lm("user/%%@%s" % (domain))

    for domain in domain_folders.keys():
        auth = Auth(domain=domain)
        auth.connect(domain)

        for folder in domain_folders[domain]:
            user = folder.replace('user/','')

            try:
                recipient = auth.find_recipient(user)
            except ldap.NO_SUCH_OBJECT, errmsg:
                if not user in subjects_deleted and conf.dryrun:
                    subjects_deleted.append(user)

                if conf.dryrun:
                    log.info(_("Would have deleted folder 'user/%s' (dryrun)") % (user))
                else:
                    log.info(_("Deleting folder 'user/%s'") % (user))
                continue

            if len(recipient) == 0 or recipient == []:
                if not user in subjects_deleted and conf.dryrun:
                    subjects_deleted.append(user)

                if conf.dryrun:
                    log.info(_("Would have deleted folder 'user/%s' (dryrun)") % (user))
                else:
                    log.info(_("Deleting folder 'user/%s'") % (user))
                    try:
                        imap.dm(folder)
                    except:
                        log.error(_("Error deleting folder 'user/%s'") % (user))
            else:
                log.debug(_("Valid recipient found for 'user/%s'") % (user), level=6)

                if not user in subjects:
                    subjects.append(user)

    imap_domains = []
    folders = imap.lm()
    for folder in folders:
        namespace = folder.split('/')[0]
        mailbox = folder.split('/')[1]

        if len(mailbox.split('@')) > 1:
            domain = mailbox.split('@')[1]
            if not domain in domains.keys() and not domain in imap_domains:
                imap_domains.append(domain)

    for domain in imap_domains:
        for folder in imap.lm('user/%%@%s' % (domain)):

            user = folder.replace('user/', '')

            if not user in subjects_deleted and conf.dryrun:
                subjects_deleted.append(user)

            if conf.dryrun:
                log.info(_("Would have deleted folder '%s' (dryrun)") % (folder))
            else:
                log.info(_("Deleting folder '%s'") % (folder))
                try:
                    imap.dm(folder)
                except:
                    log.error(_("Error deleting folder '%s'") % (folder))

        for folder in imap.lm('shared/%%@%s' % (domain)):
            if conf.dryrun:
                log.info(_("Would have deleted folder '%s' (dryrun)") % (folder))
            else:
                log.info(_("Deleting folder '%s'") % (folder))
                try:
                    imap.dm(folder)
                except:
                    log.error(_("Error deleting folder '%s'") % (folder))

    for folder in [x for x in imap.lm() if not x.startswith('DELETED/')]:
        folder = imap_utf7.decode(folder)
        acls = imap.list_acls(folder)

        for subject in acls.keys():
            if subject == 'anyone':
                log.info(
                        _("Skipping removal of ACL %s for subject %s on folder %s") % (
                                acls[subject],
                                subject,
                                folder
                            )
                    )

                continue

            if not subject in subjects and not subject in subjects_deleted:
                if conf.dryrun:
                    log.info(
                            _("Would have deleted ACL %s for subject %s on folder %s") % (
                                    acls[subject],
                                    subject,
                                    folder
                                )
                        )
                else:
                    log.info(
                            _("Deleting ACL %s for subject %s on folder %s") % (
                                    acls[subject],
                                    subject,
                                    folder
                                )
                        )

                    try:
                        imap.set_acl(folder, aci_subject, '')
                    except:
                        log.error(
                                _("Error removing ACL %s for subject %s from folder %s") % (
                                        acls[subject],
                                        subject,
                                        folder
                                    )
                            )

