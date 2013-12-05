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
import univention_baseconfig
import univention.debug as ulog

sys.path = [
        os.path.abspath(
                os.path.join(
                        os.path.dirname(
                                os.path.realpath(os.path.abspath(__file__))
                            ),
                        '..'
                    )
            ) ] + sys.path

sys.stderr = open('/dev/null', 'a')

name = 'kolab_sieve'
description = "Sieve Script Management for Kolab Groupware on UCS"

# The filter has to be composed to make sure only Kolab Groupware
# related objects are passed along to this listener module.
filter = '(objectClass=kolabInetOrgPerson)'
#attributes = [ '*' ]

import pykolab
from pykolab import constants
from pykolab import utils

log = pykolab.getLogger('pykolab.listener')
log.remove_stdout_handler()
log.setLevel(logging.DEBUG)
log.debuglevel = 9

conf = pykolab.getConf()
conf.finalize_conf(fatal=False)
conf.debuglevel = 9

from pykolab.auth import Auth

def handler(*args, **kw):
    auth = Auth()
    auth.connect()

    if len(args) == 4:
        # moddn, not relevant for Sieve Script Management
        pass

    elif len(args) == 3:
        dn = args[0]
        new = utils.normalize(args[1])
        old = utils.normalize(args[2])

        if isinstance(old, dict) and len(old.keys()) > 0:
            # Either the entry changed or was deleted

            if isinstance(new, dict) and len(new.keys()) > 0:
                # The entry was modified.

                result_attr = conf.get('cyrus-sasl', 'result_attribute')

                if not new.has_key(result_attr):
                    log.error(
                            "Entry %r does not have attribute %r" % (
                                    dn,
                                    result_attr
                                )
                        )

                    return

                # See if the mailserver_attribute exists
                mailserver_attribute = conf.get('ldap', 'mailserver_attribute').lower()

                if mailserver_attribute == None:
                    log.error("Mail server attribute is not set")
                    # TODO: Perhaps, query for IMAP servers. If there is only one,
                    #       we know what to do.
                    return

                if new.has_key(mailserver_attribute):
                    if not new[mailserver_attribute] == constants.fqdn:
                        log.info(
                                "The mail server for user %r is set, and it is not me (%r)" % (
                                        dn,
                                        new[mailserver_attribute]
                                    )
                            )

                        return
                else:
                    log.error("Entry %r does not have a mail server set" % (dn))
                    return

                conf.plugins.exec_hook(
                        'sieve_mgmt_refresh',
                        kw = {
                                'user': new[result_attr]
                            }
                    )

            else:
                # The entry was deleted. This is irrelevant for
                # Sieve Script Management
                return

        elif isinstance(new, dict) and len(new.keys()) > 0:
            # Old is not a dict (or empty), so the entry is just created

            # See if the mailserver_attribute exists
            mailserver_attribute = conf.get('ldap', 'mailserver_attribute').lower()
            result_attr = conf.get('cyrus-sasl', 'result_attribute').lower()

            if mailserver_attribute == None:
                log.error("Mail server attribute is not set")
                # TODO: Perhaps, query for IMAP servers. If there is only one,
                #       we know what to do.
                return

            if new.has_key(mailserver_attribute):
                if not new[mailserver_attribute] == constants.fqdn:
                    log.info("The mail server for user %r is set, and it is not me (%r)" % (dn, new[mailserver_attribute]))
                    return

                conf.plugins.exec_hook(
                        'sieve_mgmt_refresh',
                        kw = {
                                'user': new[result_attr]
                            }
                    )

        else:
            log.info("entry %r changed, but no new or old attributes" % (dn))

