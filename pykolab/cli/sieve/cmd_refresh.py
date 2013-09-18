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

    log.debug(_("Found the following scripts for user %s: %s") % (address, ','.join(scripts)), level=8)
    log.deubg(_("And the following script is active for user %s: %s") % (address, active), level=8)

    mgmt_required_extensions = []

    mgmt_script = """#
# MANAGEMENT
#
"""

    user = auth.get_entry_attributes(domain, user, ['*'])

    #
    # Vacation settings (a.k.a. Out of Office)
    #
    vacation_active = None
    vacation_text = None
    vacation_uce = None
    vacation_noreact_domains = None
    vacation_react_domains = None

    vacation_active_attr = conf.get('sieve', 'vacation_active_attr')
    vacation_text_attr = conf.get('sieve', 'vacation_text_attr')
    vacation_uce_attr = conf.get('sieve', 'vacation_uce_attr')
    vacation_noreact_domains_attr = conf.get('sieve', 'vacation_noreact_domains_attr')
    vacation_react_domains_attr = conf.get('sieve', 'vacation_react_domains_attr')

    if not vacation_text_attr == None:

        if user.has_key(vacation_active_attr):
            vacation_active = utils.true_or_false(user[vacation_active_attr])
        else:
            vacation_active = False

        if user.has_key(vacation_text_attr):
            vacation_text = user[vacation_text_attr]
        else:
            vacation_active = False

        if user.has_key(vacation_uce_attr):
            vacation_uce = utils.true_or_false(user[vacation_uce_attr])
        else:
            vacation_uce = False

        if user.has_key(vacation_react_domains_attr):
            if isinstance(user[vacation_react_domains_attr], list):
                vacation_react_domains = user[vacation_react_domains_attr]
            else:
                vacation_react_domains = [ user[vacation_react_domains_attr] ]
        else:
            if user.has_key(vacation_noreact_domains_attr):
                if isinstance(user[vacation_noreact_domains_attr], list):
                    vacation_noreact_domains = user[vacation_noreact_domains_attr]
                else:
                    vacation_noreact_domains = [ user[vacation_noreact_domains_attr] ]
            else:
                vacation_noreact_domains = []

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

        if len(forward_addresses) == 0:
            forward_active = False

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

    if vacation_active:
        mgmt_required_extensions.append('vacation')
        mgmt_required_extensions.append('envelope')

    if dtf_active:
        mgmt_required_extensions.append('fileinto')

    if forward_active and (len(forward_addresses) > 1 or forward_keepcopy):
        mgmt_required_extensions.append('copy')

    if sdf_filter:
        mgmt_required_extensions.append('fileinto')

    import sievelib.factory

    mgmt_script = sievelib.factory.FiltersSet("MANAGEMENT")

    for required_extension in mgmt_required_extensions:
        mgmt_script.require(required_extension)

    mgmt_script.require('fileinto')

    if vacation_active:
        if not vacation_react_domains == None and len(vacation_react_domains) > 0:
            mgmt_script.addfilter(
                    'vacation',
                    [('envelope', ':domain', ":is", "from", vacation_react_domains)],
                    [
                            (
                                    "vacation",
                                    ":days", 1,
                                    ":subject",
                                    "Out of Office",
                                    # ":handle", see http://tools.ietf.org/html/rfc5230#page-4
                                    # ":mime", to indicate the reason is in fact MIME
                                    vacation_text
                                )
                        ]
                )

        elif not vacation_noreact_domains == None and len(vacation_noreact_domains) > 0:
            mgmt_script.addfilter(
                    'vacation',
                    [('not', ('envelope', ':domain', ":is", "from", vacation_noreact_domains))],
                    [
                            (
                                    "vacation",
                                    ":days", 1,
                                    ":subject",
                                    "Out of Office",
                                    # ":handle", see http://tools.ietf.org/html/rfc5230#page-4
                                    # ":mime", to indicate the reason is in fact MIME
                                    vacation_text
                                )
                        ]
                )

        else:
            mgmt_script.addfilter(
                    'vacation',
                    [('true',)],
                    [
                            (
                                    "vacation",
                                    ":days", 1,
                                    ":subject",
                                    "Out of Office",
                                    # ":handle", see http://tools.ietf.org/html/rfc5230#page-4
                                    # ":mime", to indicate the reason is in fact MIME
                                    vacation_text
                                )
                        ]
                )

    if forward_active:
        forward_rules = []

        # Principle can be demonstrated by:
        #
        # python -c "print ','.join(['a','b','c'][:-1])"
        #
        for forward_copy in forward_addresses[:-1]:
            forward_rules.append(("redirect", ":copy", forward_copy))

        if forward_keepcopy:
            # Principle can be demonstrated by:
            #
            # python -c "print ','.join(['a','b','c'][-1])"
            #
            if forward_uce:
                rule_name = 'forward-uce-keepcopy'
            else:
                rule_name = 'forward-keepcopy'

            forward_rules.append(("redirect", ":copy", forward_addresses[-1]))
        else:
            if forward_uce:
                rule_name = 'forward-uce'
            else:
                rule_name = 'forward'

            forward_rules.append(("redirect", forward_addresses[-1]))
            forward_rules.append(("stop"))

        if forward_uce:
            mgmt_script.addfilter(rule_name, ['true'], forward_rules)

        else:
            mgmt_script.addfilter(rule_name, [("X-Spam-Status", ":matches", "No,*")], forward_rules)

    if sdf_filter:
        mgmt_script.addfilter('spam_delivery_folder', [("X-Spam-Status", ":matches", "Yes,*")], [("fileinto", "INBOX/Spam"), ("stop")])

    if dtf_active:
        mgmt_script.addfilter('delivery_to_folder', ['true'], [("fileinto", dtf_folder)])

    mgmt_script = mgmt_script.__str__()

    log.debug(_("MANAGEMENT script for user %s contents: %r") % (address,mgmt_script), level=9)

    result = sieveclient.putscript("MANAGEMENT", mgmt_script)

    if not result:
        log.error(_("Uploading script MANAGEMENT failed for user %s") % (address))
    else:
        log.debug(_("Uploading script MANAGEMENT for user %s succeeded") % (address), level=8)

    user_script = """#
# User
#

require ["include"];
"""

    for script in scripts:
        if not script in [ "MASTER", "MANAGEMENT", "USER" ]:
            log.debug(_("Including script %s in USER (for user %s)") % (script,address) ,level=8)
            user_script = """%s

include :personal "%s";
""" % (user_script, script)

    result = sieveclient.putscript("USER", user_script)

    if not result:
        log.error(_("Uploading script USER failed for user %s") % (address))
    else:
        log.debug(_("Uploading script USER for user %s succeeded") % (address), level=8)

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
        log.error(_("Uploading script MASTER failed for user %s") % (address))
    else:
        log.debug(_("Uploading script MASTER for user %s succeeded") % (address), level=8)

    sieveclient.setactive("MASTER")
