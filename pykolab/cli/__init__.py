# -*- coding: utf-8 -*-
# Copyright 2010 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 only
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

import ldap
import ldif
import traceback
import shutil
import sys

from ldap.modlist import addModlist

import pykolab
import pykolab.plugins

from pykolab import utils
from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.translate import _

class Cli(object):
    def __init__(self):
        self.conf = Conf()

        domain_group = self.conf.parser.add_option_group(_("Domain Options"))
        domain_group.add_option(    '--review',
                                    dest    = "review",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Review LDIF before committed"))

        self.conf.finalize_conf()

        # The first argument has to be a command
        action = self.conf.args.pop(0)
        action_function = action.replace('-','_')
        action_components = action.split('-')

        if hasattr(self, "action_%s" %(action_function)):
            self.conf.log.info(_("TODO: self.check_%s()") %(action_function))
            exec("self.action_%s()" %(action_function))
        else:
            try:
                action_domain = action_components.pop()
                action_action = action_components.pop()
                exec("from pykolab.cli import action_%s" %(action_domain))
                if hasattr("action_%s" %(action_domain), "%s" %(action_action)):
                    exec("result = action_%s.%s(%r)" %(action_domain,action_action,self.conf.args))
            except ImportError, e:
                pass

            self.print_usage()

    def action_list_domains(self):
        ldap_con = ldap.initialize(self.conf.get('ldap', 'uri'))
        ldap_con.bind_s(self.conf.get('ldap', 'bind_dn'), self.conf.get('ldap', 'bind_pw'))

        results = ldap_con.search_s('cn=kolab,cn=config', ldap.SCOPE_ONELEVEL, '(objectClass=*)', ['associatedDomain'])

        for dn,entry in results:
            print ''.join(entry['associatedDomain'])

    def action_del_domain(self):
        domainname = self.conf.args.pop(0)

        self.conf.log.info(_("Deleting domain %s") %(domainname))

        dn = "associateddomain=%s,cn=kolab,cn=config" %(domainname)

        ldap_con = ldap.initialize(self.conf.get('ldap', 'uri'))
        ldap_con.bind_s(self.conf.get('ldap', 'bind_dn'), self.conf.get('ldap', 'bind_pw'))

        # The try/except should actually be in check_del_domain()
        try:
            # Do the actual synchronous add-operation to the ldapserver
            ldap_con.delete_s(dn)
        except ldap.NO_SUCH_OBJECT, e:
            self.conf.log.error(_("No domain %s exists.") %(domainname))

        # Its nice to the server to disconnect and free resources when done
        ldap_con.unbind_s()

    def action_add_domain(self):
        self.conf.log.info(_("TODO: Figure out where the domain should actually be added."))

        domainname = self.conf.args.pop(0)

        self.conf.log.info(_("Adding domain %s") %(domainname))

        # The dn of our new entry/object
        self.conf.log.info(_("TODO: Make the format for a new domain configurable."))
        dn = "associateddomain=%s,cn=kolab,cn=config" %(domainname)

        # A dict to help build the "body" of the object
        self.conf.log.info(_("TODO: Make what a domain looks like configurable."))
        attrs = {}
        attrs['objectclass'] = [
                'top',
                'domainrelatedobject',
                'organization',
                'inetdomain'
            ]
        attrs['associatedDomain'] = ['%s' %(domainname)]
        domainname_components = domainname.split('.')
        attrs['inetDomainBaseDN'] = ['dc=%s,dc=%s' %(domainname_components[0],domainname_components[1])]

        self.conf.log.info(_("TODO: Prompt for organization name/description. For now, use domain name."))
        attrs['o'] = ['%s' %(domainname)]

        go_ahead = True

        if self.conf.cli_options.review:
            ldif_writer = ldif.LDIFWriter(sys.stdout)
            ldif_writer.unparse(dn,attrs)
            if not utils.ask_confirmation(_("Please ACK or NACK the above LDIF:"), default="y", all_inclusive_no=True):
                go_ahead = False

        if go_ahead:
            # Convert our dict to nice syntax for the add-function using modlist-module
            _ldif = addModlist(attrs)

            # Now build an ldap connection and execute the motherf.
            ldap_con = ldap.initialize(self.conf.get('ldap', 'uri'))
            ldap_con.bind_s(self.conf.get('ldap', 'bind_dn'), self.conf.get('ldap', 'bind_pw'))

            # The try/except should actually be in check_add_domain
            try:
                # Do the actual synchronous add-operation to the ldapserver
                ldap_con.add_s(dn,_ldif)
            except ldap.ALREADY_EXISTS, e:
                self.conf.log.error(_("Domain %s already exists.") %(domainname))

            # Its nice to the server to disconnect and free resources when done
            ldap_con.unbind_s()
#

    def run(self):
        pass

    def print_usage(self):
        print >> sys.stderr, _("Actions") + ":"
        print >> sys.stderr, "add-domain <domainname>"