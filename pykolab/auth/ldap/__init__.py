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

import _ldap
import ldap
import ldap.async
import ldap.controls
import ldap.resiter
import logging
import time

from pykolab import utils
from pykolab.conf import Conf
from pykolab.constants import *
from pykolab.translate import _

class LDAP(object):
    """
        Abstraction layer for the LDAP authentication / authorization backend,
        for use with Kolab.
    """

    def __init__(self, conf):
        self.conf = conf
        self.log = logging.getLogger('pykolab.ldap')
        self.ldap = None
        self.bind = False

    def _authenticate(self, login, domain):
        print "Authenticating:", login, domain
        self._connect()
        user_dn = self._find_dn(login[0], domain)
        try:
            print "Binding with user_dn %s and password %s" %(user_dn, login[1])
            # Needs to be synchronous or succeeds and continues setting retval to True!!
            self.ldap.simple_bind_s(user_dn, login[1])
            retval = True
        except:
            retval = False
        return retval

    def _connect(self, domain=None):
        if not self.ldap == None:
            return

        if domain == None:
            section = 'ldap'
        elif not self.conf.has_option(domain, uri):
            section = 'ldap'

        self.log.debug(_("Connecting to LDAP..."))

        uri = self.conf.get(section, 'uri')

        self.log.debug(_("Attempting to use LDAP URI %s") %(uri))
        self.ldap = ldap.initialize(uri, trace_level=0)
        self.ldap.protocol_version = 3

    def _bind(self):
        # TODO: Implement some mechanism for r/o, r/w and mgmt binding.
        self._connect()

        if not self.bind:
            # TODO: Use bind credentials for the domain itself.
            bind_dn = self.conf.get('ldap', 'bind_dn')
            bind_pw = self.conf.get('ldap', 'bind_pw')
            # TODO: Binding errors control
            try:
                self.ldap.simple_bind_s(bind_dn, bind_pw)
            except ldap.SERVER_DOWN:
                # Can't contact LDAP server
                #
                # - Service not started
                # - Service faulty
                # - Firewall
                pass

            self.bind = True

    def _unbind(self):
        self.ldap.unbind()
        self.bind = False

    def _reconnect(self):
        self._disconnect()
        self._connect()

    def _disconnect(self):
        self._unbind()
        del self.ldap
        self.ldap = None
        self.bind = False

    def _find_dn(self, login, domain=None):
        self._connect()
        self._bind()

        if domain == None:
            domain = self.conf.get('kolab', 'primary_domain')

        domain_root_dn = self._kolab_domain_root_dn(domain)

        if self.conf.has_option(domain_root_dn, 'user_base_dn'):
            section = domain_root_dn
        else:
            section = 'ldap'

        user_base_dn = self.conf.get_raw(section, 'user_base_dn') %({'base_dn': domain_root_dn})

        print "user_base_dn:", user_base_dn

        if self.conf.has_option(domain_root_dn, 'kolab_user_filter'):
            section = domain_root_dn
        else:
            section = 'ldap'

        kolab_user_filter = self.conf.get(section, 'kolab_user_filter', quiet=True)

        if kolab_user_filter == "":
            kolab_user_filter = self.conf.get('ldap', 'kolab_user_filter')

        search_filter = "(&(%s=%s)%s)" %(self.conf.get('cyrus-sasl', 'result_attribute'),login,kolab_user_filter)

        print search_filter

        _results = self._search(user_base_dn, filterstr=search_filter, attrlist=['dn'])

        if not len(_results) == 1:
            return False

        (_user_dn, _user_attrs) = _results[0]

        return _user_dn

    def _search(self, base_dn, scope=ldap.SCOPE_SUBTREE, filterstr="(objectClass=*)", attrlist=None, attrsonly=0, timeout=-1):
        _results = []

        page_size = 500
        critical = True

        server_page_control = ldap.controls.SimplePagedResultsControl(
                        ldap.LDAP_CONTROL_PAGE_OID,
                        critical,
                        (page_size, '')
                    )

        _search = self.ldap.search_ext(
                base_dn,
                scope=scope,
                filterstr=filterstr,
                attrlist=attrlist,
                attrsonly=attrsonly,
                serverctrls=[server_page_control]
            )

        pages = 0
        while True:
            pages += 1
            #print "Getting page %d..." %(pages)
            (_result_type, _result_data, _result_msgid, _result_controls) = self.ldap.result3(_search)
            _results.extend(_result_data)
            if (pages % 2) == 0:
                self.log.debug(_("%d results...") %(len(_results)))

            pctrls = [c for c in _result_controls if c.controlType == ldap.LDAP_CONTROL_PAGE_OID]

            if pctrls:
                est, cookie = pctrls[0].controlValue
                if cookie:
                    server_page_control.controlValue = (page_size, cookie)
                    _search = self.ldap.search_ext(
                            base_dn,
                            scope=scope,
                            filterstr=filterstr,
                            attrlist=attrlist,
                            attrsonly=attrsonly,
                            serverctrls=[server_page_control]
                        )
                else:
                    # TODO: Error out more verbose
                    break
            else:
                # TODO: Error out more verbose
                print "Warning:  Server ignores RFC 2696 control."
                break

        return _results

    def _result(self, msgid=ldap.RES_ANY, all=1, timeout=-1):
        return self.ldap.result(msgid, all, timeout)

    def _domain_default_quota(self, domain):
        domain_root_dn = self._kolab_domain_root_dn(domain)

        if self.conf.cfg_parser.has_option(domain_root_dn, 'default_quota'):
            return self.conf.get(domain_root_dn, 'default_quota', quiet=True)
        elif self.conf.cfg_parser.has_option('ldap', 'default_quota'):
            return self.conf.get('ldap', 'default_quota', quiet=True)
        elif self.conf.cfg_parser.has_option('kolab', 'default_quota'):
            return self.conf.get('kolab', 'default_quota', quiet=True)

    def _get_user_attribute(self, user, attribute):
        self._bind()

        (user_dn, user_attrs) = self._search(user, ldap.SCOPE_BASE, '(objectclass=*)', [ attribute ])[0]

        user_attrs = utils.normalize(user_attrs)
        return user_attrs[attribute]

    def _set_user_attribute(self, user, attribute, value):
        self._bind()

        #print "user:", user

        if type(user) == dict:
            user_dn = user['dn']
        elif type(user) == str:
            user_dn = user

        try:
            self.ldap.modify(user_dn, [(ldap.MOD_REPLACE, attribute, value)])
        except:
            self.log.warning(_("LDAP modification of attribute %s" + \
                " for %s to value %s failed") %(attribute,user_dn,value))

    def _list_domains(self):
        """
            Find the domains related to this Kolab setup, and return a list of
            DNS domain names.

            Returns a list of tuples, each tuple containing the primary domain
            name and a list of secondary domain names.
        """

        self.log.info(_("Listing domains..."))

        self._connect()

        bind_dn = self.conf.get('ldap', 'bind_dn')
        bind_pw = self.conf.get('ldap', 'bind_pw')

        domain_base_dn = self.conf.get('ldap', 'domain_base_dn', quiet=True)

        if domain_base_dn == "":
            # No domains are to be found in LDAP, return an empty list.
            # Note that the Auth() base itself handles this case.
            return []

        # If we haven't returned already, let's continue searching
        kolab_domain_filter = self.conf.get('ldap', 'kolab_domain_filter')

        # TODO: this function should be wrapped for error handling
        self.ldap.simple_bind(bind_dn, bind_pw)

        _search = self.ldap.search(
                domain_base_dn,
                ldap.SCOPE_SUBTREE,
                kolab_domain_filter,
                # TODO: Where we use associateddomain is actually configurable
                [ 'associateddomain' ]
            )

        domains = []
        _result_type = None

        while not _result_type == ldap.RES_SEARCH_RESULT:
            try:
                (_result_type, _domains) = self._result(_search, False, 0)
            except AttributeError, e:
                if self.ldap == None:
                    self._bind()
                continue
            if not _domains == None:
                for _domain in _domains:
                    (domain_dn, _domain_attrs) = _domain
                    primary_domain = None
                    secondary_domains = []

                    _domain_attrs = utils.normalize(_domain_attrs)

                    # TODO: Where we use associateddomain is actually configurable
                    if type(_domain_attrs['associateddomain']) == list:
                        primary_domain = _domain_attrs['associateddomain'].pop(0)
                        secondary_domains = _domain_attrs['associateddomain']
                    else:
                        primary_domain = _domain_attrs['associateddomain']

                    domains.append((primary_domain,secondary_domains))

        return domains

    def _kolab_domain_root_dn(self, domain):
        self._bind()

        print "Finding domain root dn for domain %s" %(domain)

        bind_dn = self.conf.get('ldap', 'bind_dn')
        bind_pw = self.conf.get('ldap', 'bind_pw')

        domain_base_dn = self.conf.get('ldap', 'domain_base_dn', quiet=True)

        if not domain_base_dn == "":

            # If we haven't returned already, let's continue searching
            domain_name_attribute = self.conf.get('ldap', 'domain_name_attribute')

            _results = self._search(
                    domain_base_dn,
                    ldap.SCOPE_SUBTREE,
                    "(%s=%s)" %(domain_name_attribute,domain)
                )

            domains = []
            for _domain in _results:
                (domain_dn, _domain_attrs) = _domain
                domain_rootdn_attribute = self.conf.get('ldap', 'domain_rootdn_attribute')
                _domain_attrs = utils.normalize(_domain_attrs)
                if _domain_attrs.has_key(domain_rootdn_attribute):
                    return _domain_attrs[domain_rootdn_attribute]

        return utils.standard_root_dn(domain)

    def _list_users(self, primary_domain, secondary_domains=[]):

        self.log.info(_("Listing users for domain %s") %(primary_domain))

        self._bind()

        # With read-only credentials please
        bind_dn = self.conf.get('ldap', 'bind_dn')
        #bind_dn = self.conf.get('ldap', 'ro_bind_dn')
        bind_pw = self.conf.get('ldap', 'bind_pw')
        #bind_pw = self.conf.get('ldap', 'ro_bind_pw')

        domain_root_dn = self._kolab_domain_root_dn(primary_domain)

        if self.conf.has_option(domain_root_dn, 'user_base_dn'):
            section = domain_root_dn
        else:
            section = 'ldap'

        user_base_dn = self.conf.get_raw(section, 'user_base_dn') %({'base_dn': domain_root_dn})

        if self.conf.has_option(domain_root_dn, 'kolab_user_filter'):
            section = domain_root_dn
        else:
            section = 'ldap'

        kolab_user_filter = self.conf.get(section, 'kolab_user_filter', quiet=True)

        if kolab_user_filter == "":
            kolab_user_filter = self.conf.get('ldap', 'kolab_user_filter')

        self.ldap.simple_bind(bind_dn, bind_pw)

        # TODO: For (very) large result sets, this may hit a limit and we need
        # it to just continue.
        #
        _search = self._search(
                user_base_dn,
                ldap.SCOPE_SUBTREE,
                kolab_user_filter,
                attrlist=[ 'dn', 'mail', 'sn', 'givenname', 'cn', 'uid' ],
                attrsonly=0
            )

        self.log.debug(_("Iterating over %d users, making sure we have the necessary attributes...") %(len(_search)))

        #print "SEARCH RESULTS:", _search

        users = []
        _result_type = None

        for user_dn, user_attrs in _search:
            user = {}
            user['dn'] = user_dn
            if not user.has_key('standard_domain'):
                user['standard_domain'] = (primary_domain, secondary_domains)

            user_attrs = utils.normalize(user_attrs)

            #print "USER_ATTRS:", user_attrs

            for attribute in [ 'mail', 'sn', 'givenname', 'cn', 'uid' ]:
                if not user_attrs.has_key(attribute):
                    #print "doesn't have attribute"
                    user[attribute] = self._get_user_attribute(user_dn, attribute)
                else:
                    #print "has attribute"
                    user[attribute] = user_attrs[attribute]

            users.append(user)

        #print "USERS:", users

        return users
