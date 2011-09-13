# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
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

import ldap
import ldif
import logging
import traceback
import shutil
import sys
import time

from ldap.modlist import addModlist

import pykolab
import pykolab.plugins

from pykolab import utils
from pykolab import conf
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

auth = pykolab.auth
imap = pykolab.imap

class Cli(object):
    def __init__(self):
        domain_group = conf.add_cli_parser_option_group(_("CLI Options"))

        domain_group.add_option(    '--review',
                                    dest    = "review",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Review LDIF before committed"))

        conf.finalize_conf()

        try:
            action = conf.cli_args.pop(0)
        except IndexError, e:
            self.no_command()

        action_function = action.replace('-','_')
        action_components = action.split('-')

        if hasattr(self, "action_%s" %(action)):
            exec("self.action_%s()" %(action))
        elif hasattr(self, "action_%s" %(action_function)):
            log.info(_("TODO: self.check_%s()") %(action_function))
            exec("self.action_%s()" %(action_function))
        else:
            try:
                action_domain = action_components.pop()
                action_action = action_components.pop()
                exec("from pykolab.cli import action_%s" %(action_domain))
                if hasattr("action_%s" %(action_domain), "%s" %(action_action)):
                    exec("result = action_%s.%s(%r)" %(action_domain,action_action,conf.cli_args))
            except ImportError, e:
                pass

            self.print_usage()

    def no_command(self):
        print >> sys.stderr, _("No command given, see --help for details")
        sys.exit(1)

    def action_sync(self):
        log.debug(_("Listing domains..."), level=5)
        start_time = time.time()
        domains = auth.list_domains()
        end_time = time.time()
        log.debug(_("Found %d domains in %d seconds") %(len(domains),(end_time-start_time)), level=8)

        all_folders = []

        for primary_domain,secondary_domains in domains:
            #print "Running for domain %s" %(primary_domain)
            auth.connect(primary_domain)
            start_time = time.time()
            auth.synchronize(primary_domain, secondary_domains)
            end_time = time.time()

            log.info(_("Synchronizing users for %s took %d seconds")
                    %(primary_domain, (end_time-start_time))
                )

    def action_list_deleted(self):
        """
            List deleted mailboxes
        """
        imap.connect()
        folders = imap.lm("DELETED/*")
        print "Deleted folders:"
        for folder in folders:
            print folder

    def action_delete(self):
        """
            Delete mailbox
        """

        target_folder = None

        delete_folder = conf.cli_args.pop(0)

        imap.connect()
        imap.delete(delete_folder)

    def action_undelete(self):
        """
            Undelete mailbox
        """

        target_folder = None

        undelete_folder = conf.cli_args.pop(0)
        if len(conf.cli_args) > 0:
            target_folder = conf.cli_args.pop(0)

        imap.connect()
        imap.undelete(undelete_folder, target_folder)

    def action_add_domain(self):
        log.info(_("TODO: Figure out where the domain should actually be added."))

        domainname = conf.cli_args.pop(0)

        log.info(_("Adding domain %s") %(domainname))

        # The dn of our new entry/object
        log.info(_("TODO: Make the format for a new domain configurable."))
        dn = "associateddomain=%s,cn=kolab,cn=config" %(domainname)

        # A dict to help build the "body" of the object
        log.info(_("TODO: Make what a domain looks like configurable."))
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

        log.info(_("TODO: Prompt for organization name/description. For now, use domain name."))
        attrs['o'] = ['%s' %(domainname)]

        go_ahead = True

        if conf.cli_keywords.review:
            ldif_writer = ldif.LDIFWriter(sys.stdout)
            ldif_writer.unparse(dn,attrs)
            if not utils.ask_confirmation(_("Please ACK or NACK the above LDIF:"), default="y", all_inclusive_no=True):
                go_ahead = False

        if go_ahead:
            # Convert our dict to nice syntax for the add-function using modlist-module
            _ldif = addModlist(attrs)

            # Now build an ldap connection and execute the motherf.
            ldap_con = ldap.initialize(conf.get('ldap', 'uri'))
            ldap_con.bind_s(conf.get('ldap', 'bind_dn'), conf.get('ldap', 'bind_pw'))

            # The try/except should actually be in check_add_domain
            try:
                # Do the actual synchronous add-operation to the ldapserver
                ldap_con.add_s(dn,_ldif)
            except ldap.ALREADY_EXISTS, e:
                log.error(_("Domain %s already exists.") %(domainname))

            # Its nice to the server to disconnect and free resources when done
            ldap_con.unbind_s()

    def action_del_domain(self):
        domainname = conf.cli_args.pop(0)

        log.info(_("Deleting domain %s") %(domainname))

        dn = "associateddomain=%s,cn=kolab,cn=config" %(domainname)

        ldap_con = ldap.initialize(conf.get('ldap', 'uri'))
        ldap_con.bind_s(conf.get('ldap', 'bind_dn'), conf.get('ldap', 'bind_pw'))

        # The try/except should actually be in check_del_domain()
        try:
            # Do the actual synchronous add-operation to the ldapserver
            ldap_con.delete_s(dn)
        except ldap.NO_SUCH_OBJECT, e:
            log.error(_("No domain %s exists.") %(domainname))

        # Its nice to the server to disconnect and free resources when done
        ldap_con.unbind_s()

    def action_export(self):
        import os
        import subprocess

        user = conf.cli_args.pop(0)

        # TODO: /etc/imapd.conf is not the definitive location for the
        # imapd.conf configuration file.
        partition_proc = subprocess.Popen(['grep', '^partition', '/etc/imapd.conf'], stdout=subprocess.PIPE)

        partitions = [x.split(':')[1].strip() for x in partition_proc.communicate()[0].split('\n') if len(x.split(':')) > 1]

        # TODO: ctl_mboxlist is not necessarily in this location.
        ctl_mboxlist_args = [ '/usr/lib/cyrus-imapd/ctl_mboxlist', '-d' ]
        ctl_mboxlist = subprocess.Popen(ctl_mboxlist_args, stdout=subprocess.PIPE)

        mboxlist_proc = subprocess.Popen(['grep', '-E', '\s*%s\s*.*i.*p.*' %(user)], stdin=ctl_mboxlist.stdout, stdout=subprocess.PIPE)
        ctl_mboxlist.stdout.close()

        mboxlist_output = mboxlist_proc.communicate()[0]

        directories = []

        for mbox_internal in mboxlist_output.split('\n'):
            if len(mbox_internal.split('\t')[0].split('!')) > 1:
                domain = mbox_internal.split('\t')[0].split('!')[0]
                mailbox = '/'.join(mbox_internal.split('\t')[0].split('!')[1].split('.')[1:])

                zipper_args = [
                        'zip',
                        '-r',
                        '%s.zip' %(user)
                    ]

                for partition in partitions:
                    if os.path.isdir('%s/domain/%s/%s/%s/user/%s/' %(partition,domain[0],domain,user[0],mailbox)):
                        directories.append('%s/domain/%s/%s/%s/user/%s/' %(partition,domain[0],domain,user[0],mailbox))
                    else:
                        log.debug(_('%s/domain/%s/%s/%s/user/%s/ is not a directory') %(partition,domain[0],domain,user[0],mailbox), level=5)

        zipper_output = subprocess.Popen(zipper_args + directories, stdout=subprocess.PIPE).communicate()[0]
        print >> sys.stderr, _("ZIP file at %s.zip") %(user)

    def action_list_domains(self):
        # Create the authentication object.
        # TODO: Binds with superuser credentials!
        domains = auth.list_domains()

        # TODO: Take a hint in --quiet, and otherwise print out a nice table
        # with headers and such.
        for domain,domain_aliases in domains:
            print _("Primary domain: %s - Secondary domain(s): %s") %(domain, ', '.join(domain_aliases))

    def run(self):
        pass

    def print_usage(self):
        print >> sys.stderr, _("Actions") + ":"
        print >> sys.stderr, "add-domain <domainname>"
        print >> sys.stderr, "list-domains"
