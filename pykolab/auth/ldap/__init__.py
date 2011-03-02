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
import time

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

        self.log.debug(_("Connecting to LDAP..."), level=9)
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

        try:
            self.ldap.modify(dn, [(ldap.MOD_REPLACE, attribute, value)])
        except:
            if hasattr(self.conf, "log"):
                self.conf.log.warning(_("LDAP modification of attribute %s" + \
                    " to value %s failed") %(attribute,value))
            else:
                # Cannot but print in case someone's interested
                print "LDAP modification of attribute %s to value %s" + \
                    " failed" %(attribute,value)
            self._disconnect()

    def _kolab_users(self):
        self._connect()

        bind_dn = self.conf.get('ldap', 'bind_dn')
        bind_pw = self.conf.get('ldap', 'bind_pw')
        user_base_dn = self.conf.get('ldap', 'user_base_dn')
        kolab_user_filter = self.conf.get('ldap', 'kolab_user_filter')

        self.ldap.simple_bind(bind_dn, bind_pw)

        _search = self.ldap.search(
                user_base_dn,
                ldap.SCOPE_SUBTREE,
                kolab_user_filter
            )

        users = []
        _result_type = None

        while not _result_type == ldap.RES_SEARCH_RESULT:
            (_result_type, _users) = self.ldap.result(_search, False, 0)
            if not _users == None:
                for _user in _users:
                    user_attrs = {}

                    (user_dn, _user_attrs) = _user
                    _user_attrs['dn'] = user_dn

                    self.conf.log.debug(_("Found user %s") %(user_dn), level=9)

                    for key in _user_attrs.keys():
                        if type(_user_attrs[key]) == list:
                            if len(_user_attrs[key]) == 1:
                                user_attrs[key.lower()] = ''.join(_user_attrs[key])
                            else:
                                user_attrs[key.lower()] = _user_attrs[key]
                        else:
                            # What the heck?
                            user_attrs[key.lower()] = _user_attrs[key]

                    # Execute plugin hooks that may change the value(s) of the
                    # user attributes we are going to be using.
                    mail = self.conf.plugins.exec_hook("set_user_attrs_mail", args=(user_attrs))
                    alternative_mail = self.conf.plugins.exec_hook("set_user_attrs_alternative_mail", args=(user_attrs))

                    if not mail == user_attrs['mail']:
                        self._set_user_attribute(user_attrs['dn'], "mail", mail)

                    if len(alternative_mail) > 0:
                        # Also make sure the required object class is available.
                        if not "mailrecipient" in user_attrs['objectclass']:
                            user_attrs['objectclass'].append('mailrecipient')
                            self._set_user_attribute(user_attrs['dn'], 'objectclass', user_attrs['objectclass'])

                    self._set_user_attribute(user_attrs['dn'], 'mailalternateaddress', alternative_mail)

                    users.append(user_attrs)

        return users

