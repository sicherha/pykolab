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

import logging

class Defaults(object):
    def __init__(self, plugins=None):
        self.loglevel = logging.CRITICAL

        self.imap_virtual_domains = 'userid'

        # An integer or float to indicate the interval at which the Cyrus IMAP
        # library should try to retrieve annotations
        self.cyrus_annotations_retry_interval = 1

        self.address_search_attrs = ['mail', 'alias']
        self.mail_attributes = ['mail', 'alias']
        self.mailserver_attribute = 'mailhost'

        # when you want a new domain to be added in a short time, you should reduce this value to 10 seconds
        self.kolab_domain_sync_interval = 600

        self.kolab_default_locale = 'en_US'
        self.ldap_unique_attribute = 'nsuniqueid'

        self.wallace_resource_calendar_expire_days = 100