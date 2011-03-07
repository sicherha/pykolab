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

class KolabDynamicquota(object):
    """
        Example plugin making quota adjustments given arbitrary conditions.
    """

    def __init__(self, conf=None):
        self.conf = conf

    def set_user_folder_quota(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_folder_quota' hook:

            - used (integer, in KB)
            - current quota (integer, in KB)
            - quota (integer, in KB)
        """

        #print args

        (used, current_quota, new_quota, default_quota) = args

        # Escape the user without quota
        if new_quota == 0:
            # Unless default quota is set
            if default_quota > 0:
                #print "new quota is 0, but default quota > 0, returning default quota"
                return default_quota

            #print "new quota is 0, and default quota is no larger then 0, returning 0"
            return 0

        # Make your adjustments here, for example:
        #
        # - increase the quota by 10% if the currently used storage size
        #   is over 90%

        if new_quota < int(float(used) * 1.1):
            #print "new quota is smaller then 110%% of what is currently used, returning 110%% of used"
            new_quota = int(float(used) * 1.1)
        elif new_quota > int(float(used) * 1.1):
            # TODO: If the current quota in IMAP had been set to 0, but we want to apply quota, and
            # 0 is current_quota, 90% of that is still 0...
            #print "new quota is larger then 110%% of what is currently used, returning 90%% of current quota"
            new_quota = int(float(current_quota) * 0.9)

        if default_quota > new_quota:
            #print "default quota is more then the calculated new quota"
            return default_quota

        return new_quota
