# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
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
                self.imap = cyruslib.CYRUS(self.conf.get('cyrus-imap', 'uri'))
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

    def create_user_folders(self):
        inbox_folders = []

        folders = self.list_user_folders()

        # See if the folder belongs to any of the users
        _match_attr = self.conf.get('cyrus-sasl', 'result_attribute')

        for user in self.auth.users():
            if user.has_key(_match_attr):
                inbox_folders.append(user[_match_attr])

        for folder in inbox_folders:
            additional_folders = None
            try:
                if folders.index(folder) > -1:
                    continue
                else:
                    self.log.info(_("Creating new INBOX for user: %s") %(folder))
                    self.imap.cm("user/%s" %(folder))
                    self.imap.sq("user/%s" %(folder), 0)
#                    additional_folders = self.conf.plugins.exec_hook("create_user_folders", args=(folder))
            except:
                self.log.info(_("Creating new INBOX for user: %s") %(folder))
                self.imap.cm("user/%s" %(folder))
                self.imap.sq("user/%s" %(folder), 0)
#                additional_folders = self.conf.plugins.exec_hook("create_user_folders", args=(folder))

            if not additional_folders == None:
                self.create_user_additional_folders(folder, additional_folders)

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

    def set_user_folder_quota(self):
        self._connect()

        _quota_attr = self.conf.get('cyrus-imap', 'quota_attribute')
        _inbox_folder_attr = self.conf.get('cyrus-sasl', 'result_attribute')

        for user in self.auth.users():
            quota = None

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

            (used,current_quota) = self.imap.lq(folder)

            new_quota = self.conf.plugins.exec_hook("set_user_folder_quota", args=(used, current_quota, int(quota)))

            if new_quota and not new_quota == int(quota):
                self.log.debug(_("Setting new quota for folder %s to %r") %(folder, new_quota), level=9)
                quota = new_quota
                self.auth.set_user_attribute(user['dn'], _quota_attr, new_quota)

            self.log.debug(_("Quota for %s currently is %s") %(folder, current_quota), level=7)

            if not int(current_quota) == int(quota):
                self.log.debug(_("Correcting quota for %s to %s (currently %s)") %(folder, quota, current_quota), level=7)
                self.imap.sq(folder, quota)

    def expunge_user_folders(self):
        self._connect()

        inbox_folders = []

        folders = self.list_user_folders()

        # See if the folder belongs to any of the users
        _match_attr = self.conf.get('cyrus-sasl', 'result_attribute')

        for user in self.auth.users():
            if user.has_key(_match_attr):
                if not user[_match_attr] in inbox_folders:
                    inbox_folders.append(user[_match_attr])

        inbox_folders = list(set(inbox_folders))

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

    def list_user_folders(self):
        """
            List the INBOX folders in the IMAP backend. Returns a list of unique
            base folder names.
        """
        self._connect()

        _folders = self.imap.lm("user/*")
        folders = []

        for folder in _folders:
            if len(folder.split('@')) > 1:
                folder_name = "%s@%s" %(folder.split(self.imap.m.getsep())[1].split('@')[0],folder.split('@')[1])
            else:
                folder_name = "%s" %(folder.split(self.imap.m.getsep())[1])

            if not folder_name in folders:
                folders.append(folder_name)

        return folders

    def synchronize(self, users=[]):
        self._connect()
        self.expunge_user_folders()
        self.create_user_folders()
        self.set_user_folder_quota()
