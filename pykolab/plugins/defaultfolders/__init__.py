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

import pykolab

from pykolab.translate import _

conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.plugins.defaultfolders')

class KolabDefaultfolders(object):
    """
        Example plugin to create a set of default folders.
    """

    def __init__(self):
        pass

    def add_options(self, *args,  **kw):
        pass

    def create_user_folders(self, *args, **kw):
        """
            The arguments passed to the 'create_user_folders' hook:

            additional_folders - additional folders to create
            user_folder - user folder
        """

        if not kw.has_key('additional_folders'):
            log.error(_("Plugin %s called without required keyword %s.") %("defaultfolders", "additional_folders"))
            return {}

        try:
            exec("additional_folders = %s" %(kw['additional_folders']))
        except Exception, e:
            log.error(_("Could not parse additional_folders"))
            return {}

        return additional_folders
