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


import logging
import re
import time
import sys

from urlparse import urlparse

import pykolab
from pykolab.translate import _

log = pykolab.getLogger('pykolab.imap')
conf = pykolab.getConf()

class IMAP(object):
    def __init__(self):
        # Pool of named IMAP connections, by hostname
        self._imap = {}

        # Place holder for the current IMAP connection
        self.imap = None

    def cleanup_acls(self, aci_subject):
        lm_suffix = ""

        log.info(_("Cleaning up ACL entries for %s across all folders") % (aci_subject))

        if len(aci_subject.split('@')) > 1:
            lm_suffix = "@%s" % (aci_subject.split('@')[1])


        shared_folders = self.imap.lm(
                "shared/*%s" % (lm_suffix)
            )

        user_folders = self.imap.lm(
                "user/*%s" % (lm_suffix)
            )

        log.debug(
                _("Cleaning up ACL entries referring to identifier %s") % (
                        aci_subject
                    ),
                level=5
            )

        # For all folders (shared and user), ...
        folders = user_folders + shared_folders

        log.debug(_("Iterating over %d folders") % (len(folders)), level=5)

        # ... loop through them and ...
        for folder in folders:
            # ... list the ACL entries
            acls = self.imap.lam(folder)

            # For each ACL entry, see if we think it is a current, valid entry
            for acl_entry in acls.keys():
                # If the key 'acl_entry' does not exist in the dictionary of valid
                # ACL entries, this ACL entry has got to go.
                if acl_entry == aci_subject:
                    # Set the ACL to '' (effectively deleting the ACL entry)
                    log.debug(_("Removing acl %r for subject %r from folder %r") % (acls[acl_entry],acl_entry,folder), level=8)
                    self.imap.sam(folder, acl_entry, '')

    def connect(self, uri=None, server=None, domain=None, login=True):
        """
            Connect to the appropriate IMAP backend.

            Supply a domain (name space) configured in the configuration file
            as a section, with a setting 'imap_uri' to connect to a domain
            specific IMAP server, or specify an URI to connect to that
            particular IMAP server (in that order).

            Routines sitting behind this will take into account Cyrus IMAP
            Murder capabilities, brokering actions to take place against the
            correct server (such as a 'xfer' which needs to happen against the
            source backend).
        """

        # TODO: We are currently compatible with one IMAP backend technology per
        # deployment.
        backend = conf.get('kolab', 'imap_backend')

        if not domain == None:
            self.domain = domain
            if conf.has_section(domain) and conf.has_option(domain, 'imap_backend'):
                backend = conf.get(domain, 'imap_backend')

            if uri == None:
                if conf.has_section(domain) and conf.has_option(domain, 'imap_uri'):
                    uri = conf.get(domain, 'imap_uri')

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

        if not server == None:
            hostname = server

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
                    log.debug(_("Logging on to Cyrus IMAP server %s") % (hostname), level=8)
                    self._imap[hostname].login(admin_login, admin_password)
                    self._imap[hostname].logged_in = True

            elif backend == 'dovecot':
                import dovecot
                self._imap[hostname] = dovecot.Dovecot(uri)
                # Actually connect
                if login:
                    log.debug(_("Logging on to Dovecot IMAP server %s") % (hostname), level=8)
                    self._imap[hostname].login(admin_login, admin_password)
                    self._imap[hostname].logged_in = True

            else:
                import imaplib
                self._imap[hostname] = imaplib.IMAP4(hostname, port)
                # Actually connect
                if login:
                    log.debug(_("Logging on to generic IMAP server %s") % (hostname), level=8)
                    self._imap[hostname].login(admin_login, admin_password)
                    self._imap[hostname].logged_in = True

        else:
            if not login and self._imap[hostname].logged_in == True:
                self.disconnect(hostname)
                self.connect(uri=uri,login=False)
            elif login and not hasattr(self._imap[hostname],'logged_in'):
                self.disconnect(hostname)
                self.connect(uri=uri)
            else:
                try:
                    if hasattr(self._imap[hostname], 'm'):
                        self._imap[hostname].m.noop()
                    elif hasattr(self._imap[hostname], 'noop') and callable(self._imap[hostname].noop):
                        self._imap[hostname].noop()

                    log.debug(_("Reusing existing IMAP server connection to %s") % (hostname), level=8)
                except:
                    log.debug(_("Reconnecting to IMAP server %s") % (hostname), level=8)
                    self.disconnect(hostname)
                    self.connect()

        # Set the newly created technology specific IMAP library as the current
        # IMAP connection to be used.
        self.imap = self._imap[hostname]

    def disconnect(self, server=None):
        if server == None:
            # No server specified, but make sure self.imap is None anyways
            del self.imap
        else:
            if self._imap.has_key(server):
                del self._imap[server]
            else:
                log.warning(_("Called imap.disconnect() on a server that " + \
                    "we had no connection to"))

    def create_folder(self, folder_path, server=None):
        if not server == None:
            if not self._imap.has_key(server):
                self.connect(server=server)

            self._imap[server].cm(folder_path)
        else:
            self.imap.cm(folder_path)

    def __getattr__(self, name):
        if hasattr(self.imap, name):
            return getattr(self.imap, name)
        else:
            raise AttributeError, _("%r has no attribute %s") % (self,name)

    def get_metadata(self, folder):
        """
            Obtain all metadata entries on a folder
        """

        return self.imap.getannotation(folder, '*')

    def namespaces(self):
        """
            Obtain the namespaces.

            Returns a tuple of:

                (str(personal) [, str(other users) [, list(shared)]])
        """

        _personal = None
        _other_users = None
        _shared = None

        (_response, _namespaces) = self.imap.m.namespace()

        if len(_namespaces) == 1:
            _namespaces = _namespaces[0]

        _namespaces = re.split(r"\)\)\s\(\(", _namespaces)

        _other_users = [
                ''.join(_namespaces[1].replace('((','').replace('))','').split()[-1])
            ]

        if len(_namespaces) >= 3:
            _shared = []
            _shared.append(' '.join(_namespaces[2].replace('((','').replace('))','').split()[:-1]))

        if len(_namespaces) >= 2:
            _other_users = ' '.join(_namespaces[1].replace('((','').replace('))','').split()[:-1])

        if len(_namespaces) >= 1:
            _personal = _namespaces[0].replace('((','').replace('))','').split()[0]

        return (_personal, _other_users, _shared)

    def set_acl(self, folder, identifier, acl):
        """
            Set an ACL entry on a folder.
        """

        self.imap.sam(folder, identifier, acl)

    def set_metadata(self, folder, metadata_path, metadata_value, shared=True):
        """
            Set a metadata entry on a folder
        """

        if metadata_path.startswith('/shared/'):
            shared = True

        if metadata_path.startswith('/shared/'):
            metadata_path = metadata_path.replace('/shared/', '/')
        elif metadata_path.startswith('/private/'):
            shared = False
            metadata_path = metadata_path.replace('/private/', '/')

        backend = conf.get('kolab', 'imap_backend')

        if not self.domain == None:
            if conf.has_section(self.domain) and conf.has_option(self.domain, 'imap_backend'):
                backend = conf.get(self.domain, 'imap_backend')

        if not shared:
            log.warning(_("Private annotations need to be set using the appropriate user account."))

        admin_login = conf.get(backend, 'admin_login')

        admin_acl = None

        acls = self.list_acls(folder)
        if acls.has_key(admin_login):
            admin_acl = acls[admin_login]

        if admin_acl == None:
            self.set_acl(folder, admin_login, 'lrsipwa')
        elif not 'w' in admin_acl:
            self.set_acl(folder, admin_login, '%sw' % (admin_acl))

        self.imap._setannotation(folder, metadata_path, metadata_value, shared)

        if admin_acl == None:
            self.set_acl(folder, admin_login, '')
        elif not 'w' in admin_acl:
            self.set_acl(folder, admin_login, admin_acl)

    def shared_folder_create(self, folder_path, server=None):
        """
            Create a shared folder.
        """

        folder_name = "shared%s%s" % (self.imap.separator, folder_path)

        # Correct folder_path being supplied with "shared/shared/" for example
        if folder_name.startswith("shared%s" % (self.imap.separator) * 2):
            folder_name = folder_name[7:]

        log.info(_("Creating new shared folder %s") %(folder_name))
        self.create_folder(folder_name, server)

    def shared_folder_exists(self, folder_path):
        """
            Check if a shared mailbox exists.
        """
        folder_name = 'shared%s%s' % (self.imap.separator, folder_path)

        # Correct folder_path being supplied with "shared/shared/" for example
        if folder_name.startswith("shared%s" % (self.imap.separator) * 2):
            folder_name = folder_name[7:]

        return self.has_folder(folder_name)

    def shared_folder_set_type(self, folder_path, folder_type):
        folder_name = 'shared%s%s' % (self.imap.separator, folder_path)

        # Correct folder_path being supplied with "shared/shared/" for example
        if folder_name.startswith("shared%s" % (self.imap.separator) * 2):
            folder_name = folder_name[7:]

        self.imap._setannotation(folder_name, '/vendor/kolab/folder-type', folder_type)

    def shared_mailbox_create(self, mailbox_base_name, server=None):
        """
            Create a shared folder.
        """

        folder_name = "shared%s%s" % (self.imap.separator, mailbox_base_name)

        # Correct folder_path being supplied with "shared/shared/" for example
        if folder_name.startswith("shared%s" % (self.imap.separator) * 2):
            folder_name = folder_name[7:]

        log.info(_("Creating new shared folder %s") %(mailbox_base_name))
        self.create_folder(folder_name, server)

    def shared_mailbox_exists(self, mailbox_base_name):
        """
            Check if a shared mailbox exists.
        """
        folder_name = "shared%s%s" % (self.imap.separator, mailbox_base_name)

        # Correct folder_path being supplied with "shared/shared/" for example
        if folder_name.startswith("shared%s" % (self.imap.separator) * 2):
            folder_name = folder_name[7:]

        return self.has_folder(folder_name)

    def user_mailbox_create(self, mailbox_base_name, server=None):
        """
            Create a user mailbox.

            Returns the full path to the new mailbox folder.
        """
        folder_name = "user%s%s" % (self.imap.separator, mailbox_base_name)
        log.info(_("Creating new mailbox for user %s") %(mailbox_base_name))

        self.create_folder(folder_name, server)

        if not self.domain == None:
            if conf.has_option(self.domain, "autocreate_folders"):
                    _additional_folders = conf.get_raw(
                            self.domain,
                            "autocreate_folders"
                        )

                    additional_folders = conf.plugins.exec_hook(
                            "create_user_folders",
                            kw={
                                    'folder': folder_name,
                                    'additional_folders': _additional_folders
                                }
                        )

                    if not additional_folders == None:
                        self.user_mailbox_create_additional_folders(
                                mailbox_base_name,
                                additional_folders
                            )

        return folder_name

    def user_mailbox_create_additional_folders(self, folder, additional_folders):
        log.debug(
                _("Creating additional folders for user %s") % (folder),
                level=8
            )

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
                log.warning(_("Mailbox already exists: %s") % (folder_name))

            if additional_folders[additional_folder].has_key("annotations"):
                for annotation in additional_folders[additional_folder]["annotations"].keys():
                    if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                        self.imap._setannotation(
                                folder_name,
                                "%s" % (annotation),
                                "%s" % (additional_folders[additional_folder]["annotations"][annotation])
                            )

            if additional_folders[additional_folder].has_key("quota"):
                self.imap.sq(
                        folder_name,
                        additional_folders[additional_folder]['quota']
                    )

            if additional_folders[additional_folder].has_key("acls"):
                for acl in additional_folders[additional_folder]["acls"].keys():
                    self.imap.sam(
                            folder_name,
                            "%s" % (acl),
                            "%s" % (additional_folders[additional_folder]["acls"][acl])
                        )

        backend = conf.get('kolab', 'imap_backend')

        if len(folder.split('@')) > 1:
            domain = folder.split('@')[1]
            domain_suffix = "@%s" % (domain)
        else:
            domain = None
            domain_suffix = ""

        if not domain == None:
            if conf.has_section(domain) and conf.has_option(domain, 'imap_backend'):
                backend = conf.get(domain, 'imap_backend')

            if conf.has_section(domain) and conf.has_option(domain, 'imap_uri'):
                uri = conf.get(domain, 'imap_uri')
            else:
                uri = None

        log.debug(_("Subscribing user to the additional folders"), level=8)
        # Get the credentials
        admin_login = conf.get(backend, 'admin_login')
        admin_password = conf.get(backend, 'admin_password')

        self.connect(login=False)
        self.login_plain(admin_login, admin_password, folder)

        _tests = []

        # Subscribe only to personal folders
        (personal, other, shared) = self.namespaces()

        if not other == None:
            _tests.append(other)

        if not shared == None:
            for _shared in shared:
                _tests.append(_shared)

        for _folder in self.lm():
            _subscribe = True

            for _test in _tests:
                if not _subscribe:
                    continue

                if _folder.startswith(_test):
                    _subscribe = False

            if _subscribe:
                self.subscribe(_folder)

        self.logout()

    def user_mailbox_delete(self, mailbox_base_name):
        """
            Delete a user mailbox.
        """
        folder = "user%s%s" %(self.imap.separator,mailbox_base_name)
        self.delete_mailfolder(folder)
        self.cleanup_acls(mailbox_base_name)

    def user_mailbox_exists(self, mailbox_base_name):
        """
            Check if a user mailbox exists.
        """
        return self.has_folder('user%s%s' %(self.imap.separator, mailbox_base_name))

    def user_mailbox_quota(self, mailbox_quota):
        pass

    def user_mailbox_rename(self, old_name, new_name):
        old_name = "user%s%s" % (self.imap.separator,old_name)
        new_name = "user%s%s" % (self.imap.separator,new_name)

        if old_name == new_name:
            return

        if not self.has_folder(new_name):
            log.info(_("Renaming INBOX from %s to %s") % (old_name,new_name))
            try:
                self.imap.rename(old_name,new_name)
            except:
                log.error(_("Could not rename INBOX folder %s to %s") % (old_name,new_name))
        else:
            log.warning(_("Moving INBOX folder %s won't succeed as target folder %s already exists") % (old_name,new_name))

    def user_mailbox_server(self, mailbox):
        return self.imap.find_mailfolder_server(mailbox)

    def has_folder(self, folder):
        """
            Check if the environment has a folder named folder.
        """
        folders = self.imap.lm(folder)
        log.debug(_("Looking for folder '%s', we found folders: %r") % (folder,folders), level=8)
        # Greater then one, this folder may have subfolders.
        if len(folders) > 0:
            return True
        else:
            return False

    def _set_kolab_mailfolder_acls(self, acls):
        if isinstance(acls, basestring):
            acls = [ acls ]

        for acl in acls:
            exec("acl = %s" % (acl))
            folder = acl[0]
            subject = acl[1]
            rights = acl[2]
            if len(acl) == 4:
                epoch = acl[3]
            else:
                epoch = (int)(time.time()) + 3600

            if epoch > (int)(time.time()):
                log.debug(
                        _("Setting ACL rights %s for subject %s on folder " + \
                            "%s") % (rights,subject,folder), level=8)

                self.imap.sam(
                        folder,
                        "%s" % (subject),
                        "%s" % (rights)
                    )

            else:
                log.debug(
                        _("Removing ACL rights %s for subject %s on folder " + \
                            "%s") % (rights,subject,folder), level=8)

                self.imap.sam(
                        folder,
                        "%s" % (subject),
                        ""
                    )

        pass

    """ Blah functions """

    def move_user_folders(self, users=[], domain=None):
        for user in users:
            if type(user) == dict:
                if user.has_key('old_mail'):
                    inbox = "user/%s" % (user['mail'])
                    old_inbox = "user/%s" % (user['old_mail'])

                    if self.has_folder(old_inbox):
                        log.debug(_("Found old INBOX folder %s") % (old_inbox), level=8)

                        if not self.has_folder(inbox):
                            log.info(_("Renaming INBOX from %s to %s") % (old_inbox,inbox))
                            self.imap.rename(old_inbox,inbox)
                            self.inbox_folders.append(inbox)
                        else:
                            log.warning(_("Moving INBOX folder %s won't succeed as target folder %s already exists") % (old_inbox,inbox))
                    else:
                        log.debug(_("Did not find old folder user/%s to rename") % (user['old_mail']), level=8)
            else:
                log.debug(_("Value for user is not a dictionary"), level=8)

    def set_quota(self, folder, quota):
        self.imap._setquota(folder, quota)

    def set_user_folder_quota(self, users=[], primary_domain=None, secondary_domain=[], folders=[]):
        """

            Sets the quota in IMAP using the authentication and authorization
            database 'quota' attribute for the users listed in parameter 'users'
        """
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
                quota = auth.get_user_attribute(user, _quota_attr)
                folder = "user/%s" % (user)

            folder = folder.lower()

            try:
                (used,current_quota) = self.imap.lq(folder)
            except:
                # TODO: Go in fact correct the quota.
                log.warning(_("Cannot get current IMAP quota for folder %s") % (folder))
                used = 0
                current_quota = 0

            new_quota = conf.plugins.exec_hook("set_user_folder_quota", kw={
                        'used': used,
                        'current_quota': current_quota,
                        'new_quota': (int)(quota),
                        'default_quota': (int)(default_quota),
                        'user': user
                    }
                )

            log.debug(_("Quota for %s currently is %s") % (folder, current_quota), level=7)

            if new_quota == None:
                continue

            if not int(new_quota) == int(quota):
                log.info(_("Adjusting authentication database quota for folder %s to %d") % (folder,int(new_quota)))
                quota = int(new_quota)
                auth.set_user_attribute(primary_domain, user, _quota_attr, new_quota)

            if not int(current_quota) == int(quota):
                log.info(_("Correcting quota for %s to %s (currently %s)") % (folder, quota, current_quota))
                self.imap._setquota(folder, quota)

    def set_user_mailhost(self, users=[], primary_domain=None, secondary_domain=[], folders=[]):
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
                folder = "user/%s" % (user)

            folder = folder.lower()

            _current_mailserver = self.imap.find_mailfolder_server(folder)

            if not _mailserver == None:
                # TODO:
                if not _current_mailserver == _mailserver:
                    self.imap._xfer(folder, _current_mailserver, _mailserver)
            else:
                auth.set_user_attribute(primary_domain, user, _mailserver_attr, _current_mailserver)

    def parse_mailfolder(self, mailfolder):
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
        if inbox_folders == None:
            inbox_folders = []

        folders = self.list_user_folders()

        for folder in folders:
            log.debug(_("Checking folder: %s") % (folder), level=1)
            try:
                if inbox_folders.index(folder) > -1:
                    continue
                else:
                    log.info(_("Folder has no corresponding user (1): %s") % (folder))
                    self.delete_mailfolder("user/%s" % (folder))
            except:
                log.info(_("Folder has no corresponding user (2): %s") % (folder))
                try:
                    self.delete_mailfolder("user/%s" % (folder))
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

        log.info(_("Deleting folder %s") % (mailfolder_path))

        self.imap.dm(mailfolder_path)

    def get_quota(self, mailfolder_path):
        try:
            return self.lq(mailfolder_path)
        except:
            return

    def get_quota_root(self, mailfolder_path):
        return self.lqr(mailfolder_path)

    def list_acls(self, folder):
        """
            List the ACL entries on a folder
        """
        return self.imap.lam(folder)

    def list_user_folders(self, primary_domain=None, secondary_domains=[]):
        """
            List the INBOX folders in the IMAP backend. Returns a list of unique
            base folder names.
        """
        _folders = self.imap.lm("user/%")
        # TODO: Replace the .* below with a regex representing acceptable DNS
        # domain names.
        domain_re = ".*\.?%s$"

        acceptable_domain_name_res = []

        if not primary_domain == None:
            for domain in [ primary_domain ] + secondary_domains:
                acceptable_domain_name_res.append(domain_re % (domain))

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
                        #print "%s is not acceptable against %s yet using %s" % (folder.split('@')[1],folder,domain_name_re)

                #if acceptable:
                    #folder_name = "%s@%s" % (folder.split(self.separator)[1].split('@')[0],folder.split('@')[1])

                folder_name = "%s@%s" % (folder.split(self.imap.separator)[1].split('@')[0],folder.split('@')[1])
            else:
                folder_name = "%s" % (folder.split(self.imap.separator)[1])

            if not folder_name == None:
                if not folder_name in folders:
                    folders.append(folder_name)

        return folders

    def lm(self, *args, **kw):
        return self.imap.lm(*args, **kw)

    def lq(self, *args, **kw):
        return self.imap.lq(*args, **kw)

    def lqr(self, *args, **kw):
        return self.imap.lqr(*args, **kw)

    def undelete_mailfolder(self, *args, **kw):
        self.imap.undelete_mailfolder(*args, **kw)
