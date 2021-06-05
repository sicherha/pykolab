# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
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
            - imap_quota (current imap quota obtained from IMAP, integer, in KB)
            - ldap_quota (current LDAP quota obtained from LDAP, integer, in KB)
            - default_quota (integer, in KB)

            Returns:

            - None - an error has occurred and this plugin doesn't care.
            - Negative 1 - remove quota.
            - Zero - Absolute 0.
            - Positive Integer - set new quota.
        """

        for keyword in [ 'used', 'imap_quota', 'ldap_quota', 'default_quota' ]:
            if keyword not in kw:
                log.warning(
                        _("No keyword %s passed to set_user_folder_quota") % (
                                keyword
                            )
                    )

                return
            else:
                try:
                    if not kw[keyword] == None:
                        kw[keyword] = (int)(kw[keyword])

                except:
                    log.error(_("Quota '%s' not an integer!") % (keyword))
                    return

        # Escape the user without quota
        if kw['ldap_quota'] == None:
            return kw['default_quota']
        elif kw['ldap_quota'] == -1:
            return -1
        elif kw['ldap_quota'] > 0:
            return kw['ldap_quota']
        else:
            return kw['default_quota']