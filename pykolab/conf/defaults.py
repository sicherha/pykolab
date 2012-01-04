# -*- coding: utf-8 -*-
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
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

import logging

class Defaults(object):
    def __init__(self, plugins=None):
        self.loglevel = logging.CRITICAL

        self.virtual_domains = 'userid'

        # An integer or float to indicate the interval at which the Cyrus IMAP
        # library should try to retrieve annotations
        self.cyrus_annotations_retry_interval = 1

        self.address_search_attrs = "mail, alias"

        self.kolab_default_locale = 'en_US'
