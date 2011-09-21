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

from urlparse import urlparse

import pykolab

from pykolab.translate import _

conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.imap.cyrus')

imap = pykolab.imap

class Cyrus(cyruslib.CYRUS):
    """
        Abstraction class for some common actions to do exclusively in Cyrus.

        For example, the following functions require the commands to be
        executed against the backend server if a murder is being used.

        - Setting quota
        - Renaming the top-level mailbox
        - Setting annotations

    """

    setquota = cyruslib.CYRUS.sq

    def __init__(self, uri):
        """
            Initialize this class, but do not connect yet.
        """
        port = None

        result = urlparse(uri)

        if hasattr(result, 'hostname'):
            scheme = result.scheme
            hostname = result.hostname
            port = result.port
        else:
            scheme = uri.split(':')[0]
            (hostname, port) = uri.split('/')[2].split(':')

        if not port:
            if scheme == 'imap':
                port = 143
            else:
                port = 993

        self.server = hostname

        self.uri = "%s://%s:%s" %(scheme,hostname,port)

        cyruslib.CYRUS.__init__(self, self.uri)

        if conf.debuglevel > 8:
            self.VERBOSE = True

        # Initialize our variables
        self.seperator = self.SEP

        # Placeholder for known mailboxes on known servers
        self.mbox = {}

    def __del__(self):
        pass

    def login(self, *args, **kw):
        """
            Login to the Cyrus IMAP server through cyruslib.CYRUS, but set our
            hierarchy seperator.
        """
        cyruslib.CYRUS.login(self, *args, **kw)
        self.seperator = self.SEP

        self.murder = False

        for capability in self.m.capabilities:
            if capability.startswith("MUPDATE="):
                log.debug(_("Detected we are running in a Murder topology"), level=8)
                self.murder = True

        if not self.murder:
            log.debug(_("This system is not part of a murder topology"), level=8)

    def find_mailbox_server(self, mailbox):
        annotations = {}

        _mailbox = self.parse_mailbox(mailbox)
        prefix = _mailbox['path_parts'].pop(0)
        mbox = _mailbox['path_parts'].pop(0)
        if not _mailbox['domain'] == None:
            mailbox = "%s%s%s@%s" %(prefix,self.seperator,mbox,_mailbox['domain'])

        # TODO: Workaround for undelete
        if len(self.lm(mailbox)) < 1:
            return self.server

        if not self.murder:
            return self.server

        log.debug(_("Checking actual backend server for folder %s through annotations") %(mailbox), level=8)
        if self.mbox.has_key(mailbox):
            return self.mbox[mailbox]

        max_tries = 20
        num_try = 0
        while 1:
            num_try += 1
            annotations = self._getannotation(mailbox, "/vendor/cmu/cyrus-imapd/server")

            if annotations.has_key(mailbox):
                break

            if max_tries <= num_try:
                log.error(_("Could not get the annotations after %s tries.") %(num_try))
                annotations = { mailbox: { '/vendor/cmu/cyrus-imapd/server': self.server }}
                break

            log.warning(_("No annotations for %s: %r") %(mailbox,annotations))

            time.sleep(1)

        server = annotations[mailbox]['/vendor/cmu/cyrus-imapd/server']
        self.mbox[mailbox] = server

        if not server == self.server:
            if imap._imap.has_key(server):
                if not imap._imap[server].mbox.has_key(mailbox):
                    imap._imap[server].mbox[mailbox] = server

        log.debug(_("Server for INBOX folder %s is %s") %(mailbox,server), level=8)

        return server

    def _setquota(self, mailbox, quota):
        """
            Login to the actual backend server.
        """
        server = self.find_mailbox_server(mailbox)
        imap.connect('imap://%s:143' %(server))

        log.debug(_("Setting quota for INBOX folder %s to %s") %(mailbox,quota), level=8)
        try:
            imap.setquota(mailbox, quota)
        except:
            log.error(_("Could not set quota for mailbox %s") %(mailbox))

    def _rename(self, from_mailbox, to_mailbox, partition=None):
        """
            Login to the actual backend server, then rename.
        """
        server = self.find_mailbox_server(from_mailbox)
        imap.connect('imap://%s:143' %(server))

        log.debug(_("Moving INBOX folder %s to %s") %(from_mailbox,to_mailbox), level=8)
        imap.rename(from_mailbox, to_mailbox, partition)

    def _getannotation(self, *args, **kw):
        imap.connect()
        return imap.getannotation(*args, **kw)

    def _setannotation(self, mailbox, annotation, value):
        """
            Login to the actual backend server, then set annotation.
        """
        server = self.find_mailbox_server(mailbox)
        imap.connect('imap://%s:143' %(server))

        log.debug(_("Setting annotation %s on folder %s") %(annotation,mailbox), level=8)
        imap.setannotation(mailbox, annotation, value)

    def _xfer(self, mailbox, current_server, new_server):
        imap.connect('imap://%s:143' %(current_server))
        log.debug(_("Transferring folder %s from %s to %s") %(mailbox, current_server, new_server), level=8)
        imap.xfer(mailbox, new_server)

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

            target_server = self.find_mailbox_server(target_folder)

            if not target_server == self.server:
                self.xfer(undelete_folder,target_server)

            self.rename(undelete_folder,target_folder)

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

            folders = self.lm(verify_folder_search)

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
                    # TODO: The prefix used is configurable
                    'deleted_prefix': "DELETED",
                    'mailbox': self.seperator.join(mbox['path_parts']),
                    'seperator': self.seperator,
                }

        if not mbox['domain'] == None:
            deleted_folder_search = "%s@%s" %(deleted_folder_search,mbox['domain'])

        folders = self.lm(deleted_folder_search)

        # The folders we have found at this stage include virtdomain folders.
        #
        # For example, having searched for user/userid, it will also find
        # user/userid@example.org
        #

        # Here, we explicitely remove any virtdomain folders.
        if mbox['domain'] == None:
            _folders = []
            for folder in folders:
                if len(folder.split('@')) < 2:
                    _folders.append(folder)

            folders = _folders

        return folders
