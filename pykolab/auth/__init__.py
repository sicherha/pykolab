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
        if hasattr(self.conf, "log"):
            self.log = self.conf.log

        self._auth = None

    def _connect(self):
        if not self._auth == None:
            return

        if self.conf.get('kolab', 'auth_mechanism') == 'ldap':
            try:
                from pykolab.auth import ldap
            except:
                if hasattr(self, "log"):
                    self.log.error(_("Failure to import authentication layer %s," +
                        " please verify module dependencies have been installed") % "ldap")
            self._auth = ldap.LDAP(self.conf)

    def users(self):
        self._connect()
        users = self._auth._kolab_users()
        return users

    def set_user_attribute(self, user, attribute, value):
        self._connect()
        self._auth._set_user_attribute(user, attribute, value)

