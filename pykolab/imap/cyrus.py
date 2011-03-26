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

import cyruslib
import time

import pykolab

from pykolab.imap import IMAP

from pykolab.translate import _

log = pykolab.getLogger('pykolab.imap.cyrus')
conf = pykolab.getConf()

class Cyrus(object):
    """
        Abstraction class for some common actions to do exclusively in Cyrus.

        For example, the following functions require the commands to be
        executed against the backend server if a murder is being used.

        - Setting quota
        - Renaming the top-level mailbox
        - Setting annotations
    """
    def __init__(self, imap=None):
        self.imap = imap

        if self.imap == None:
            self.imap = IMAP()

    def setquota(self, mailbox, quota):
        """
            Login to the actual backend server.
        """
        log.debug(_("Checking actual backend server for folder %s through annotations") %(mailbox), level=8)
        annotations = self.imap.getannotation(mailbox, "/vendor/cmu/cyrus-imapd/server")
        server = annotations[mailbox]['/vendor/cmu/cyrus-imapd/server']
        log.debug(_("Server for INBOX folder %s is %s") %(mailbox,server), level=8)

        _imap = cyruslib.IMAP4(server, 143)
        admin_login = conf.get('cyrus-imap', 'admin_login')
        admin_password = conf.get('cyrus-imap', 'admin_password')
        _imap.login(admin_login, admin_password)

        log.debug(_("Setting quota for INBOX folder %s to %s") %(mailbox,quota), level=8)
        _imap.setquota(mailbox, quota)

        del _imap

    def rename(self, from_mailbox, to_mailbox, partition=None):
        """
            Login to the actual backend server, then rename.
        """
        log.debug(_("Checking actual backend server for folder %s through annotations") %(from_mailbox), level=8)
        annotations = self.imap.getannotation(from_mailbox, "/vendor/cmu/cyrus-imapd/server")
        server = annotations[from_mailbox]['/vendor/cmu/cyrus-imapd/server']
        log.debug(_("Server for INBOX folder %s is %s") %(from_mailbox,server), level=8)

        _imap = cyruslib.IMAP4(server, 143)
        admin_login = conf.get('cyrus-imap', 'admin_login')
        admin_password = conf.get('cyrus-imap', 'admin_password')
        _imap.login(admin_login, admin_password)

        log.debug(_("Moving INBOX folder %s to %s") %(from_mailbox,from_mailbox), level=8)
        _imap.rename(from_mailbox, from_mailbox, partition)

        del _imap

    def setannotation(self, mailbox, annotation, value):
        """
            Login to the actual backend server, then set annotation.
        """
        log.debug(_("Checking actual backend server for folder %s through annotations") %(mailbox), level=8)
        annotations = self.imap.getannotation(mailbox, "/vendor/cmu/cyrus-imapd/server")
        server = annotations[mailbox]['/vendor/cmu/cyrus-imapd/server']
        log.debug(_("Server for INBOX folder %s is %s") %(mailbox,server), level=8)

        _imap = cyruslib.IMAP4(server, 143)
        admin_login = conf.get('cyrus-imap', 'admin_login')
        admin_password = conf.get('cyrus-imap', 'admin_password')
        _imap.login(admin_login, admin_password)

        log.debug(_("Setting annotation %s on folder %s") %(annotation,mailbox), level=8)
        _imap.setannotation(mailbox, annotation, value)

        del _imap

    def undelete(self, mailbox, to_mailbox=None, recursive=True):
        """
            Login to the actual backend server, then "undelete" the mailbox.

            'mailbox' may be a string representing either of the following two
            options;

            - the fully qualified pathof the deleted folder in its current
              location, such as, for a deleted INBOX folder originally known as
              "user/userid[@domain]";

                "DELETED/user/userid/hex[@domain]"

            - the original folder name, such as;

                "user/userid[@domain]"

            'to_mailbox' may be the target folder to "undelete" the deleted
            folder to. If not specified, the original folder name is used.
        """

        log.debug(_("Checking actual backend server for folder %s through annotations") %(mailbox), level=8)
        annotations = self.imap.getannotation(mailbox, "/vendor/cmu/cyrus-imapd/server")
        server = annotations[mailbox]['/vendor/cmu/cyrus-imapd/server']
        log.debug(_("Server for deleted folder %s is %s") %(mailbox,server), level=8)

        _imap = cyruslib.IMAP4(server, 143)
        admin_login = conf.get('cyrus-imap', 'admin_login')
        admin_password = conf.get('cyrus-imap', 'admin_password')
        _imap.login(admin_login, admin_password)

        # Get the seperator used
        self.seperator = _imap.getsep()

        # Placeholder for folders we have recovered already.
        target_folders = []

        mailbox = self.parse_mailbox(mailbox)

        undelete_folders = self._find_deleted_folder(mailbox)

        if not to_mailbox == None:
            target_mbox = self.parse_mailbox(to_mailbox)
        else:
            target_mbox = mailbox

        for undelete_folder in undelete_folders:
            undelete_mbox = self.parse_mailbox(undelete_folder)

            prefix = undelete_mbox['path_parts'].pop(0)
            mbox = undelete_mbox['path_parts'].pop(0)

            if to_mailbox == None:
                target_folder = self.seperator.join([prefix,mbox])
            else:
                target_folder = self.seperator.join(target_mbox['path_parts'])

            if not to_mailbox == None:
                target_folder = "%s%s%s" %(target_folder,self.seperator,mbox)
            if not len(undelete_mbox['path_parts']) == 0:
                target_folder = "%s%s%s" %(target_folder,self.seperator,self.seperator.join(undelete_mbox['path_parts']))

            if target_folder in target_folders:
                target_folder = "%s%s%s" %(target_folder,self.seperator,undelete_mbox['hex_timestamp'])

            target_folders.append(target_folder)

            if not target_mbox['domain'] == None:
                target_folder = "%s@%s" %(target_folder,target_mbox['domain'])

            log.info(_("Undeleting %s to %s") %(undelete_folder,target_folder))
            _imap.rename(undelete_folder,target_folder)

    def parse_mailbox(self, mailbox):
        """
            Parse a mailbox name to it's parts.

            Takes a fully qualified mailbox or mailbox sub-folder.
        """
        mbox = {
                'domain': None
            }

        # Split off the virtual domain identifier, if any
        if len(mailbox.split('@')) > 1:
            mbox['domain'] = mailbox.split('@')[1]
            mbox['path_parts'] = mailbox.split('@')[0].split(self.seperator)
        else:
            mbox['path_parts'] = mailbox.split(self.seperator)

        # See if the path that has been specified is the current location for
        # the deleted folder, or the original location, we have to find the deleted
        # folder for.
        if not mbox['path_parts'][0] in [ 'user', 'shared' ]:
            deleted_prefix = mbox['path_parts'].pop(0)
            # See if the hexadecimal timestamp is actually hexadecimal.
            # This prevents "DELETED/user/userid/Sent", but not
            # "DELETED/user/userid/FFFFFF" from being specified.
            try:
                epoch = int(mbox['path_parts'][(len(mbox['path_parts'])-1)], 16)
                try:
                    timestamp = time.asctime(time.gmtime(epoch))
                except:
                    return None
            except:
                return None

            # Verify that the input for the deleted folder is actually a
            # deleted folder.
            verify_folder_search = "%(dp)s%(sep)s%(mailbox)s" % {
                    'dp': deleted_prefix,
                    'sep': self.seperator,
                    'mailbox': self.seperator.join(mbox['path_parts'])
                }

            if not mbox['domain'] == None:
                verify_folder_search = "%s@%s" %(verify_folder_search, mbox['domain'])

            folders = self.imap.imap.lm(verify_folder_search)

            # NOTE: Case also covered is valid hexadecimal folders; won't be the
            # actual check as intended, but doesn't give you anyone else's data
            # unless... See the following:
            #
            # TODO: Case not covered is usernames that are hexadecimal.
            #
            # We could probably attempt to convert the int(hex) into a time.gmtime(),
            # but it still would not cover all cases.
            #

            # If no folders where found... well... then there you go.
            if len(folders) < 1:
                return None

            # Pop off the hex timestamp, which turned out to be valid
            mbox['hex_timestamp'] = mbox['path_parts'].pop()

        return mbox

    def _find_deleted_folder(self, mbox):
        """
            Give me the parts that are in an original mailbox name and I'll find
            the deleted folder name.

            TODO: It finds virtdomain folders for non-virtdomain searches.
        """
        deleted_folder_search = "%(deleted_prefix)s%(seperator)s%(mailbox)s%(seperator)s*" % {
                    'deleted_prefix': "DELETED",
                    'mailbox': self.seperator.join(mbox['path_parts']),
                    'seperator': self.seperator,
                }

        if not mbox['domain'] == None:
            deleted_folder_search = "%s@%s" %(deleted_folder_search,mbox['domain'])

        folders = self.imap.lm(deleted_folder_search)

        #print "the deleted folders that i could find are:", folders

        if mbox['domain'] == None:
            #print "removing the folders that are virtdomain folders"
            _folders = []
            for folder in folders:
                if len(folder.split('@')) < 2:
                    _folders.append(folder)

            #print "remaining folders:", _folders
            folders = _folders

        return folders