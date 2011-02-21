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

class Defaults(object):
    def __init__(self, plugins=None):
        # Each possible section in the configuration has a dict here.

        # The default authentication mechanism
        self.kolab = {
                'auth_mechanism': 'ldap',
            }

        # The default LDAP URI. Note that these are
        # prefixed with the section name.
        self.ldap   = {
                'uri': "ldap://localhost",
                'base_dn': "dc=localhost,dc=localdomain",
                'bind_dn': "",
                'bind_pw': "",
                'user_base_dn': "ou=People,%(base_dn)s",
                'group_base_dn': "ou=Groups,%(base_dn)s",
                'kolab_user_filter': '(objectClass=*)'
            }

        self.testing = {
                'admin_password': 'secret',
                'admin_login': 'manager',
                'server': '127.0.0.1',
                'users': []
            }