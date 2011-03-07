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

class KolabDefaultfolders(object):
    """
        Example plugin to create a set of default folders.
    """

    def __init__(self, conf=None):
        self.conf = conf

    def create_user_folders(self, kw={}, args=()):
        """
            The arguments passed to the 'create_user_folders' hook:

            - imap connection
            - user folder
        """

        (folder) = args

        folders_to_create = {}

        folders_to_create["Calendar"] = {
                "annotations": {
                        "/vendor/kolab/folder-test": "true",
                        "/vendor/kolab/folder-type": "event.default"
                    }
            }

        folders_to_create["Calendar/Personlich"] = {
                "annotations": {
                        "/vendor/kolab/folder-test": "true",
                        "/vendor/kolab/folder-type": "event"
                    }
            }

        folders_to_create["Contacts"] = {
                "annotations": {
                        "/vendor/kolab/folder-test": "true",
                        "/vendor/kolab/folder-type": "contact.default"
                    }
            }

        folders_to_create["Dagboek"] = {
                "annotations": {
                        "/vendor/kolab/folder-test": "true",
                        "/vendor/kolab/folder-type": "journal.default"
                    }
            }

        return folders_to_create