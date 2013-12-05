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

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('acl_cleanup', execute, description=description())

def description():
    return _("Clean up ACLs that use identifiers that no longer exist")

def execute(*args, **kw):
    """
        List mailboxes
    """

    try:
        aci_subject = conf.cli_args.pop(0)
    except:
        aci_subject = None

    imap = IMAP()
    imap.connect()

    folders = imap.lm()

    for folder in folders:
        acls = imap.list_acls(folder)

        if not aci_subject == None:
            if aci_subject in acls.keys():
                log.debug(_("Deleting ACL %s for subject %s on folder %s") % (
                        acls[aci_subject],
                        aci_subject,
                        folder
                    ), level=8)

                imap.set_acl(folder, aci_subject, '')

        #else:
            #for _aci_subject in acls.keys():
                # connect to auth(!)
                # find recipient result_attr=aci_subject
                # if no entry, expire acl