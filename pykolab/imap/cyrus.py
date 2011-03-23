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

import pykolab

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
