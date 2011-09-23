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
log = pykolab.getLogger('pykolab.plugins.dynamicquota')

class KolabDynamicquota(object):
    """
        Example plugin making quota adjustments given arbitrary conditions.
    """

    def __init__(self):
        pass

    def add_options(self, *args,  **kw):
        pass

    def set_user_folder_quota(self, *args, **kw):
        """
            The arguments passed to the 'set_user_folder_quota' hook:

            - used (integer, in KB)
            - current quota (integer, in KB)
            - quota (integer, in KB)
        """

        for keyword in [ 'used', 'current_quota', 'new_quota', 'default_quota' ]:
            if not kw.has_key(keyword):
                log.warning(_("No keyword %s passed to set_user_folder_quota") %(keyword))
                return 0
            else:
                try:
                    kw[keyword] = (int)(kw[keyword])
                except:
                    log.error(_("Quota '%s' not an integer!") %(keyword))
                    return 0

        # Escape the user without quota
        if kw['new_quota'] == 0:
            # Unless default quota is set
            if kw['default_quota'] > 0:
                log.info(_("The new quota was set to 0, but default quota > 0, returning default quota"))
                return kw['default_quota']

            return 0

        # Make your adjustments here, for example:
        #
        # - increase the quota by 10% if the currently used storage size
        #   is over 90%

        if kw['new_quota'] < int(float(kw['used']) * 1.1):
            _new_quota = int(float(kw['used']) * 1.1)
        elif kw['new_quota'] > int(float(kw['used']) * 1.1):
            # TODO: If the current quota in IMAP had been set to 0, but we want to apply quota, and
            # 0 is current_quota, 90% of that is still 0...
            _new_quota = int(float(kw['current_quota']) * 0.9)

        if kw['new_quota'] == 0:
            if kw['default_quota'] > _new_quota:
                log.info(_("The default quota is larger then the calculated new quota, using the default quota"))
                return kw['default_quota']

            else:
                new_quota = _new_quota
        else:
            new_quota = kw['new_quota']

        return new_quota
