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
import time
from urlparse import urlparse

import pykolab

from pykolab import utils
from pykolab.auth import Auth
from pykolab.cli import commands
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register(
            'list',
            execute,
            group='sieve',
            description=description()
        )

def description():
    return """List a user's sieve scripts."""

def execute(*args, **kw):
    try:
        address = conf.cli_args.pop(0)
    except:
        address = utils.ask_question(_("Email Address"))

    auth = Auth()
    auth.connect()

    user = auth.find_recipient(address)

    # Get the main, default backend
    backend = conf.get('kolab', 'imap_backend')

    if len(address.split('@')) > 1:
        domain = address.split('@')[1]
    else:
        domain = conf.get('kolab', 'primary_domain')

    if conf.has_section(domain) and conf.has_option(domain, 'imap_backend'):
        backend = conf.get(domain, 'imap_backend')

    if conf.has_section(domain) and conf.has_option(domain, 'imap_uri'):
        uri = conf.get(domain, 'imap_uri')
    else:
        uri = conf.get(backend, 'uri')

    hostname = None
    port = None

    result = urlparse(uri)

    if hasattr(result, 'hostname'):
        hostname = result.hostname
    else:
        scheme = uri.split(':')[0]
        (hostname, port) = uri.split('/')[2].split(':')

    port = 4190

    # Get the credentials
    admin_login = conf.get(backend, 'admin_login')
    admin_password = conf.get(backend, 'admin_password')

    import sievelib.managesieve

    sieveclient = sievelib.managesieve.Client(
            hostname,
            port,
            conf.debuglevel > 8
        )

    sieveclient.connect(None, None, True)

    result = sieveclient._plain_authentication(
            admin_login,
            admin_password,
            address
        )

    if not result:
        print "LOGIN FAILED??"

    sieveclient.authenticated = True

    result = sieveclient.listscripts()

    if result == None:
        print "No scripts"
        sys.exit(0)

    (active, scripts) = result

    print "%s (active)" % (active)
    for script in scripts:
        print script

