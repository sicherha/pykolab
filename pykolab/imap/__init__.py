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

import pykolab
from pykolab.auth import Auth
from pykolab.translate import _

conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.imap')

class IMAP(object):
    def __init__(self):
        self.auth = Auth()

        self.imap = None

    def _connect(self):
        if not self.imap:
            if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                import cyruslib
                try:
                    self.imap = cyruslib.CYRUS(conf.get('cyrus-imap', 'uri'))
                # TODO: Actually handle the error
                except cyruslib.CYRUSError, e:
                    (code, error, message) = e
                    raise cyruslib.CYRUSError, e

                if conf.debuglevel >= 9:
                    self.imap.VERBOSE = 1
                try:
                    admin_login = conf.get('cyrus-imap', 'admin_login')
                    admin_password = conf.get('cyrus-imap', 'admin_password')
                    self.imap.login(admin_login, admin_password)
                    self.seperator = self.imap.m.getsep()
                except cyruslib.CYRUSError, e:
                    (code, error, message) = e
                    if error == 'LOGIN':
                        log.error(_("Invalid login credentials for IMAP Administrator"))
            else:
                import dovecotlib
                self.imap = dovecotlib.IMAP4()

    def _disconnect(self):
        del self.imap
        self.imap = None

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
                            if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                                from pykolab.imap.cyrus import Cyrus
                                _imap = Cyrus(self.imap)
                                _imap.rename(old_inbox,inbox)
                        else:
                            log.warning(_("Moving INBOX folder %s won't succeed as target folder %s already exists") %(old_inbox,inbox))
                    else:
                        log.debug(_("Did not find old folder user/%s to rename") %(user['old_mail']), level=8)
            else:
                log.debug(_("Value for user is not a dictionary"), level=8)

    def create_user_folders(self, users, primary_domain, secondary_domains):
        inbox_folders = []

        domain_section = self.auth.domain_section(primary_domain)

        folders = self.list_user_folders(primary_domain, secondary_domains)

        # See if the folder belongs to any of the users
        _match_attr = conf.get('cyrus-sasl', 'result_attribute')

        #print domain

        if not users:
            users = self.auth.list_users(primary_domain)

        for user in users:
            if type(user) == dict:
                if user.has_key(_match_attr):
                    inbox_folders.append(user[_match_attr])
            elif type(user) == str:
                inbox_folders.append(user)

        for folder in inbox_folders:
            additional_folders = None
            try:
                if folders.index(folder) > -1:
                    continue
                else:
                    # TODO: Perhaps this block is moot
                    log.info(_("Creating new INBOX for user (%d): %s") %(1,folder))
                    self.imap.cm("user/%s" %(folder))
                    if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                        from pykolab.imap.cyrus import Cyrus
                        _imap = Cyrus(self.imap)
                        _imap.setquota("user/%s" %(folder),0)

            except:
                # TODO: Perhaps this block is moot
                log.info(_("Creating new INBOX for user (%d): %s") %(2,folder))
                self.imap.cm("user/%s" %(folder))
                if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                    from pykolab.imap.cyrus import Cyrus
                    _imap = Cyrus(self.imap)
                    _imap.setquota("user/%s" %(folder),0)

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
        for additional_folder in additional_folders.keys():
            _add_folder = {}
            if len(folder.split('@')) > 1:
                folder_name = "user%(seperator)s%(username)s%(seperator)s%(additional_folder_name)s@%(domainname)s"
                _add_folder['username'] = folder.split('@')[0]
                _add_folder['domainname'] = folder.split('@')[1]
                _add_folder['additional_folder_name'] = additional_folder
                _add_folder['seperator'] = self.seperator
                folder_name = folder_name % _add_folder
            else:
                folder_name = "user%(seperator)s%(username)s%(seperator)s%(additional_folder_name)s" % {
                        "username": folder,
                        "seperator": self.seperator,
                        "additional_folder_name": additional_folder
                    }

            self.imap.cm(folder_name)

            if additional_folders[additional_folder].has_key("annotations"):
                for annotation in additional_folders[additional_folder]["annotations"].keys():
                    if conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                        from pykolab.imap.cyrus import Cyrus
                        _imap = Cyrus(self.imap)
                        _imap.setannotation(
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
        self._connect()

        if conf.has_option(primary_domain, 'quota_attribute'):
            _quota_attr = conf.get(primary_domain, 'quota_attribute')
        else:
            auth_mechanism = conf.get('kolab', 'auth_mechanism')
            _quota_attr = conf.get(auth_mechanism, 'quota_attribute')

        _inbox_folder_attr = conf.get('cyrus-sasl', 'result_attribute')

        default_quota = self.auth.domain_default_quota(primary_domain)

        if default_quota == "":
            default_quota = 0

        if len(users) == 0:
            users = self.auth.list_users(primary_domain)

        for user in users:
            quota = None

            if type(user) == dict:
                if user.has_key(_quota_attr):
                    #print "user has key"
                    if type(user[_quota_attr]) == list:
                        quota = user[_quota_attr].pop(0)
                    elif type(user[_quota_attr]) == str:
                        quota = user[_quota_attr]
                else:
                    _quota = self.auth.get_user_attribute(primary_domain, user, _quota_attr)
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
                quota = self.auth.get_user_attribute(user, 'quota')
                folder = "user/%s" %(user)

            try:
                (used,current_quota) = self.imap.lq(folder)
            except:
                # TODO: Go in fact correct the quota.
                log.warning(_("Cannot get current IMAP quota for folder %s") %(folder))
                continue

            new_quota = conf.plugins.exec_hook("set_user_folder_quota", kw={
                        'used': used,
                        'current_quota': current_quota,
                        'new_quota': int(quota),
                        'default_quota': default_quota
                    }
                )

            log.debug(_("Quota for %s currently is %s") %(folder, current_quota), level=7)

            if new_quota == None:
                continue

            if not int(new_quota) == int(quota):
                log.info(_("Adjusting authentication database quota for folder %s to %d") %(folder,int(new_quota)))
                quota = int(new_quota)
                self.auth.set_user_attribute(primary_domain, user, _quota_attr, new_quota)

            if not int(current_quota) == int(quota):
                #log.info(_("Correcting quota for %s to %s (currently %s)") %(folder, quota, current_quota))
                log.debug(_("Checking actual backend server for folder %s through annotations") %(folder), level=8)
                annotations = self.imap.getannotation(folder, "/vendor/cmu/cyrus-imapd/server")
                server = annotations[folder]['/vendor/cmu/cyrus-imapd/server']
                log.debug(_("Server for INBOX folder %s is %s") %(folder,server))
                import cyruslib
                _imap = cyruslib.IMAP4(server, 143)
                admin_login = conf.get('cyrus-imap', 'admin_login')
                admin_password = conf.get('cyrus-imap', 'admin_password')
                _imap.login(admin_login, admin_password)

                log.info(_("Correcting quota for %s to %s (currently %s)") %(folder, quota, current_quota))
                _imap.setquota(folder, quota)

                del _imap

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
        self._connect()

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
                    self.imap.dm("user/%s" %(folder))
            except:
                log.info(_("Folder has no corresponding user (2): %s") %(folder))
                self.imap.dm("user/%s" %(folder))

    def list_user_folders(self, primary_domain=None, secondary_domains=[]):
        """
            List the INBOX folders in the IMAP backend. Returns a list of unique
            base folder names.
        """
        self._connect()

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
                #acceptable = False
                #for domain_name_re in acceptable_domain_name_res:
                    #prog = re.compile(domain_name_re)
                    #if prog.match(folder.split('@')[1]):
                        #print "Acceptable indeed"
                        #acceptable = True
                    #if not acceptable:
                        #print "%s is not acceptable against %s yet using %s" %(folder.split('@')[1],folder,domain_name_re)

                #if acceptable:
                    #folder_name = "%s@%s" %(folder.split(self.seperator)[1].split('@')[0],folder.split('@')[1])

                folder_name = "%s@%s" %(folder.split(self.seperator)[1].split('@')[0],folder.split('@')[1])
            else:
                folder_name = "%s" %(folder.split(self.seperator)[1])

            if not folder_name == None:
                if not folder_name in folders:
                    folders.append(folder_name)

        #print folders

        return folders

    def synchronize(self, users=[], primary_domain=None, secondary_domains=[]):
        self._connect()
        self.users = users

        self.move_user_folders(users)

        folders = self.create_user_folders(users, primary_domain, secondary_domains)

        self.set_user_folder_quota(users, primary_domain, secondary_domains, folders)

        return folders
