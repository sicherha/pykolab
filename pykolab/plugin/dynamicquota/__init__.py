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

class KolabDynamicquota(object):
    """
        Example plugin making quota adjustments given arbitrary conditions.
    """

    def __init__(self, conf=None):
        if not conf == None:
            self.conf = conf
        pass

    def set_user_folder_quota(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_folder_quota' hook:

            - used (integer, in KB)
            - current quota (integer, in KB)
            - quota (integer, in KB)
        """

        (used, current_quota, new_quota) = args

        # Escape the user without quota
        if new_quota == 0:
            return 0

        # Make your adjustments here, for example:
        #
        # - increase the quota by 10% if the currently used storage size
        #   is over 90%

        if new_quota < int(float(used) * 1.1):
            new_quota = int(float(used) * 1.1)
        elif new_quota > int(float(used) * 1.1):
            new_quota = int(float(current_quota) * 0.9)

        return new_quota
