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

import pykolab

from pykolab.auth import Auth
from pykolab.cli import commands
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

import time
from urlparse import urlparse


def __init__():
    commands.register('test', execute, group='sieve', description=description())

def description():
    return """Syntactically check a user's sieve scripts."""

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
 
    sieveclient = sievelib.managesieve.Client(hostname, port, True)
    sieveclient.connect(None, None, True)
    sieveclient._plain_authentication(admin_login, admin_password, address)
    sieveclient.authenticated = True

    active, scripts = sieveclient.listscripts()

    print("%s (active)" % (active))
    
    _all_scripts = [ active ] + scripts
    _used_scripts = [ active ]
    _included_scripts = []

    _a_script = sieveclient.getscript(active)

    print(_a_script)

    import sievelib.parser

    _a_parser = sievelib.parser.Parser(debug=True)
    _a_parsed = _a_parser.parse(_a_script)

    #print "%r" % (_a_parsed)

    if not _a_parsed:
        print(_a_parser.error)

    print("%r" % (_a_parser.result))

    for _a_command in _a_parser.result:
        print(_a_command.name, _a_command.arguments)
        if len(_a_command.children) > 0:
            for _a_child in _a_command.children:
                print("  ", _a_child.name, _a_child.arguments)

        if _a_command.name == "include":
            if _a_command.arguments["script"].strip('"') in scripts:
                print("OK")
                _used_scripts.append(_a_command.arguments["script"].strip('"'))
            else:
                print("Not OK")

    for script in scripts:
        print(script)

