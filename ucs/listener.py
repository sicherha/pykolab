#!/usr/bin/python
#
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
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

#sys.stderr = open('/dev/null', 'a')

name = 'kolab'
description = "Kolab Groupware Listener for UCS"

# The filter has to be composed to make sure only Kolab Groupware
# related objects are passed along to this listener module.
filter = '(|(objectClass=kolabInetOrgPerson)(objectClass=univentionMailSharedFolder))'
#attributes = [ '*' ]

import pykolab
from pykolab import constants
from pykolab import utils

log = pykolab.getLogger('pykolab.listener')
#log.remove_stdout_handler()
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

                auth._auth._synchronize_callback(
                        change_type = 'modify',
                        previous_dn = None,
                        change_number = None,
                        dn = dn,
                        entry = new
                    )

            else:
                log.info("Delete entry %r" % (dn))

                auth._auth._synchronize_callback(
                        change_type = 'delete',
                        previous_dn = None,
                        change_number = None,
                        dn = dn,
                        entry = old
                    )

        elif isinstance(new, dict) and len(new.keys()) > 0:
            # Old is not a dict (or empty), so the entry is just created
            log.info("Add entry %r" % (dn))

            # See if the mailserver_attribute exists
            mailserver_attribute = conf.get('ldap', 'mailserver_attribute').lower()

            if mailserver_attribute == None:
                log.error("Mail server attribute is not set")
                # TODO: Perhaps, query for IMAP servers. If there is only one,
                #       we know what to do.
                return

            if new.has_key(mailserver_attribute):
                log.info("Added entry %r has mail server attribute %s: %r" % (dn, mailserver_attribute, new[mailserver_attribute]))

                if not new[mailserver_attribute] == constants.fqdn:
                    log.info("The mail server for user %r is set, and it is not me (%r)" % (dn, new[mailserver_attribute]))
                    return

            auth._auth._synchronize_callback(
                    change_type = 'add',
                    previous_dn = None,
                    change_number = None,
                    dn = dn,
                    entry = new
                )

        else:
            log.info("entry %r changed, but no new or old attributes" % (dn))

def initialize():
    log.info("kolab.initialize()")
