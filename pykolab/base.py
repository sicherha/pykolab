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
from pykolab.imap import IMAP

conf = pykolab.getConf()

class Base(object):
    """
        Abstraction class for functions commonly shared between auth, imap, etc.
    """
    def __init__(self, *args, **kw):
        if kw.has_key('domain') and not kw['domain'] == None:
            self.domain = kw['domain']
        else:
            self.domain = conf.get('kolab', 'primary_domain')

        # Placeholder primary_domain => [secondary_domains]. Should be updated
        # on auth backend _connect().
        self.domains = None

        self.imap = IMAP()
        self.domain_rootdns = {}

    def config_get(self, key1, key2=None, default=None):
        if key2 is not None:
            return conf.get(key1, key2, default=default)

        if conf.has_option(self.domain, key1):
            return conf.get(self.domain, key1)

        if conf.has_option(self.domain, 'auth_mechanism'):
            if conf.has_option(conf.get(self.domain, 'auth_mechanism'), key1):
                return conf.get(conf.get(self.domain, 'auth_mechanism'), key1)

        if conf.has_option(conf.get('kolab', 'auth_mechanism'), key1):
            return conf.get(conf.get('kolab', 'auth_mechanism'), key1)

        if conf.has_option('kolab', key1):
            return conf.get('kolab', key1)

        return default

    def config_get_list(self, key1, key2=None, default=None):
        if key2 is not None:
            return conf.get_list(key1, key2, default=default)

        if conf.has_option(self.domain, key1):
            return conf.get_list(self.domain, key1)

        if conf.has_option(self.domain, 'auth_mechanism'):
            if conf.has_option(conf.get(self.domain, 'auth_mechanism'), key1):
                return conf.get_list(conf.get(self.domain, 'auth_mechanism'), key1)

        if conf.has_option(conf.get('kolab', 'auth_mechanism'), key1):
            return conf.get_list(conf.get('kolab', 'auth_mechanism'), key1)

        if conf.has_option('kolab', key1):
            return conf.get_list('kolab', key1)

        return default

    def config_get_raw(self, key1, key2=None, default=None):
        if key2 is not None:
            return conf.get_raw(key1, key2, default=default)

        if conf.has_option(self.domain, key1):
            return conf.get_raw(self.domain, key1)

        if conf.has_option(self.domain, 'auth_mechanism'):
            if conf.has_option(conf.get(self.domain, 'auth_mechanism'), key1):
                return conf.get_raw(conf.get(self.domain, 'auth_mechanism'), key1)

        if conf.has_option(conf.get('kolab', 'auth_mechanism'), key1):
            return conf.get_raw(conf.get('kolab', 'auth_mechanism'), key1)

        if conf.has_option('kolab', key1):
            return conf.get_raw('kolab', key1)

        return default

