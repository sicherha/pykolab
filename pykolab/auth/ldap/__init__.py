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

import ldap

from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.translate import _

class LDAP(object):
    def __init__(self, conf=None):
        if not conf:
            self.conf = Conf()
            self.conf.finalize_conf()
            self.log = self.conf.log
        else:
            self.conf = conf
            self.log = conf.log

        self.ldap = None

    def _connect(self):

        if not self.ldap == None:
            return

        self.log.debug(_("Connecting to LDAP..."), 9)
        uri = self.conf.get('ldap', 'uri')
        self.ldap = ldap.initialize(uri)

    def _disconnect(self):
        del self.ldap
        self.ldap = None

    def _set_user_attribute(self, dn, attribute, value):
        self._connect()
        bind_dn = self.conf.get('ldap', 'bind_dn')
        bind_pw = self.conf.get('ldap', 'bind_pw')
        user_base_dn = self.conf.get('ldap', 'user_base_dn')
        kolab_user_filter = self.conf.get('ldap', 'kolab_user_filter')

        self.ldap.simple_bind(bind_dn, bind_pw)

        self.ldap.modify_s(dn, [(ldap.MOD_REPLACE, attribute, value)])

    def _kolab_users(self):
        self._connect()

        bind_dn = self.conf.get('ldap', 'bind_dn')
        bind_pw = self.conf.get('ldap', 'bind_pw')
        user_base_dn = self.conf.get('ldap', 'user_base_dn')
        kolab_user_filter = self.conf.get('ldap', 'kolab_user_filter')

        self.ldap.simple_bind(bind_dn, bind_pw)

        _users = self.ldap.search_s(user_base_dn, ldap.SCOPE_SUBTREE, kolab_user_filter)

        self._disconnect()

        users = []

        for _user in _users:
            user_attrs = {}

            (user_dn, _user_attrs) = _user
            _user_attrs['dn'] = user_dn

            for key in _user_attrs.keys():
                if type(_user_attrs[key]) == list:
                    if len(_user_attrs[key]) == 1:
                        user_attrs[key.lower()] = ''.join(_user_attrs[key])
                    else:
                        user_attrs[key.lower()] = _user_attrs[key]
                else:
                    # What the heck?
                    user_attrs[key.lower()] = _user_attrs[key]


            user_attrs = self.conf.plugins.exec_hook("set_user_attrs", args=(user_attrs))

            users.append(user_attrs)

        return users

