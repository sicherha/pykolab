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

import re

import pykolab.auth

from pykolab.conf import Conf
from pykolab.translate import _

class IMAP(object):
    def __init__(self, conf=None):
        if not conf:
            self.conf = Conf()
            self.conf.finalize_conf()
            self.log = self.conf.log
        else:
            self.conf = conf
            self.log = conf.log

        self.auth = pykolab.auth.Auth(self.conf)

        self.imap = None

    def _connect(self):
        if not self.imap:
            if self.conf.get('kolab', 'imap_backend') == 'cyrus-imap':
                import cyruslib
                try:
                    self.imap = cyruslib.CYRUS(self.conf.get('cyrus-imap', 'uri'))
                # TODO: Actually handle the error
                except cyruslib.CYRUSError, e:
                    (code, error, message) = e
                    raise cyruslib.CYRUSError, e

                if self.conf.debuglevel > 8:
                    self.imap.VERBOSE = 1
                self.imap.login('cyrus-admin', 'VerySecret')
                self.seperator = self.imap.m.getsep()
            else:
                import dovecotlib
                self.imap = dovecotlib.IMAP4()

    def _disconnect(self):
        del self.imap
        self.imap = None

    def create_user_folders(self, users, primary_domain, secondary_domains):
        inbox_folders = []

        folders = self.list_user_folders(primary_domain, secondary_domains)

        # See if the folder belongs to any of the users
        _match_attr = self.conf.get('cyrus-sasl', 'result_attribute')

        #print domain

        if not users:
            users = self.auth.users(primary_domain)

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
                    self.log.info(_("Creating new INBOX for user: %s") %(folder))
                    self.imap.cm("user/%s" %(folder))
                    self.imap.sq("user/%s" %(folder), 0)
                    additional_folders = self.conf.plugins.exec_hook("create_user_folders", args=(folder))
            except:
                self.log.info(_("Creating new INBOX for user: %s") %(folder))
                self.imap.cm("user/%s" %(folder))
                self.imap.sq("user/%s" %(folder), 0)
                additional_folders = self.conf.plugins.exec_hook("create_user_folders", args=(folder))

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
                    self.imap.setannotation(
                            folder_name,
                            "%s" %(annotation),
                            "%s" %(additional_folders[additional_folder]["annotations"][annotation])
                        )

    def set_user_folder_quota(self, users=[], primary_domain=None, secondary_domain=[], folders=[]):
        self._connect()

        _quota_attr = self.conf.get('cyrus-imap', 'quota_attribute')
        _inbox_folder_attr = self.conf.get('cyrus-sasl', 'result_attribute')

        default_quota = self.auth.domain_default_quota(primary_domain)

        #print "Default quota", default_quota

        if default_quota == "":
            default_quota = 0

        if len(users) == 0:
            users = self.auth.list_users(domain)

        for user in users:
            quota = None

            if type(user) == dict:
                if user.has_key(_quota_attr):
                    if type(user[_quota_attr]) == list:
                        quota = user[_quota_attr].pop(0)
                    elif type(user[_quota_attr]) == str:
                        quota = user[_quota_attr]
                else:
                    quota = 0

                if not user.has_key(_inbox_folder_attr):
                    continue
                else:
                    if type(user[_inbox_folder_attr]) == list:
                        folder = "user/%s" % user[_inbox_folder_attr].pop(0)
                    elif type(user[_inbox_folder_attr]) == str:
                        folder = "user/%s" % user[_inbox_folder_attr]
            elif type(user) == str:
                quota = self.auth.get_user_attribute(user, 'quota')
                #print type(quota), quota
                folder = "user/%s" %(user)

            (used,current_quota) = self.imap.lq(folder)

            new_quota = self.conf.plugins.exec_hook("set_user_folder_quota", args=(used, current_quota, int(quota), default_quota))

            #print type(new_quota), new_quota

            if new_quota == None:
                continue

            if not int(new_quota) == int(quota):
                self.log.debug(_("Setting new authz quota for folder %s to %r") %(folder, int(new_quota)), level=6)
                quota = int(new_quota)
                print user
                self.auth.set_user_attribute(primary_domain, user, _quota_attr, new_quota)

            self.log.debug(_("Quota for %s currently is %s") %(folder, current_quota), level=7)

            if not int(current_quota) == int(quota):
                self.log.debug(_("Correcting quota for %s to %s (currently %s)") %(folder, quota, current_quota), level=7)
                self.imap.sq(folder, quota)

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
            self.log.debug(_("Checking folder: %s") %(folder), level=1)
            try:
                if inbox_folders.index(folder) > -1:
                    continue
                else:
                    self.log.info(_("Folder has no corresponding user (1): %s") %(folder))
                    self.imap.dm("user/%s" %(folder))
            except:
                self.log.info(_("Folder has no corresponding user (2): %s") %(folder))
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

        folders = self.create_user_folders(users, primary_domain, secondary_domains)

        self.set_user_folder_quota(users, primary_domain, secondary_domains, folders)

        return folders
