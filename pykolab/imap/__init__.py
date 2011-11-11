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


import logging
import re
import time
import sys

from urlparse import urlparse

import pykolab
from pykolab.translate import _

log = pykolab.getLogger('pykolab.imap')
conf = pykolab.getConf()

auth = pykolab.auth

class IMAP(object):
    def __init__(self):
        # Pool of named IMAP connections, by hostname
        self._imap = {}

        # Place holder for the current IMAP connection
        self.imap = None

        self.users = []
        self.inbox_folders = []

    def connect(self, uri=None, login=True):
        backend = conf.get('kolab', 'imap_backend')

        hostname = None
        port = None

        if uri == None:
            uri = conf.get(backend, 'uri')

        result = urlparse(uri)

        if hasattr(result, 'hostname'):
            hostname = result.hostname
        else:
            scheme = uri.split(':')[0]
            (hostname, port) = uri.split('/')[2].split(':')

        if port == None:
            port = 993

        # Get the credentials
        admin_login = conf.get(backend, 'admin_login')
        admin_password = conf.get(backend, 'admin_password')

        if not self._imap.has_key(hostname):
            if backend == 'cyrus-imap':
                import cyrus
                self._imap[hostname] = cyrus.Cyrus(uri)
                # Actually connect
                if login:
                    log.debug(_("Logging on to Cyrus IMAP server %s") %(hostname), level=8)
                    self._imap[hostname].login(admin_login, admin_password)

            elif backend == 'dovecot':
                import dovecot
                self._imap[hostname] = dovecot.Dovecot(uri)
                # Actually connect
                if login:
                    log.debug(_("Logging on to Dovecot IMAP server %s") %(hostname), level=8)
                    self._imap[hostname].login(admin_login, admin_password)

            else:
                import imaplib
                self._imap[hostname] = imaplib.IMAP4(hostname, port)
                # Actually connect
                if login:
                    log.debug(_("Logging on to generic IMAP server %s") %(hostname), level=8)
                    self._imap[hostname].login(admin_login, admin_password)
        else:
            log.debug(_("Reusing existing IMAP server connection to %s") %(hostname), level=8)

        # Set the newly created technology specific IMAP library as the current
        # IMAP connection to be used.
        self.imap = self._imap[hostname]

    def disconnect(self, server=None):
        if server == None:
            # No server specified, but make sure self.imap is None anyways
            self.imap = None
        else:
            if self._imap.has_key(server):
                del self._imap[server]
            else:
                log.warning(_("Called imap.disconnect() on a server that " + \
                    "we had no connection to"))

    def __getattr__(self, name):
        if hasattr(self.imap, name):
            return getattr(self.imap, name)
        else:
            raise AttributeError, _("%r has no attribute %s") %(self,name)

    def has_folder(self, folder):
        folders = self.imap.lm(folder)
        log.debug(_("Looking for folder '%s', we found folders: %r") %(folder,folders), level=8)
        # Greater then one, this folder may have subfolders.
        if len(folders) > 0:
            return True
        else:
            return False

    def move_user_folders(self, users=[]):
        for user in users:
            if type(user) == dict:
                if user.has_key('old_mail'):
                    inbox = "user/%s" %(user['mail'])
                    old_inbox = "user/%s" %(user['old_mail'])

                    if self.has_folder(old_inbox):
                        log.debug(_("Found old INBOX folder %s") %(old_inbox), level=8)

                        if not self.has_folder(inbox):
                            log.info(_("Renaming INBOX from %s to %s") %(old_inbox,inbox))
                            self.imap.rename(old_inbox,inbox)
                            self.inbox_folders.append(inbox)
                        else:
                            log.warning(_("Moving INBOX folder %s won't succeed as target folder %s already exists") %(old_inbox,inbox))
                    else:
                        log.debug(_("Did not find old folder user/%s to rename") %(user['old_mail']), level=8)
            else:
                log.debug(_("Value for user is not a dictionary"), level=8)

    def create_user_folders(self, users, primary_domain, secondary_domains):
        inbox_folders = []

        domain_section = auth.domain_section(primary_domain)

        folders = self.list_user_folders(primary_domain, secondary_domains)

        # See if the folder belongs to any of the users
        _match_attr = conf.get('cyrus-sasl', 'result_attribute')

        if not users:
            users = auth.list_users(primary_domain)

        for user in users:
            if type(user) == dict:
                if user.has_key(_match_attr):
                    inbox_folders.append(user[_match_attr].lower())
                else:
                    # If the user passed on to this function does not have
                    # a key for _match_attr, then we have to bail out and
                    # continue
                    continue

            elif type(user) == str:
                inbox_folders.append(user.lower())

        for folder in inbox_folders:
            additional_folders = None
            try:
                if folders.index(folder) > -1:
                    continue
                else:
                    # TODO: Perhaps this block is moot
                    log.info(_("Creating new INBOX for user (%d): %s")
                        %(1,folder))
                    try:
                        self.imap.cm("user/%s" %(folder))
                    except:
                        log.warning(_("Mailbox already exists: user/%s")
                            %(folder))
                        continue
                    if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                        self.imap._setquota("user/%s" %(folder),0)

            except:
                # TODO: Perhaps this block is moot
                log.info(_("Creating new INBOX for user (%d): %s") %(2,folder))
                try:
                    self.imap.cm("user/%s" %(folder))
                except:
                    log.warning(_("Mailbox already exists: user/%s") %(folder))
                    continue
                self.imap._setquota("user/%s" %(folder),0)

            if conf.has_option(domain_section, "autocreate_folders"):
                _additional_folders = conf.get_raw(domain_section, "autocreate_folders")
                additional_folders = conf.plugins.exec_hook("create_user_folders",
                        kw={
                                'folder': folder,
                                'additional_folders': _additional_folders
                            }
                    )

            if not additional_folders == None:
                self.create_user_additional_folders(folder, additional_folders)

        return inbox_folders

    def create_user_additional_folders(self, folder, additional_folders):
        self.connect()

        for additional_folder in additional_folders.keys():
            _add_folder = {}
            if len(folder.split('@')) > 1:
                folder_name = "user%(separator)s%(username)s%(separator)s%(additional_folder_name)s@%(domainname)s"
                _add_folder['username'] = folder.split('@')[0]
                _add_folder['domainname'] = folder.split('@')[1]
                _add_folder['additional_folder_name'] = additional_folder
                _add_folder['separator'] = self.imap.separator
                folder_name = folder_name % _add_folder
            else:
                folder_name = "user%(separator)s%(username)s%(separator)s%(additional_folder_name)s" % {
                        "username": folder,
                        "separator": self.imap.separator,
                        "additional_folder_name": additional_folder
                    }

            try:
                self.imap.cm(folder_name)
            except:
                log.warning(_("Mailbox already exists: user/%s") %(folder))

            if additional_folders[additional_folder].has_key("annotations"):
                for annotation in additional_folders[additional_folder]["annotations"].keys():
                    if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                        self.imap._setannotation(
                                folder_name,
                                "%s" %(annotation),
                                "%s" %(additional_folders[additional_folder]["annotations"][annotation])
                            )

            if additional_folders[additional_folder].has_key("acls"):
                for acl in additional_folders[additional_folder]["acls"].keys():
                    self.imap.sam(
                            folder_name,
                            "%s" %(acl),
                            "%s" %(additional_folders[additional_folder]["acls"][acl])
                        )

    def set_user_folder_quota(self, users=[], primary_domain=None, secondary_domain=[], folders=[]):
        """

            Sets the quota in IMAP using the authentication and authorization
            database 'quota' attribute for the users listed in parameter 'users'
        """

        self.connect()

        if conf.has_option(primary_domain, 'quota_attribute'):
            _quota_attr = conf.get(primary_domain, 'quota_attribute')
        else:
            auth_mechanism = conf.get('kolab', 'auth_mechanism')
            _quota_attr = conf.get(auth_mechanism, 'quota_attribute')

        _inbox_folder_attr = conf.get('cyrus-sasl', 'result_attribute')

        default_quota = auth.domain_default_quota(primary_domain)

        if default_quota == "" or default_quota == None:
            default_quota = 0

        if len(users) == 0:
            users = auth.list_users(primary_domain)

        for user in users:
            quota = None

            if type(user) == dict:
                if user.has_key(_quota_attr):
                    if type(user[_quota_attr]) == list:
                        quota = user[_quota_attr].pop(0)
                    elif type(user[_quota_attr]) == str:
                        quota = user[_quota_attr]
                else:
                    _quota = auth.get_user_attribute(primary_domain, user, _quota_attr)
                    if _quota == None:
                        quota = 0
                    else:
                        quota = _quota

                if not user.has_key(_inbox_folder_attr):
                    continue
                else:
                    if type(user[_inbox_folder_attr]) == list:
                        folder = "user/%s" % user[_inbox_folder_attr].pop(0)
                    elif type(user[_inbox_folder_attr]) == str:
                        folder = "user/%s" % user[_inbox_folder_attr]
            elif type(user) == str:
                quota = auth.get_user_attribute(user, 'quota')
                folder = "user/%s" %(user)

            folder = folder.lower()

            try:
                (used,current_quota) = self.imap.lq(folder)
            except:
                # TODO: Go in fact correct the quota.
                log.warning(_("Cannot get current IMAP quota for folder %s") %(folder))
                used = 0
                current_quota = 0

            new_quota = conf.plugins.exec_hook("set_user_folder_quota", kw={
                        'used': used,
                        'current_quota': current_quota,
                        'new_quota': (int)(quota),
                        'default_quota': (int)(default_quota)
                    }
                )

            log.debug(_("Quota for %s currently is %s") %(folder, current_quota), level=7)

            if new_quota == None:
                continue

            if not int(new_quota) == int(quota):
                log.info(_("Adjusting authentication database quota for folder %s to %d") %(folder,int(new_quota)))
                quota = int(new_quota)
                auth.set_user_attribute(primary_domain, user, _quota_attr, new_quota)

            if not int(current_quota) == int(quota):
                log.info(_("Correcting quota for %s to %s (currently %s)") %(folder, quota, current_quota))
                self.imap._setquota(folder, quota)

    def set_user_mailhost(self, users=[], primary_domain=None, secondary_domain=[], folders=[]):
        self.connect()

        if conf.has_option(primary_domain, 'mailserver_attribute'):
            _mailserver_attr = conf.get(primary_domain, 'mailserver_attribute')
        else:
            auth_mechanism = conf.get('kolab', 'auth_mechanism')
            _mailserver_attr = conf.get(auth_mechanism, 'mailserver_attribute')

        _inbox_folder_attr = conf.get('cyrus-sasl', 'result_attribute')

        if len(users) == 0:
            users = auth.list_users(primary_domain)

        for user in users:
            mailhost = None

            if type(user) == dict:
                if user.has_key(_mailserver_attr):
                    if type(user[_mailserver_attr]) == list:
                        _mailserver = user[_mailserver_attr].pop(0)
                    elif type(user[_mailserver_attr]) == str:
                        _mailserver = user[_mailserver_attr]
                else:
                    _mailserver = auth.get_user_attribute(primary_domain, user, _mailserver_attr)

                if not user.has_key(_inbox_folder_attr):
                    continue
                else:
                    if type(user[_inbox_folder_attr]) == list:
                        folder = "user/%s" % user[_inbox_folder_attr].pop(0)
                    elif type(user[_inbox_folder_attr]) == str:
                        folder = "user/%s" % user[_inbox_folder_attr]

            elif type(user) == str:
                _mailserver = auth.get_user_attribute(user, _mailserver_attr)
                folder = "user/%s" %(user)

            folder = folder.lower()

            _current_mailserver = self.imap.find_mailfolder_server(folder)

            if not _mailserver == None:
                # TODO:
                if not _current_mailserver == _mailserver:
                    self.imap._xfer(folder, _current_mailserver, _mailserver)
            else:
                auth.set_user_attribute(primary_domain, user, _mailserver_attr, _current_mailserver)

    def parse_mailfolder(self, mailfolder):
        self.connect()
        return self.imap.parse_mailfolder(mailfolder)

    def expunge_user_folders(self, inbox_folders=None):
        """
            Delete folders that have no equivalent user qualifier in the list
            of users passed to this function, ...

            TODO: Explain the domain parameter, and actually get it to work
                  properly. This also relates to threading for multi-domain
                  deployments.

            Parameters:

                users
                        A list of users. Can be a list of user qualifiers, e.g.
                        [ 'user1', 'user2' ] or a list of user attribute
                        dictionaries, e.g. [ { 'user1': { 'attr': 'value' } } ]

                primary_domain, secondary_domains
        """
        self.connect()

        if inbox_folders == None:
            inbox_folders = []

        folders = self.list_user_folders()

        for folder in folders:
            log.debug(_("Checking folder: %s") %(folder), level=1)
            try:
                if inbox_folders.index(folder) > -1:
                    continue
                else:
                    log.info(_("Folder has no corresponding user (1): %s") %(folder))
                    self.delete_mailfolder("user/%s" %(folder))
            except:
                log.info(_("Folder has no corresponding user (2): %s") %(folder))
                try:
                    self.delete_mailfolder("user/%s" %(folder))
                except:
                    pass

    def delete_mailfolder(self, mailfolder_path):
        """
            Deletes a mail folder described by mailfolder_path.
        """

        mbox_parts = self.parse_mailfolder(mailfolder_path)

        if mbox_parts == None:
            # We got user identifier only
            log.error(_("Please don't give us just a user identifier"))
            return

        self.imap.dm(mailfolder_path)

        clean_acls = False

        section = False

        if mbox_parts['domain']:
            if conf.has_option(mbox_parts['domain'], 'delete_clean_acls'):
                section = mbox_parts['domain']
            elif conf.has_option('kolab', 'delete_clean_acls'):
                section = 'kolab'
        elif conf.has_option('kolab', 'delete_clean_acls'):
            section = 'kolab'

        if not section == False:
            clean_acls = conf.get(section, 'delete_clean_acls')

        if not clean_acls == False and not clean_acls == 0:
            log.info(_("Cleaning up ACL entries across all folders"))

            if mbox_parts['domain']:
                # List the shared and user folders
                shared_folders = self.imap.lm(
                        "shared/*@%s" %(mbox_parts['domain'])
                    )

                user_folders = self.imap.lm(
                        "user/*@%s" %(mbox_parts['domain'])
                    )

                aci_identifier = "%s@%s" %(
                        mbox_parts['path_parts'][1],
                        mbox_parts['domain']
                    )

            else:
                shared_folders = self.imap.lm("shared/*")
                user_folders = self.imap.lm("user/*")
                aci_identifier = "%s" %(mbox_parts['path_parts'][1])

            log.debug(
                    _("Cleaning up ACL entries referring to identifier %s") %(
                            aci_identifier
                        ),
                    level=5
                )

            # For all folders (shared and user), ...
            folders = user_folders + shared_folders

            log.debug(_("Iterating over %d folders") %(len(folders)), level=5)

            # ... loop through them and ...
            for folder in folders:
                # ... list the ACL entries
                acls = self.imap.lam(folder)

                # For each ACL entry, see if we think it is a current, valid entry
                for acl_entry in acls.keys():
                    # If the key 'acl_entry' does not exist in the dictionary of valid
                    # ACL entries, this ACL entry has got to go.
                    if acl_entry == aci_identifier:
                        # Set the ACL to '' (effectively deleting the ACL entry)
                        self.imap.sam(folder, acl_entry, '')

    def list_user_folders(self, primary_domain=None, secondary_domains=[]):
        """
            List the INBOX folders in the IMAP backend. Returns a list of unique
            base folder names.
        """
        self.connect()

        _folders = self.imap.lm("user/%")
        # TODO: Replace the .* below with a regex representing acceptable DNS
        # domain names.
        domain_re = ".*\.?%s$"

        acceptable_domain_name_res = []

        if not primary_domain == None:
            for domain in [ primary_domain ] + secondary_domains:
                acceptable_domain_name_res.append(domain_re %(domain))

        folders = []

        for folder in _folders:
            folder_name = None
            if len(folder.split('@')) > 1:
                # TODO: acceptable domain name spaces
                #acceptable = False
                #for domain_name_re in acceptable_domain_name_res:
                    #prog = re.compile(domain_name_re)
                    #if prog.match(folder.split('@')[1]):
                        #print "Acceptable indeed"
                        #acceptable = True
                    #if not acceptable:
                        #print "%s is not acceptable against %s yet using %s" %(folder.split('@')[1],folder,domain_name_re)

                #if acceptable:
                    #folder_name = "%s@%s" %(folder.split(self.separator)[1].split('@')[0],folder.split('@')[1])

                folder_name = "%s@%s" %(folder.split(self.imap.separator)[1].split('@')[0],folder.split('@')[1])
            else:
                folder_name = "%s" %(folder.split(self.imap.separator)[1])

            if not folder_name == None:
                if not folder_name in folders:
                    folders.append(folder_name)

        return folders

    def synchronize(self, users=[], primary_domain=None, secondary_domains=[]):
        self.connect()
        self.users.extend(users)

        self.move_user_folders(users)

        self.inbox_folders.extend(self.create_user_folders(users, primary_domain, secondary_domains))

        self.set_user_folder_quota(users, primary_domain, secondary_domains, self.inbox_folders)

        self.set_user_mailhost(users, primary_domain, secondary_domains, self.inbox_folders)

    def lm(self, *args, **kw):
        return self.imap.lm(*args, **kw)

    def undelete_mailfolder(self, *args, **kw):
        self.imap.undelete_mailfolder(*args, **kw)
