#!/usr/bin/python
#
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

# workaround for PEP 366
__package__ = ''

import listener
import logging
import os
import sys
from univention.config_registry import ConfigRegistry
import univention.debug as ulog

sys.path = [
        os.path.abspath(
                os.path.join(
                        os.path.dirname(
                                os.path.realpath(os.path.abspath(__file__))
                            ),
                        '..'
                    )
            )] + sys.path

#sys.stderr = open('/dev/null', 'a')

name = 'kolab'
description = "Kolab Groupware Listener for UCS"

# The filter has to be composed to make sure only Kolab Groupware
# related objects are passed along to this listener module.
filter = '(|(objectClass=kolabInetOrgPerson)(objectClass=univentionMailSharedFolder))'
# attributes = ['*']

import pykolab
from pykolab import constants
from pykolab import utils

log = pykolab.getLogger('pykolab.listener')
# log.remove_stdout_handler()
log.setLevel(logging.DEBUG)
log.debuglevel = 9

conf = pykolab.getConf()
conf.finalize_conf(fatal=False)
conf.debuglevel = 9

from pykolab.auth import Auth


def handler(*args, **kw):
    log.info("kolab.handler(args(%d): %r, kw: %r)" % (len(args), args, kw))

    auth = Auth()
    auth.connect()

    if len(args) == 4:
        # moddn
        dn = args[0]
        new = utils.normalize(args[1])
        old = utils.normalize(args[2])
        command = args[4]
        pass

    elif len(args) == 3:
        dn = args[0]
        new = utils.normalize(args[1])
        old = utils.normalize(args[2])

        if isinstance(old, dict) and len(old.keys()) > 0:
            # Two options:
            # - entry changed
            # - entry deleted
            log.info("user %r, old is dict" % (dn))

            if isinstance(new, dict) and len(new.keys()) > 0:
                log.info("Modify entry %r" % (dn))

                mailserver_attribute = conf.get('ldap', 'mailserver_attribute').lower()

                if mailserver_attribute is None:
                    log.error("Mail server attribute is not set")
                    return

                if mailserver_attribute in old:
                    log.info("Modified entry %r has mail server attribute %s: %r" % (dn, mailserver_attribute, new[mailserver_attribute]))

                    if not old[mailserver_attribute] == constants.fqdn:
                        # Even though the new mailserver can be us, it is the
                        # *current* mail server that needs to push for the XFER.
                        log.info("The mail server for user %r is set, and it is not me (%r)" % (dn, old[mailserver_attribute]))
                        return

                else:
                    # If old has no mailserver attribute, but new does, we need to create
                    # the user locally.
                    if mailserver_attribute in new:
                        if not new[mailserver_attribute] == constants.fqdn:
                            log.info("The mail server for user %r is set (in new, not old), but it is not me (%r)" % (dn, new[mailserver_attribute]))
                            return
                    else:
                        log.info("Entry %r does not have a mail server attribute." % (dn))
                        return

                auth._auth._synchronize_callback(
                        change_type='modify',
                        previous_dn=None,
                        change_number=None,
                        dn=dn,
                        entry=new
                    )

            else:
                log.info("Delete entry %r" % (dn))

                # See if the mailserver_attribute exists
                mailserver_attribute = conf.get('ldap', 'mailserver_attribute').lower()

                if mailserver_attribute is None:
                    log.error("Mail server attribute is not set")
                    # TODO: Perhaps, query for IMAP servers. If there is only one,
                    #       we know what to do.
                    return

                if mailserver_attribute in old:
                    log.info("Deleted entry %r has mail server attribute %s: %r" % (dn, mailserver_attribute, old[mailserver_attribute]))

                    if not old[mailserver_attribute] == constants.fqdn:
                        log.info("The mail server for user %r is set, and it is not me (%r)" % (dn, old[mailserver_attribute]))
                        return

                else:
                    log.info("Entry deletion notification for %r does not have a mail server attribute specified." % (dn))

                cfg = ConfigRegistry()
                cfg.load()

                if cfg.is_true('mail/cyrus/mailbox/delete', True):
                    auth._auth._synchronize_callback(
                            change_type='delete',
                            previous_dn=None,
                            change_number=None,
                            dn=dn,
                            entry=old
                        )

        elif isinstance(new, dict) and len(new.keys()) > 0:
            # Old is not a dict (or empty), so the entry is just created
            log.info("Add entry %r" % (dn))

            # See if the mailserver_attribute exists
            mailserver_attribute = conf.get('ldap', 'mailserver_attribute').lower()

            if mailserver_attribute is None:
                log.error("Mail server attribute is not set")
                # TODO: Perhaps, query for IMAP servers. If there is only one,
                #       we know what to do.
                return

            if mailserver_attribute in new:
                log.info("Added entry %r has mail server attribute %s: %r" % (dn, mailserver_attribute, new[mailserver_attribute]))

                if not new[mailserver_attribute] == constants.fqdn:
                    log.info("The mail server for user %r is set, and it is not me (%r)" % (dn, new[mailserver_attribute]))
                    return

            else:
                log.info("Added entry %r does not have a mail server attribute set." % (dn))
                return

            auth._auth._synchronize_callback(
                    change_type='add',
                    previous_dn=None,
                    change_number=None,
                    dn=dn,
                    entry=new
                )

        else:
            log.info("entry %r changed, but no new or old attributes" % (dn))


def initialize():
    log.info("kolab.initialize()")
