# -*- coding: utf-8 -*-
# Copyright 2015 Instituto Tecnológico de Informática (http://www.iti.es)
#
# Sergio Talens-Oliag (ITI) <sto at iti.es>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# -----
# Note:
#
# This file is based on the original cyrus.py driver from Kolab,
# replacing annotation related functions with metadata functions; to use it
# on a debian installation it can be copied to the path:
#
#   /usr/share/pyshared/pykolab/imap/dovecot.py
#
# The file needs some review, as some functions have been modified to behave
# as we want, but the real changes should be done on other places.
#
# As an example, with annotations you can get all existing annotations with
# one call, but if we use metadatata we have to ask for specific variables,
# there is no function to get all of them at once (at least on the RFC); in
# our case when a pattern like '*' is received we look for fields of the form
# 'vendor/kolab/folder-type', as we know they are the fields the functions we
# are using need.
# -----

import cyruslib
import imaplib
import sys
import time

from urlparse import urlparse

import pykolab

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.imap')
conf = pykolab.getConf()

# BEG: Add GETMETADATA and SETMETADATA support to the cyruslib IMAP objects

Commands = {
    'GETMETADATA':   ('AUTH',),
    'SETMETADATA':   ('AUTH',),
}

imaplib.Commands.update(Commands)

def imap_getmetadata(self, mailbox, pattern='*', shared=None):
    # If pattern is '*' clean pattern and search all entries under /shared
    # and/or /private (depens on the shared parameter value) to emulate the
    # ANNOTATEMORE behaviour
    if pattern == '*':
        pattern = ''
        options = '(DEPTH infinity)'
    else:
        options = '(DEPTH 0)'
    if shared == None:
        entries = '( /shared%s /private%s )' % (pattern, pattern)
    elif shared:
        entries = "/shared%s" % pattern
    else:
        entries = " /private%s" % pattern

    typ, dat = self._simple_command('GETMETADATA', options, mailbox, entries)

    return self._untagged_response(typ, dat, 'METADATA')

def imap_setmetadata(self, mailbox, desc, value, shared=False):
    if value:
        value = value.join(['"', '"'])
    else:
        value = "NIL"

    if shared:
        typ, dat = self._simple_command('SETMETADATA', mailbox, 
                                        "(/shared%s %s)" % (desc,value))
    else:
        typ, dat = self._simple_command('SETMETADATA', mailbox,
                                        "(/private%s %s)" % (desc,value))

    return self._untagged_response(typ, dat, 'METADATA')

# Bind the new methods to the cyruslib IMAP4 and IMAP4_SSL objects
from types import MethodType
cyruslib.IMAP4.getmetadata = MethodType(imap_getmetadata, None, cyruslib.IMAP4)
cyruslib.IMAP4.setmetadata = MethodType(imap_setmetadata, None, cyruslib.IMAP4)
cyruslib.IMAP4_SSL.getmetadata = MethodType(imap_getmetadata, None, cyruslib.IMAP4_SSL)
cyruslib.IMAP4_SSL.setmetadata = MethodType(imap_setmetadata, None, cyruslib.IMAP4_SSL)

# END: Add GETMETADATA and SETMETADATA support to the cyruslib IMAP objects

# Auxiliary functions
def _get_line_entries(lines):
    """Function to get metadata entries """
    entries   = {}
    name  = None
    value = ""
    vlen = 0
    for line in lines:
        line_len = len(line)
        i = 0
        while i < line_len:
            if name == None:
                if line[i] == '/':
                    j = i
                    while j < line_len:
                        if line[j] == ' ':
                            break
                        j += 1
                    name = line[i:j]
                    i = j
            elif vlen != 0:
                j = i + vlen
                if j > line_len:
                    value += line[i:line_len]
                    vlen -= line_len - i
                else:
                    value += line[i:i+vlen]
                    if value in ('', 'NIL'):
                        entries[name] = ""
                    else:
                        entries[name] = value
                    name  = None
                    value = ""
                    vlen  = 0
            elif line[i] == '{':
                j = i
                while j < line_len:
                    if line[j] == '}':
                        vlen = int(line[i+1:j])
                        break
                    j += 1
                i = j
            elif line[i] != ' ':
                j = i
                if line[i] == '"':
                    while j < line_len:
                        # Skip quoted text
                        if line[j] == '\\':
                            j += 2
                            continue
                        elif line[j] == '"':
                            break
                        j += 1
                else:
                    while j < line_len:
                        if line[j] == ' ' or line[j] == ')':
                            break
                        j += 1
                value = line[i:j]
                if value in ('', 'NIL'):
                    entries[name] = ""
                else:
                    entries[name] = value
                name = None
                value = ""
                i = j
            i += 1
    return entries

class Dovecot(cyruslib.CYRUS):
    """
        Abstraction class for some common actions to do exclusively in
        Dovecot.

        Initially based on the Cyrus driver, will remove dependencies on
        cyruslib later; right now this module has only been tested to use the
        dovecot metadata support (no quota or folder operations tests have
        been performed).

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

        self.uri = "%s://%s:%s" % (scheme,hostname,port)

        while 1:
            try:
                cyruslib.CYRUS.__init__(self, self.uri)
                break
            except cyruslib.CYRUSError:
                log.warning(_("Could not connect to Dovecot IMAP server %r") % (self.uri))
                time.sleep(10)

        if conf.debuglevel > 8:
            self.VERBOSE = True
            self.m.debug = 5

        # Initialize our variables
        self.separator = self.SEP

        # Placeholder for known mailboxes on known servers
        self.mbox = {}

        # By default don't assume that we have metadata support
        self.metadata = False

    def __del__(self):
        pass

    def __verbose(self, msg):
        if self.VERBOSE:
            print >> self.LOGFD, msg

    def connect(self, uri):
        """
            Dummy connect function that checks if the server that we want to
            connect to is actually the server we are connected to.

            Uses pykolab.imap.IMAP.connect() in the background.
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

        if hostname == self.server:
            return

        imap = IMAP()
        imap.connect(uri=uri)

        if not self.SEP == self.separator:
            self.separator = self.SEP

    def login(self, *args, **kw):
        """
            Login to the Dovecot IMAP server through cyruslib.CYRUS, but set our
            hierarchy separator.
        """
        cyruslib.CYRUS.login(self, *args, **kw)
        self.separator = self.SEP

        log.debug(_("Continuing with separator: %r") % (self.separator), level=8)

        # Check if we have metadata support or not
        self.metadata = False
        typ, dat = self.m.capability()
        for capability in tuple(dat[-1].upper().split()):
            if capability.startswith("METADATA"):
                log.debug(_("Detected METADATA support"), level=8)
                self.metadata = True
        if not self.metadata:
            log.debug(_("This system does not support METADATA: '%s'" % ','.join(self.m.capabilities)), level=8)

    def find_mailfolder_server(self, mailfolder):
        # Nothing to do in dovecot, returns the current server
        return self.server

    def folder_utf7(self, folder):
        from pykolab import imap_utf7
        return imap_utf7.encode(folder)

    def folder_utf8(self, folder):
        from pykolab import imap_utf7
        return imap_utf7.decode(folder)

    def _setquota(self, mailfolder, quota):
        # Removed server reconnection for dovecot, we only have one server
        log.debug(_("Setting quota for folder %s to %s") % (mailfolder,quota), level=8)
        try:
            self.m.setquota(mailfolder, quota)
        except:
            log.error(_("Could not set quota for mailfolder %s") % (mailfolder))

    def _rename(self, from_mailfolder, to_mailfolder, partition=None):
        # Removed server reconnection for dovecot, we only have one server
        if not partition == None:
            log.debug(_("Moving INBOX folder %s to %s on partition %s") % (from_mailfolder,to_mailfolder, partition), level=8)
        else:
            log.debug(_("Moving INBOX folder %s to %s") % (from_mailfolder,to_mailfolder), level=8)

        self.m.rename(self.folder_utf7(from_mailfolder), self.folder_utf7(to_mailfolder), '"%s"' % (partition))

# BEG: METADATA support functions ... quite similar to annotations, really

    def _getmetadata(self, mailbox, pattern='*', shared=None):
        """Get Metadata"""
        # This test needs to be reviewed
        #if not self.metadata:
        #    return {}

        # Annotations vs. Metadata fix ... we set a pattern that we know is
        # good enough for our purposes for now, but the fact is that the
        # calling programs should be fixed instead. 

        res, data = self.m.getmetadata(self.decode(mailbox), pattern, shared)

        if (len(data) == 1) and data[0] is None:
            self.__verbose( '[GETMETADATA %s] No results' % (mailbox) )
            return {}

        # Get the first response line (it can be a string or a tuple)
        if isinstance(data[0], tuple):
            fline = data[0][0]
        else:
            fline = data[0]

        # Find the folder name 
        fbeg = 0
        fend = -1
        if fline[0] == '"':
            # Quoted name
            fbeg = 1
            i    = 1
            while i < len(fline):
                if fline[i] == '"':
                    # folder name ended unless the previous char is \ (we
                    # should test more, this test would fail if we had a \
                    # at the end of the folder name, but we leave it at that
                    # right now
                    if fline[i-1] != '\\':
                        fend = i
                        break
                i += 1
        else:
            # For unquoted names the first word is the folder name
            fend = fline.find(' ')

        # No mailbox found
        if fend < 0:
            self.__verbose( '[GETMETADATA %s] Mailbox not found in results' % (mailbox) )
            return {}

        # Folder name
        folder = fline[fbeg:fend]

        # Check mailbox name against the folder name
        if folder != mailbox:
            quoted_mailbox = "\"%s\"" % (mailbox)
            if folder != quoted_mailbox:
                self.__verbose(
                   '[GETMETADATA %s] Mailbox \'%s\' is not the same as \'%s\'' \
                   % (mailbox, quoted_mailbox, folder)
                )
                return {}

        # Process the rest of the first line, the first value will be
        # available after the first '(' found
        i=fend
        ebeg = -1
        while i < len(fline):
            if fline[i] == '(':
                ebeg = i+1
                break
            i += 1

        if ebeg < 0:
            self.__verbose(
                '[GETMETADATA %s] Mailbox has no values, skipping' % (mailbox)
            )
            return {}

        # This variable will start with an entry name and will continue with
        # the value lenght or the value
        nfline = fline[ebeg:]
        if isinstance(data[0], tuple):
            entries = _get_line_entries((nfline,) + data[0][1:])
        else:
            entries = _get_line_entries((nfline,))

        for line in data[1:]:
            if isinstance(line, tuple):
                lentries = _get_line_entries(line)
            else:
                lentries = _get_line_entries([line,])

            if lentries != None and lentries != {}:
                entries.update(lentries)

        mdat = { mailbox: entries };
        return mdat

    def _setmetadata(self, mailbox, desc, value, shared=False):
        """Set METADADATA"""
        res, msg = self.m.setmetadata(self.decode(mailbox), desc, value, shared)
        self.__verbose( '[SETMETADATA %s] %s: %s' % (mailbox, res, msg[0]) )

    # Use metadata instead of annotations
    def _getannotation(self, *args, **kw):
        return self._getmetadata(*args, **kw)

    def getannotation(self, *args, **kw):
        return self._getmetadata(*args, **kw)

    # Use metadata instead of annotations
    def _setannotation(self, *args, **kw):
        return self._setmetadata(*args, **kw)

    def setannotation(self, *args, **kw):
        return self._setmetadata(*args, **kw)

# END: METADATA / Annotations

    # The functions that follow are the same ones used with Cyrus, probably a
    # review is needed

    def _xfer(self, mailfolder, current_server, new_server):
        self.connect(self.uri.replace(self.server,current_server))
        log.debug(_("Transferring folder %s from %s to %s") % (mailfolder, current_server, new_server), level=8)
        self.xfer(mailfolder, new_server)

    def undelete_mailfolder(self, mailfolder, to_mailfolder=None, recursive=True):
        """
            Login to the actual backend server, then "undelete" the mailfolder.

            'mailfolder' may be a string representing either of the following two
            options;

            - the fully qualified pathof the deleted folder in its current
              location, such as, for a deleted INBOX folder originally known as
              "user/userid[@domain]";

                "DELETED/user/userid/hex[@domain]"

            - the original folder name, such as;

                "user/userid[@domain]"

            'to_mailfolder' may be the target folder to "undelete" the deleted
            folder to. If not specified, the original folder name is used.
        """
        # Placeholder for folders we have recovered already.
        target_folders = []

        mailfolder = self.parse_mailfolder(mailfolder)

        undelete_folders = self._find_deleted_folder(mailfolder)

        if not to_mailfolder == None:
            target_mbox = self.parse_mailfolder(to_mailfolder)
        else:
            target_mbox = mailfolder

        for undelete_folder in undelete_folders:
            undelete_mbox = self.parse_mailfolder(undelete_folder)

            prefix = undelete_mbox['path_parts'].pop(0)
            mbox = undelete_mbox['path_parts'].pop(0)

            if to_mailfolder == None:
                target_folder = self.separator.join([prefix,mbox])
            else:
                target_folder = self.separator.join(target_mbox['path_parts'])

            if not to_mailfolder == None:
                target_folder = "%s%s%s" % (target_folder,self.separator,mbox)

            if not len(undelete_mbox['path_parts']) == 0:
                target_folder = "%s%s%s" % (target_folder,self.separator,self.separator.join(undelete_mbox['path_parts']))

            if target_folder in target_folders:
                target_folder = "%s%s%s" % (target_folder,self.separator,undelete_mbox['hex_timestamp'])

            target_folders.append(target_folder)

            if not target_mbox['domain'] == None:
                target_folder = "%s@%s" % (target_folder,target_mbox['domain'])

            log.info(_("Undeleting %s to %s") % (undelete_folder,target_folder))

            target_server = self.find_mailfolder_server(target_folder)

            if hasattr(conf,'dry_run') and not conf.dry_run:
                if not target_server == self.server:
                    self.xfer(undelete_folder,target_server)

                self.rename(undelete_folder,target_folder)
            else:
                if not target_server == self.server:
                    print >> sys.stdout, _("Would have transfered %s from %s to %s") % (undelete_folder, self.server, target_server)

                print >> sys.stdout, _("Would have renamed %s to %s") % (undelete_folder, target_folder)

    def parse_mailfolder(self, mailfolder):
        """
            Parse a mailfolder name to it's parts.

            Takes a fully qualified mailfolder or mailfolder sub-folder.
        """
        mbox = {
                'domain': None
            }

        if len(mailfolder.split('/')) > 1:
            self.separator = '/'

        # Split off the virtual domain identifier, if any
        if len(mailfolder.split('@')) > 1:
            mbox['domain'] = mailfolder.split('@')[1]
            mbox['path_parts'] = mailfolder.split('@')[0].split(self.separator)
        else:
            mbox['path_parts'] = mailfolder.split(self.separator)

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
            verify_folder_search = "%(dp)s%(sep)s%(mailfolder)s" % {
                    'dp': deleted_prefix,
                    'sep': self.separator,
                    'mailfolder': self.separator.join(mbox['path_parts'])
                }

            if not mbox['domain'] == None:
                verify_folder_search = "%s@%s" % (verify_folder_search, mbox['domain'])

            if ' ' in verify_folder_search:
                folders = self.lm('"%s"' % self.folder_utf7(verify_folder_search))
            else:
                folders = self.lm(self.folder_utf7(verify_folder_search))

            # NOTE: Case also covered is valid hexadecimal folders; won't be the
            # actual check as intended, but doesn't give you anyone else's data
            # unless... See the following:
            #
            # TODO: Case not covered is usernames that are hexadecimal.
            #
            # We could probably attempt to convert the int(hex) into a time.gmtime(),
            # but it still would not cover all cases.
            #

            # If no folders were found... well... then there you go.
            if len(folders) < 1:
                return None

            # Pop off the hex timestamp, which turned out to be valid
            mbox['hex_timestamp'] = mbox['path_parts'].pop()

        return mbox

    def _find_deleted_folder(self, mbox):
        """
            Give me the parts that are in an original mailfolder name and I'll find
            the deleted folder name.

            TODO: It finds virtdomain folders for non-virtdomain searches.
        """
        deleted_folder_search = "%(deleted_prefix)s%(separator)s%(mailfolder)s%(separator)s*" % {
                    # TODO: The prefix used is configurable
                    'deleted_prefix': "DELETED",
                    'mailfolder': self.separator.join(mbox['path_parts']),
                    'separator': self.separator,
                }

        if not mbox['domain'] == None:
            deleted_folder_search = "%s@%s" % (deleted_folder_search,mbox['domain'])

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
