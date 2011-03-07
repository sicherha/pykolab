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

import logging
import os
import time

from pykolab.conf import Conf
from pykolab.translate import _

class Auth(object):
    """
        This is the Authentication and Authorization module for PyKolab.
    """

    def __init__(self, conf=None):
        """
            Initialize the authentication class.
        """
        self.conf = conf
        self.log = logging.getLogger('pykolab')

        self._auth = {}

    def authenticate(self, login):
        # Login is a list of authentication credentials:
        # 0: username
        # 1: password
        # 2: service
        # 3: realm, optional

        if len(login) == 3:
            # Realm not set
            use_virtual_domains = self.conf.get('imap', 'virtual_domains', quiet=True)
            if use_virtual_domains == "userid":
                print "# Derive domain from login[0]"
            elif not use_virtual_domains:
                print "# Explicitly do not user virtual domains??"
            else:
                # Do use virtual domains, derive domain from login[0]
                print "# Derive domain from login[0]"

        if len(login[0].split('@')) > 1:
            domain = login[0].split('@')[1]
        else:
            domain = self.conf.get("kolab", "primary_domain")

        # realm overrides domain
        if len(login) == 4:
            domain = login[3]

        self.connect(domain)

        retval = self._auth[domain]._authenticate(login, domain)

        return retval

    def connect(self, domain=None):
        """
            Connect to the domain authentication backend using domain, or fall
            back to the primary domain specified by the configuration.
        """

        if domain == None:
            section = 'kolab'
            domain = self.conf.get('kolab', 'primary_domain')
        else:
            section = domain

        if self._auth.has_key(section) and not self._auth[section] == None:
            return

        #print "Connecting to Authentication backend for domain %s" %(domain)

        if not self.conf.has_section(section):
            section = 'kolab'

        if self.conf.get(section, 'auth_mechanism') == 'ldap':
            from pykolab.auth import ldap
            self._auth[domain] = ldap.LDAP(self.conf)
        elif self.conf.get(section, 'auth_mechanism') == 'sql':
            from pykolab.auth import sql
            self._auth[domain] = sql.SQL(self.conf)
        #else:
            ## TODO: Fail more verbose
            #print "COULD NOT FIND AUTHENTICATION MECHANISM FOR DOMAIN %s" %(domain)

        #print self._auth

    def list_domains(self):
        """
            List the domains using the auth_mechanism setting in the kolab
            section of the configuration file, either ldap or sql or (...).

            The actual setting would be used by self.connect(), and stuffed
            into self._auth, for use with self._auth._list_domains()

            For each domain found, returns a two-part tuple of the primary
            domain and a list of secondary domains (aliases).
        """

        # Connect to the global namespace
        self.connect()

        # Find the domains in the authentication backend.
        kolab_primary_domain = self.conf.get('kolab', 'primary_domain')
        domains = self._auth[kolab_primary_domain]._list_domains()

        # If no domains are found, the primary domain is used.
        if len(domains) < 1:
            domains = [(kolab_primary_domain, [])]

        return domains

    def list_users(self, primary_domain, secondary_domains=[]):
        self.connect(domain=primary_domain)
        users = self._auth[primary_domain]._list_users(primary_domain, secondary_domains)
        #print "USERS RETURNED FROM self._auth['%s']._list_users():", users
        return users

    def domain_default_quota(self, domain):
        self.connect(domain=domain)
        print self._auth
        return self._auth[domain]._domain_default_quota(domain)

    def get_user_attribute(self, user, attribute):
        return self._auth[domain]._get_user_attribute(user, attribute)

    def set_user_attribute(self, domain, user, attribute, value):
        self._auth[domain]._set_user_attribute(user, attribute, value)
