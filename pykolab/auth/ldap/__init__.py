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

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.errors import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.auth')
conf = pykolab.getConf()

class LDAP(object):
    """
        Abstraction layer for the LDAP authentication / authorization backend,
        for use with Kolab.
    """

    def __init__(self):
        self.ldap = None
        self.bind = False

    def _authenticate(self, login, domain):
        log.debug(_("Attempting to authenticate user %s in domain %s") %(login, domain), level=8)
        self._connect()
        user_dn = self._find_dn(login[0], domain)
        try:
            log.debug(_("Binding with user_dn %s and password %s") %(user_dn, login[1]))
            # Needs to be synchronous or succeeds and continues setting retval to True!!
            self.ldap.simple_bind_s(user_dn, login[1])
            retval = True
        except:
            retval = False
        return retval

    def _connect(self, domain=None):
        """
            Connect to the LDAP server through the uri configured.

            Pass it a configuration section name to get the ldap options from
            that section instead of the default [ldap] section.
        """
        if not self.ldap == None:
            return

        if domain == None:
            section = 'ldap'
        elif not conf.has_option(domain, uri):
            section = 'ldap'

        log.debug(_("Connecting to LDAP..."), level=8)

        uri = conf.get(section, 'uri')

        log.debug(_("Attempting to use LDAP URI %s") %(uri), level=8)

        trace_level = 0

        # TODO: Perhaps we can be smarter then this!
        if conf.debuglevel >= 9:
            trace_level = 1

        self.ldap = ldap.initialize(uri, trace_level=trace_level)
        self.ldap.protocol_version = 3

    def _bind(self):
        # TODO: Implement some mechanism for r/o, r/w and mgmt binding.
        self._connect()

        if not self.bind:
            # TODO: Use bind credentials for the domain itself.
            bind_dn = conf.get('ldap', 'bind_dn')
            bind_pw = conf.get('ldap', 'bind_pw')

            # TODO: Binding errors control
            try:
                self.ldap.simple_bind_s(bind_dn, bind_pw)
                self.bind = True
            except ldap.SERVER_DOWN:
                # Can't contact LDAP server
                #
                # - Service not started
                # - Service faulty
                # - Firewall
                pass
            except ldap.INVALID_CREDENTIALS:
                log.error(_("Invalid bind credentials"))

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
            domain = conf.get('kolab', 'primary_domain')

        domain_root_dn = self._kolab_domain_root_dn(domain)

        if conf.has_option(domain_root_dn, 'user_base_dn'):
            section = domain_root_dn
        else:
            section = 'ldap'

        user_base_dn = conf.get_raw(section, 'user_base_dn') %({'base_dn': domain_root_dn})

        #print "user_base_dn:", user_base_dn

        if conf.has_option(domain_root_dn, 'kolab_user_filter'):
            section = domain_root_dn
        else:
            section = 'ldap'

        kolab_user_filter = conf.get(section, 'kolab_user_filter', quiet=True)

        if kolab_user_filter == "":
            kolab_user_filter = conf.get('ldap', 'kolab_user_filter')

        search_filter = "(&(%s=%s)%s)" %(conf.get('cyrus-sasl', 'result_attribute'),login,kolab_user_filter)

        #print search_filter

        _results = self._search(user_base_dn, filterstr=search_filter, attrlist=['dn'])

        if len(_results) == 1:
            (_user_dn, _user_attrs) = _results[0]
        else:
            # Retry to find the user_dn with just uid=%s against the root_dn, if the login is not fully qualified
            if len(login.split('@')) < 2:
                search_filter = "(uid=%s)" %(login)
                _results = self._search(domain_root_dn, filterstr=search_filter, attrlist=['dn'])
                if len(_results) == 1:
                    (_user_dn, _user_attrs) = _results[0]
                else:
                    # Overall fail
                    return False
            else:
                return False

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
            try:
                (_result_type, _result_data, _result_msgid, _result_controls) = self.ldap.result3(_search)
            except ldap.NO_SUCH_OBJECT, e:
                log.warning(_("Object %s searched no longer exists") %(base_dn))
                break
            _results.extend(_result_data)
            if (pages % 2) == 0:
                log.debug(_("%d results...") %(len(_results)))

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

        if conf.has_option(domain_root_dn, 'default_quota'):
            return conf.get(domain_root_dn, 'default_quota', quiet=True)
        elif conf.has_option('ldap', 'default_quota'):
            return conf.get('ldap', 'default_quota', quiet=True)
        elif conf.has_option('kolab', 'default_quota'):
            return conf.get('kolab', 'default_quota', quiet=True)

    def _domain_section(self, domain):
        domain_root_dn = self._kolab_domain_root_dn(domain)

        if conf.has_section(domain_root_dn):
            return domain_root_dn
        else:
            return 'ldap'

    def _get_user_attribute(self, user, attribute):
        self._bind()

        result = self._search(user['dn'], ldap.SCOPE_BASE, '(objectclass=*)', [ attribute ])

        if len(result) >= 1:
            (user_dn, user_attrs) = result[0]
        else:
            log.warning(_("Could not get user attribute %s for %s") %(attribute,user['dn']))
            return None

        user_attrs = utils.normalize(user_attrs)
        if not user_attrs.has_key(attribute):
            user_attrs[attribute] = None

        return user_attrs[attribute]


    def _set_user_attribute(self, user, attribute, value):
        self._bind()

        #print "user:", user

        attribute = attribute.lower()

        # TODO: This should be a schema check!
        if attribute in [ 'mailquota', 'mailalternateaddress' ]:
            if not user.has_key('objectclass'):
                user['objectclass'] = self._get_user_attribute(user,'objectclass')
                if user['objectclass'] == None:
                    return
            if not 'mailrecipient' in user['objectclass']:
                user['objectclass'].append('mailrecipient')
                self._set_user_attribute(user, 'objectclass', user['objectclass'])

        try:
            self.ldap.modify(user['dn'], [(ldap.MOD_REPLACE, attribute, value)])
        except:
            log.warning(_("LDAP modification of attribute %s" + \
                " for %s to value %s failed") %(attribute,user_dn,value))

    def _list_domains(self):
        """
            Find the domains related to this Kolab setup, and return a list of
            DNS domain names.

            Returns a list of tuples, each tuple containing the primary domain
            name and a list of secondary domain names.
        """

        log.info(_("Listing domains..."))

        self._connect()

        bind_dn = conf.get('ldap', 'bind_dn')
        bind_pw = conf.get('ldap', 'bind_pw')

        domain_base_dn = conf.get('ldap', 'domain_base_dn', quiet=True)

        if domain_base_dn == "":
            # No domains are to be found in LDAP, return an empty list.
            # Note that the Auth() base itself handles this case.
            return []

        # If we haven't returned already, let's continue searching
        kolab_domain_filter = conf.get('ldap', 'kolab_domain_filter')

        # TODO: this function should be wrapped for error handling
        try:
            self.ldap.simple_bind_s(bind_dn, bind_pw)
        except ldap.SERVER_DOWN, e:
            raise AuthBackendError, _("Authentication database DOWN")

        _search = self._search(
                domain_base_dn,
                ldap.SCOPE_SUBTREE,
                kolab_domain_filter,
                # TODO: Where we use associateddomain is actually configurable
                [ 'associateddomain' ]
            )

        domains = []

        for domain_dn, domain_attrs in _search:
            primary_domain = None
            secondary_domains = []

            domain_attrs = utils.normalize(domain_attrs)

            # TODO: Where we use associateddomain is actually configurable
            if type(domain_attrs['associateddomain']) == list:
                primary_domain = domain_attrs['associateddomain'].pop(0)
                secondary_domains = domain_attrs['associateddomain']
            else:
                primary_domain = domain_attrs['associateddomain']

            domains.append((primary_domain,secondary_domains))

        return domains

    def _kolab_domain_root_dn(self, domain):
        self._bind()

        log.debug(_("Finding domain root dn for domain %s") %(domain), level=8)

        bind_dn = conf.get('ldap', 'bind_dn')
        bind_pw = conf.get('ldap', 'bind_pw')

        domain_base_dn = conf.get('ldap', 'domain_base_dn', quiet=True)

        if not domain_base_dn == "":

            # If we haven't returned already, let's continue searching
            domain_name_attribute = conf.get('ldap', 'domain_name_attribute')

            _results = self._search(
                    domain_base_dn,
                    ldap.SCOPE_SUBTREE,
                    "(%s=%s)" %(domain_name_attribute,domain)
                )

            domains = []
            for _domain in _results:
                (domain_dn, _domain_attrs) = _domain
                domain_rootdn_attribute = conf.get('ldap', 'domain_rootdn_attribute')
                _domain_attrs = utils.normalize(_domain_attrs)
                if _domain_attrs.has_key(domain_rootdn_attribute):
                    return _domain_attrs[domain_rootdn_attribute]

        return utils.standard_root_dn(domain)

    def _list_users(self, primary_domain, secondary_domains=[]):

        log.info(_("Listing users for domain %s (and %s)") %(primary_domain, ' '.join(secondary_domains)))

        self._bind()

        # TODO: Bind with read-only credentials, perhaps even domain-specific, please
        bind_dn = conf.get('ldap', 'bind_dn')
        #bind_dn = conf.get('ldap', 'ro_bind_dn')
        bind_pw = conf.get('ldap', 'bind_pw')
        #bind_pw = conf.get('ldap', 'ro_bind_pw')

        domain_root_dn = self._kolab_domain_root_dn(primary_domain)

        if conf.has_option(domain_root_dn, 'user_base_dn'):
            section = domain_root_dn
        else:
            section = 'ldap'

        user_base_dn = conf.get_raw(section, 'user_base_dn') %({'base_dn': domain_root_dn})

        if conf.has_option(domain_root_dn, 'kolab_user_filter'):
            section = domain_root_dn
        else:
            section = 'ldap'

        kolab_user_filter = conf.get(section, 'kolab_user_filter', quiet=True)

        if kolab_user_filter == "":
            kolab_user_filter = conf.get('ldap', 'kolab_user_filter')

        self.ldap.simple_bind_s(bind_dn, bind_pw)

        # TODO: The quota and alternative address attributes are actually
        # supposed to be settings.
        _search = self._search(
                user_base_dn,
                ldap.SCOPE_SUBTREE,
                kolab_user_filter,
                attrlist=[ 'dn', 'mail', 'mailquota', 'mailalternateaddress', 'sn', 'givenname', 'cn', 'uid' ],
                attrsonly=0
            )

        log.debug(_("Iterating over %d users, making sure we have the necessary attributes...") %(len(_search)))

        #print "SEARCH RESULTS:", _search

        users = []

        num_users = len(_search)
        num_user = 0

        for user_dn, user_attrs in _search:
            num_user += 1
            user = {}
            user['dn'] = user_dn
            if not user.has_key('standard_domain'):
                user['standard_domain'] = (primary_domain, secondary_domains)

            user_attrs = utils.normalize(user_attrs)

            #print "USER_ATTRS:", user_attrs

            for attribute in [ 'mail', 'mailalternateaddress', 'sn', 'givenname', 'cn', 'uid' ]:
                if not user_attrs.has_key(attribute):
                    #print "doesn't have attribute"
                    user[attribute] = self._get_user_attribute(user, attribute)
                else:
                    #print "has attribute"
                    user[attribute] = user_attrs[attribute]

            #print "============== EXECING PLUGINS ================="

            if conf.has_option(domain_root_dn, 'primary_mail'):
                primary_mail = conf.plugins.exec_hook("set_primary_mail",
                        kw={
                                'primary_mail': conf.get_raw(domain_root_dn, 'primary_mail'),
                                'user_attrs': user_attrs,
                                'primary_domain': primary_domain,
                                'secondary_domains': secondary_domains
                            }
                    )

                if not primary_mail == None:
                    if not user.has_key('mail'):
                        self._set_user_attribute(user, 'mail', primary_mail)
                        user['mail'] = primary_mail
                    else:
                        if not primary_mail == user['mail']:
                            user['old_mail'] = user['mail']
                            user['mail'] = primary_mail

                section = None

                if conf.has_option(domain_root_dn, 'secondary_mail'):
                    section = domain_root_dn
                elif conf.has_option('kolab', 'secondary_mail'):
                    section = 'kolab'

                if not section == None:
                    secondary_mail = conf.plugins.exec_hook("set_secondary_mail", kw={
                                'secondary_mail': conf.get_raw(domain_root_dn, 'secondary_mail'),
                                'user_attrs': user_attrs,
                                'primary_domain': primary_domain,
                                'secondary_domains': secondary_domains
                            }
                        )

                if not secondary_mail == None:
                    secondary_mail = list(set(secondary_mail))
                    if not user.has_key('mailalternateaddress'):
                        self._set_user_attribute(user, 'mailalternateaddress', secondary_mail)
                        user['mailalternateaddress'] = secondary_mail
                    else:
                        if not secondary_mail == user['mailalternateaddress']:
                            user['mailalternateaddress'] = secondary_mail

            users.append(user)

            if (num_user % 1000) == 0:
                log.info(_("Done iterating over user %d of %d") %(num_user,num_users))

        #print "USERS:", users

        return users

#class SyncControl(ldap.controls.LDAPControl):
    #controlType = '(1.3.6.1.4.1.4203.1.9.1.1'
    #def __init__(self, controlType, criticality, controlValue=None, encodedControlValue=None):
        #LDAPControl.__init__(self, controlType, criticality, controlValue, encodedControlValue)

    #def encodeControlValue(self, value):

