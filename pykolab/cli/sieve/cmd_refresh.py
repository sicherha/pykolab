# -*- coding: utf-8 -*-
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

import pykolab

from pykolab import utils
from pykolab.auth import Auth
from pykolab.cli import commands
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

import sys
import time
from urlparse import urlparse

def __init__():
    commands.register('refresh', execute, group='sieve', description=description())

def description():
    return """Refresh a user's managed and contributed sieve scripts."""

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
 
    sieveclient = sievelib.managesieve.Client(hostname, port, conf.debuglevel > 8)
    sieveclient.connect(None, None, True)
    sieveclient._plain_authentication(admin_login, admin_password, address)
    sieveclient.authenticated = True

    result = sieveclient.listscripts()
    
    if result == None:
        active = None
        scripts = []
    else:
        active, scripts = result
        

    print "Found the following scripts: %s" % (','.join(scripts))
    print "And the following script is active: %s" % (active)

    mgmt_required_extensions = []

    mgmt_script = """#
# MANAGEMENT
#
"""

    user = auth.get_entry_attributes(domain, user, ['*'])

    #
    # Delivery to Folder
    #
    dtf_active_attr = conf.get('sieve', 'deliver_to_folder_active')
    if not dtf_active_attr == None:
        if user.has_key(dtf_active_attr):
            dtf_active = utils.true_or_false(user[dtf_active_attr])
        else:
            dtf_active = False
    else:
        # TODO: Not necessarily de-activated, the *Active attributes are
        # not supposed to charge this - check the deliver_to_folder_attr
        # attribute value for a value.
        dtf_active = False

    if dtf_active:
        dtf_folder_name_attr = conf.get('sieve', 'deliver_to_folder_attr')
        if not dtf_folder_name_attr == None:
            if user.has_key(dtf_folder_name_attr):
                dtf_folder = user[dtf_folder_name_attr]
            else:
                log.warning(_("Delivery to folder active, but no folder name attribute available for user %r") % (user))
                dtf_active = False
        else:
            log.error(_("Delivery to folder active, but no folder name attribute configured"))
            dtf_active = False

    #
    # Folder name to delivery spam to.
    #
    # Global or local.
    #
    sdf_filter = True
    sdf = conf.get('sieve', 'spam_global_folder')

    if sdf == None:
        sdf = conf.get('sieve', 'spam_personal_folder')
        if sdf == None:
            sdf_filter = False

    #
    # Mail forwarding
    #
    forward_active = None
    forward_addresses = []
    forward_keepcopy = None
    forward_uce = None

    forward_active_attr = conf.get('sieve', 'forward_address_active')
    if not forward_active_attr == None:
        if user.has_key(forward_active_attr):
            forward_active = utils.true_or_false(user[forward_active_attr])
        else:
            forward_active = False

    if not forward_active == False:
        forward_address_attr = conf.get('sieve', 'forward_address_attr')
        if user.has_key(forward_address_attr):
            if isinstance(user[forward_address_attr], basestring):
                forward_addresses = [ user[forward_address_attr] ]
            elif isinstance(user[forward_address_attr], str):
                forward_addresses = [ user[forward_address_attr] ]
            else:
                forward_addresses = user[forward_address_attr]

        forward_keepcopy_attr = conf.get('sieve', 'forward_keepcopy_active')
        if not forward_keepcopy_attr == None:
            if user.has_key(forward_keepcopy_attr):
                forward_keepcopy = utils.true_or_false(user[forward_keepcopy_attr])
            else:
                forward_keepcopy = False

        forward_uce_attr = conf.get('sieve', 'forward_uce_active')
        if not forward_uce_attr == None:
            if user.has_key(forward_uce_attr):
                forward_uce = utils.true_or_false(user[forward_uce_attr])
            else:
                forward_uce = False

    if dtf_active:
        mgmt_required_extensions.append('fileinto')

    if sdf_filter:
        mgmt_required_extensions.append('fileinto')

    import sievelib.factory

    mgmt_script = sievelib.factory.FiltersSet("MANAGEMENT")

    for required_extension in mgmt_required_extensions:
        mgmt_script.require(required_extension)

    if forward_active:
        if forward_uce:
            if forward_keepcopy:
                mgmt_script.addfilter('forward-uce-keepcopy', ['true'], [("redirect", ":copy", forward_addresses)])
            else:
                mgmt_script.addfilter('forward-uce', ['true'], [("redirect", forward_addresses)])
        else:
            if forward_keepcopy:
                mgmt_script.addfilter('forward-keepcopy', [("X-Spam-Status", ":matches", "No,*")], [("redirect", ":copy", forward_addresses)])
            else:
                mgmt_script.addfilter('forward', [("X-Spam-Status", ":matches", "No,*")], [("redirect", forward_addresses)])
    
    if sdf_filter:
        mgmt_script.addfilter('spam_delivery_folder', [("X-Spam-Status", ":matches", "Yes,*")], [("fileinto", "INBOX/Spam"), ("stop")])

    mgmt_script = mgmt_script.__str__()

    result = sieveclient.putscript("MANAGEMENT", mgmt_script)

    if not result:
        print "Putting in script MANAGEMENT failed...?"
    else:
        print "Putting in script MANAGEMENT succeeded"

    user_script = """#
# User
#

require ["include"];
"""

    for script in scripts:
        if not script in [ "MASTER", "MANAGEMENT", "USER" ]:
            print "Including script %s in USER" % (script)
            user_script = """%s

include :personal "%s";
""" % (user_script, script)

    result = sieveclient.putscript("USER", user_script)
    if not result:
        print "Putting in script USER failed...?"
    else:
        print "Putting in script USER succeeded"

    result = sieveclient.putscript("MASTER", """#
# MASTER
# 
# This file is authoritative for your system and MUST BE KEPT ACTIVE.
#
# Altering it is likely to render your account dysfunctional and may
# be violating your organizational or corporate policies.
# 
# For more information on the mechanism and the conventions behind
# this script, see http://wiki.kolab.org/KEP:14
#

require ["include"];

# OPTIONAL: Includes for all or a group of users
# include :global "all-users";
# include :global "this-group-of-users";

# The script maintained by the general management system
include :personal "MANAGEMENT";

# The script(s) maintained by one or more editors available to the user
include :personal "USER";
""")

    if not result:
        print "Putting in script MASTER failed...?"
    else:
        print "Putting in script MASTER succeeded"

    sieveclient.setactive("MASTER")
