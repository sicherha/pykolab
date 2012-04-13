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

import _ldap
import ldap
import ldap.async
import ldap.controls
import logging
import time

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.errors import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.auth')
conf = pykolab.getConf()

# Catch python-ldap-2.4 changes
from distutils import version

if version.StrictVersion('2.4.0') <= version.StrictVersion(ldap.__version__):
    LDAP_CONTROL_PAGED_RESULTS = ldap.CONTROL_PAGEDRESULTS
else:
    LDAP_CONTROL_PAGED_RESULTS = ldap.LDAP_CONTROL_PAGE_OID

try:
    from ldap.controls import psearch
except:
    log.warning(_("Python LDAP library does not support persistent search"))

class SimplePagedResultsControl(ldap.controls.SimplePagedResultsControl):
    """

        Python LDAP 2.4 and later breaks the API. This is an abstraction class
        so that we can handle either.
    """

    def __init__(self, page_size=0, cookie=''):
        if version.StrictVersion(
                '2.4.0'
            ) <= version.StrictVersion(
                    ldap.__version__
                ):

            ldap.controls.SimplePagedResultsControl.__init__(
                    self,
                    size=page_size,
                    cookie=cookie
                )
        else:
            ldap.controls.SimplePagedResultsControl.__init__(
                    self,
                    LDAP_CONTROL_PAGED_RESULTS,
                    True,
                    (page_size, '')
                )

    def cookie(self):
        if version.StrictVersion(
                '2.4.0'
            ) <= version.StrictVersion(
                    ldap.__version__
                ):

            return self.cookie
        else:
            return self.controlValue[1]

    def size(self):
        if version.StrictVersion(
                '2.4.0'
            ) <= version.StrictVersion(
                    ldap.__version__
                ):

            return self.size
        else:
            return self.controlValue[0]

class LDAP(object):
    """
        Abstraction layer for the LDAP authentication / authorization backend,
        for use with Kolab.
    """

    def __init__(self):
        self.ldap = None
        self.bind = False

    def _authenticate(self, login, domain):
        log.debug(_("Attempting to authenticate user %s in domain %s")
            % (login, domain), level=8)

        self._connect()
        user_dn = self._find_dn(login[0], domain)
        try:
            log.debug(_("Binding with user_dn %s and password %s")
                % (user_dn, login[1]))

            # Needs to be synchronous or succeeds and continues setting retval
            # to True!!
            self.ldap.simple_bind_s(user_dn, login[1])
            retval = True
        except:
            log.debug(
                    _("Failed to authenticate as user %s") % (user_dn),
                    level=8
                )

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
            key = 'uri'

        if conf.has_option(domain, 'uri'):
            log.warning(_("Deprecation: Setting 'uri' for LDAP in section %s needs to be updated to 'ldap_uri'") % (domain))
            section = domain
            key = 'uri'
        elif conf.has_option(domain, 'ldap_uri'):
            section = domain
            key = 'ldap_uri'

        log.debug(_("Connecting to LDAP..."), level=8)

        uri = conf.get(section, key)

        log.debug(_("Attempting to use LDAP URI %s") % (uri), level=8)

        trace_level = 0

        if conf.debuglevel > 8:
            trace_level = 1

        self.ldap = ldap.initialize(uri, trace_level=trace_level)
        self.ldap.protocol_version = 3
        self.ldap.supported_controls = []

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
        """
            Find the distinguished name (DN) for an entry in LDAP.

        """
        self._connect()
        self._bind()

        if domain == None:
            domain = conf.get('kolab', 'primary_domain')

        domain_root_dn = self._kolab_domain_root_dn(domain)

        if conf.has_option(domain, 'base_dn'):
            section = domain
        else:
            section = 'ldap'

        user_base_dn = conf.get_raw(section, 'base_dn')

        if conf.has_option(domain, 'user_filter'):
            section = domain
        else:
            section = 'ldap'

        user_filter = conf.get(section, 'user_filter', quiet=True)

        if user_filter == "":
            user_filter = conf.get('ldap', 'user_filter')

        if conf.has_option(section, 'auth_attrs'):
            auth_search_attrs = conf.get_list(section, 'auth_attrs')
        elif conf.has_section('kolab_smtp_access_policy'):
            if conf.has_option('kolab_smtp_access_policy', 'address_search_attrs'):
                log.warning(
                        _("Deprecation warning: The setting " + \
                            "kolab_smtp_access_policy.address_search_attrs " + \
                            "is to be replaced with the 'auth_attrs' key in " + \
                            "the 'ldap' or '%s' domain section.") % (domain)
                    )

                auth_search_attrs = conf.get_list(
                        'kolab_smtp_access_policy',
                        'address_search_attrs'
                    )

            else:
                auth_search_attrs = [ 'uid', 'mail' ]
        else:
            auth_search_attrs = [ 'uid', 'mail' ]

        if not 'uid' in auth_search_attrs:
            auth_search_attrs.append('uid')

        auth_search_filter = [ '(|' ]

        for auth_search_attr in auth_search_attrs:
            auth_search_filter.append('(%s=%s)' % (auth_search_attr,login))
            auth_search_filter.append('(%s=%s@%s)' % (auth_search_attr,login,domain))

        auth_search_filter.append(')')

        auth_search_filter = ''.join(auth_search_filter)

        search_filter = "(&%s%s)" % (
                auth_search_filter,
                user_filter
            )

        _results = self._search(
                user_base_dn,
                filterstr=search_filter,
                attrlist=[ 'dn' ],
                override_search='_regular_search'
            )

        if len(_results) == 1:
            (_user_dn, _user_attrs) = _results[0]
        else:
            # Retry to find the user_dn with just uid=%s against the root_dn,
            # if the login is not fully qualified
            if len(login.split('@')) < 2:
                search_filter = "(uid=%s)" % (login)
                _results = self._search(
                        domain,
                        filterstr=search_filter,
                        attrlist=[ 'dn' ]
                    )

                if len(_results) == 1:
                    (_user_dn, _user_attrs) = _results[0]
                else:
                    # Overall fail
                    return False
            else:
                return False

        return _user_dn

    def _find_group(self, attr, value, domain=None, additional_filter=None, base_dn=None):
        self._connect()
        self._bind()

        if domain == None:
            domain = conf.get('kolab', 'primary_domain')

        domain_root_dn = self._kolab_domain_root_dn(domain)

        if conf.has_option(domain, 'group_base_dn'):
            section = domain
        else:
            section = 'ldap'

        if base_dn == None:
            group_base_dn = conf.get_raw(
                    section,
                    'group_base_dn'
                ) % ({'base_dn': domain_root_dn})
        else:
            group_base_dn = base_dn

        if type(attr) == str:
            search_filter = "(%s=%s)" % (
                    attr,
                    value
                )
        elif type(attr) == list:
            search_filter = "(|"
            for _attr in attr:
                search_filter = "%s(%s=%s)" % (search_filter, _attr, value)
            search_filter = "%s)" % (search_filter)

        if additional_filter:
            search_filter = additional_filter % {
                    'search_filter': search_filter
                }

        log.debug(
                _("Attempting to find the group with search filter: %s") % (
                        search_filter
                    ),
                level=8
            )

        _results = self.ldap.search_s(
                group_base_dn,
                scope=ldap.SCOPE_SUBTREE,
                filterstr=search_filter,
                attrlist=[ 'dn' ]
            )

        if len(_results) == 1:
            (_group_dn, _group_attrs) = _results[0]
        else:
            return False

        return _group_dn

    def _find_user(self, attr, value, domain=None, additional_filter=None, base_dn=None):
        self._connect()
        self._bind()

        if domain == None:
            domain = conf.get('kolab', 'primary_domain')

        domain_root_dn = self._kolab_domain_root_dn(domain)

        if conf.has_option(domain, 'user_base_dn'):
            section = domain
        else:
            section = 'ldap'

        if base_dn == None:
            user_base_dn = conf.get_raw(
                    section,
                    'user_base_dn'
                ) % ({'base_dn': domain_root_dn})
        else:
            user_base_dn = base_dn

        if type(attr) == str:
            search_filter = "(%s=%s)" % (
                    attr,
                    value
                )
        elif type(attr) == list:
            search_filter = "(|"
            for _attr in attr:
                search_filter = "%s(%s=%s)" % (search_filter, _attr, value)
            search_filter = "%s)" % (search_filter)

        if additional_filter:
            search_filter = additional_filter % {
                    'search_filter': search_filter
                }

        log.debug(
                _("Attempting to find the user with search filter: %s") % (
                        search_filter
                    ),
                level=8
            )

        _results = self.ldap.search_s(
                user_base_dn,
                scope=ldap.SCOPE_SUBTREE,
                filterstr=search_filter,
                attrlist=[ 'dn' ]
            )

        if len(_results) == 1:
            (_user_dn, _user_attrs) = _results[0]
        else:
            return False

        return _user_dn

    def _search_users(self, attr, value, domain=None, additional_filter=None, base_dn=None):
        self._connect()
        self._bind()

        if domain == None:
            domain = conf.get('kolab', 'primary_domain')

        domain_root_dn = self._kolab_domain_root_dn(domain)

        if conf.has_option(domain, 'user_base_dn'):
            section = domain
        else:
            section = 'ldap'

        if base_dn == None:
            user_base_dn = conf.get_raw(
                    section,
                    'user_base_dn'
                ) % ({'base_dn': domain_root_dn})
        else:
            user_base_dn = base_dn

        if type(attr) == str:
            search_filter = "(%s=%s)" % (
                    attr,
                    value
                )
        elif type(attr) == list:
            search_filter = "(|"
            for _attr in attr:
                search_filter = "%s(%s=%s)" % (search_filter, _attr, value)
            search_filter = "%s)" % (search_filter)

        if additional_filter:
            search_filter = additional_filter % {
                    'search_filter': search_filter
                }

        log.debug(
                _("Attempting to find entries with search filter: %s") % (
                        search_filter
                    ),
                level=8
            )

        _results = self.ldap.search_s(
                user_base_dn,
                scope=ldap.SCOPE_SUBTREE,
                filterstr=search_filter,
                attrlist=[ 'dn' ]
            )

        _user_dns = []

        for _result in _results:
            (_user_dn, _user_attrs) = _result
            _user_dns.append(_user_dn)

        return _user_dns

    def _persistent_search(self,
            base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr="(objectClass=*)",
            attrlist=None,
            attrsonly=0,
            timeout=-1,
            callback=False,
            primary_domain=None,
            secondary_domains=[]
        ):
        _results = []

        psearch_server_controls = []

        psearch_server_controls.append(psearch.PersistentSearchControl(
                    criticality=True,
                    changeTypes=[ 'add', 'delete', 'modify', 'modDN' ],
                    changesOnly=False,
                    returnECs=True
                )
            )

        _search = self.ldap.search_ext(
                base_dn,
                scope=scope,
                filterstr=filterstr,
                attrlist=attrlist,
                attrsonly=attrsonly,
                timeout=timeout,
                serverctrls=psearch_server_controls
            )

        ecnc = psearch.EntryChangeNotificationControl

        while True:
            res_type,res_data,res_msgid,_None,_None,_None = self.ldap.result4(
                    _search,
                    all=0,
                    add_ctrls=1,
                    add_intermediates=1,
                    resp_ctrl_classes={ecnc.controlType:ecnc}
                )

            change_type = None
            previous_dn = None
            change_number = None

            for dn,entry,srv_ctrls in res_data:
                log.debug(_("LDAP Search Result Data Entry:"), level=8)
                log.debug("    DN: %r" % (dn), level=8)
                log.debug("    Entry: %r" % (entry), level=8)

                ecn_ctrls = [
                        c for c in srv_ctrls
                        if c.controlType == ecnc.controlType
                    ]

                if ecn_ctrls:
                    change_type = ecn_ctrls[0].changeType
                    previous_dn = ecn_ctrls[0].previousDN
                    change_number = ecn_ctrls[0].changeNumber
                    change_type_desc = psearch.CHANGE_TYPES_STR[change_type]

                    log.debug(
                            _("Entry Change Notification attributes:"),
                            level=8
                        )

                    log.debug(
                            "    " + _("Change Type: %r (%r)") % (
                                    change_type,
                                    change_type_desc
                                ),
                            level=8
                        )

                    log.debug(
                            "    " + _("Previous DN: %r") % (previous_dn),
                            level=8
                        )

                if callback:
                    callback(
                            dn=dn,
                            entry=entry,
                            previous_dn=previous_dn,
                            change_type=change_type,
                            change_number=change_number,
                            primary_domain=primary_domain,
                            secondary_domains=secondary_domains
                        )

    def _paged_search(self,
            base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr="(objectClass=*)",
            attrlist=None,
            attrsonly=0,
            timeout=-1,
            callback=False,
            primary_domain=None,
            secondary_domains=[]
        ):

        page_size = 500
        critical = True
        _results = []

        server_page_control = SimplePagedResultsControl(page_size=page_size)

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
            try:
                (
                        _result_type,
                        _result_data,
                        _result_msgid,
                        _result_controls
                    ) = self.ldap.result3(_search)

            except ldap.NO_SUCH_OBJECT, e:
                log.warning(_("Object %s searched no longer exists") % (base_dn))
                break

            if callback:
                callback(
                        user=_result_data,
                        primary_domain=primary_domain,
                        secondary_domains=secondary_domains
                    )

            _results.extend(_result_data)
            if (pages % 2) == 0:
                log.debug(_("%d results...") % (len(_results)))

            pctrls = [
                    c for c in _result_controls
                        if c.controlType == LDAP_CONTROL_PAGED_RESULTS
                ]

            if pctrls:
                size = pctrls[0].size
                cookie = pctrls[0].cookie
                if cookie:
                    server_page_control.cookie = cookie
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

    def _vlv_search(self,
            base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr="(objectClass=*)",
            attrlist=None,
            attrsonly=0,
            timeout=-1,
            callback=False,
            primary_domain=None,
            secondary_domains=[]
        ):
        pass

    def _sync_repl(self,
            base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr="(objectClass=*)",
            attrlist=None,
            attrsonly=0,
            timeout=-1,
            callback=False,
            primary_domain=None,
            secondary_domains=[]
        ):

        import syncrepl

        ldap_sync_conn = syncrepl.DNSync(
                '/var/lib/pykolab/syncrepl.db',
                ldap_url.initializeUrl(),
                trace_level=ldapmodule_trace_level,
                trace_file=ldapmodule_trace_file
            )

        msgid = ldap_sync_conn.syncrepl_search(
                base_dn,
                scope,
                mode='refreshAndPersist',
                filterstr=filterstr
            )

        try:
            # Here's where returns need to be taken into account...
            while ldap_sync_conn.syncrepl_poll(all=1, msgid=msgid):
                pass
        except KeyboardInterrupt:
            pass

    def _regular_search(self,
            base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr="(objectClass=*)",
            attrlist=None,
            attrsonly=0,
            timeout=-1,
            callback=False,
            primary_domain=None,
            secondary_domains=[]
        ):
        self._connect()
        self._bind()

        _search = self.ldap.search(
                base_dn,
                scope=scope,
                filterstr=filterstr,
                attrlist=attrlist,
                attrsonly=attrsonly
            )

        _results = []
        _result_type = None

        while not _result_type == ldap.RES_SEARCH_RESULT:
            (_result_type, _result) = self.ldap.result(_search, False, 0)

            if not _result == None:
                for result in _result:
                    _results.append(result)

        return _results

    def _search(self,
            base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr="(objectClass=*)",
            attrlist=None,
            attrsonly=0,
            timeout=-1,
            override_search=False,
            callback=False,
            primary_domain=None,
            secondary_domains=[]
        ):
        """
            Search LDAP.

            Use the priority ordered SUPPORTED_LDAP_CONTROLS and use
            the first one supported.
        """

        if len(self.ldap.supported_controls) < 1:
            for control_num in SUPPORTED_LDAP_CONTROLS.keys():
                log.debug(
                        _("Checking for support for %s") % (
                                SUPPORTED_LDAP_CONTROLS[control_num]['desc']
                            ),
                        level=8
                    )

            _search = self.ldap.search_s(
                    '',
                    scope=ldap.SCOPE_BASE,
                    attrlist=['supportedControl']
                )

            for (_result,_supported_controls) in _search:
                supported_controls = _supported_controls.values()[0]
                for control_num in SUPPORTED_LDAP_CONTROLS.keys():
                    if SUPPORTED_LDAP_CONTROLS[control_num]['oid'] in \
                            supported_controls:

                        self.ldap.supported_controls.append(
                                SUPPORTED_LDAP_CONTROLS[control_num]['func']
                            )

        _results = []

        if not override_search == False:
            _use_ldap_controls = [ override_search ]
        else:
            _use_ldap_controls = self.ldap.supported_controls

        for supported_control in _use_ldap_controls:
            exec("""_results = self.%s(
                    %r,
                    scope=%r,
                    filterstr=%r,
                    attrlist=%r,
                    attrsonly=%r,
                    timeout=%r,
                    callback=callback,
                    primary_domain=%r,
                    secondary_domains=%r
                )""" % (
                        supported_control,
                        base_dn,
                        scope,
                        filterstr,
                        attrlist,
                        attrsonly,
                        timeout,
                        primary_domain,
                        secondary_domains
                    )
                )

        return _results

    def _result(self, msgid=ldap.RES_ANY, all=1, timeout=-1):
        return self.ldap.result(msgid, all, timeout)

    def _domain_default_quota(self, domain):
        if conf.has_option(domain, 'default_quota'):
            return conf.get(domain, 'default_quota', quiet=True)
        elif conf.has_option('ldap', 'default_quota'):
            return conf.get('ldap', 'default_quota', quiet=True)
        elif conf.has_option('kolab', 'default_quota'):
            return conf.get('kolab', 'default_quota', quiet=True)

    def _domain_section(self, domain):
        if conf.has_section(domain):
            return domain
        else:
            return 'ldap'

    def _get_group_attribute(self, group, attribute):
        self._bind()

        attribute = attribute.lower()

        log.debug(
                _("Getting attribute %s for group %s") % (attribute,user),
                level=8
            )

        _result_type = None

        _search = self.ldap.search_ext(
                group['dn'],
                ldap.SCOPE_BASE,
                '(objectclass=*)',
                [ 'dn', attribute ]
            )

        (
                _result_type,
                _result_data,
                _result_msgid,
                _result_controls
            ) = self.ldap.result3(_search)

        if len(_result_data) >= 1:
            (group_dn, group_attrs) = _result_data[0]
        else:
            log.warning(_("Could not get attribute %s for group %s")
                % (attribute,user['dn']))

            return None

        group_attrs = utils.normalize(group_attrs)

        if not group_attrs.has_key(attribute):
            log.debug(
                    _("Wanted attribute %s, which does not exist for group " + \
                    "%r") % (
                            attribute,
                            group_dn
                        ),
                    level=8
                )

            group_attrs[attribute] = None

        return group_attrs[attribute]

    def _get_user_attribute(self, user, attribute):
        self._bind()

        attribute = attribute.lower()

        log.debug(
                _("Getting attribute %s for user %s") % (attribute,user),
                level=8
            )

        _result_type = None

        _search = self.ldap.search_ext(
                user['dn'],
                ldap.SCOPE_BASE,
                '(objectclass=*)',
                [ 'dn', attribute ]
            )

        (
                _result_type,
                _result_data,
                _result_msgid,
                _result_controls
            ) = self.ldap.result3(_search)

        if len(_result_data) >= 1:
            (user_dn, user_attrs) = _result_data[0]
        else:
            log.warning(_("Could not get attribute %s for user %s")
                % (attribute,user['dn']))

            return None

        user_attrs = utils.normalize(user_attrs)

        if not user_attrs.has_key(attribute):
            log.debug(
                    _("Wanted attribute %s, which does not exist for user " + \
                    "%r") % (
                            attribute,
                            user_dn
                        ),
                    level=8
                )

            user_attrs[attribute] = None

        return user_attrs[attribute]

    def _get_user_attributes(self, user, attributes):
        _user_attrs = {}

        for attribute in attributes:
            _user_attrs[attribute] = self._get_user_attribute(user, attribute)

        return _user_attrs

    def _search_mail_address(self, domain, mail_address):
        self._bind()

        domain_root_dn = self._kolab_domain_root_dn(domain)

        return self._search(
                domain_root_dn,
                ldap.SCOPE_SUBTREE,
                # TODO: Configurable
                '(|(mail=%s)(mailalternateaddress=%s))' % (
                        mail_address,
                        mail_address
                    ),
                [ 'mail', 'mailalternateaddress' ],
                override_search='_regular_search'
            )

    def _set_user_attribute(self, user, attribute, value):
        self._bind()

        if isinstance(user, basestring):
            user = { "dn": user }

        attribute = attribute.lower()

        if not user.has_key(attribute):
            user[attribute] = self._get_user_attribute(user, attribute)

        mode = None

        # TODO: This should be a schema check!
        if attribute in [ 'mailquota', 'mailalternateaddress' ]:
            if not user.has_key('objectclass'):
                user['objectclass'] = self._get_user_attribute(
                        user,
                        'objectclass'
                    )

                if user['objectclass'] == None:
                    return

            if not 'mailrecipient' in user['objectclass']:
                user['objectclass'].append('mailrecipient')
                self._set_user_attribute(
                        user,
                        'objectclass',
                        user['objectclass']
                    )

        if user.has_key(attribute) and not user[attribute] == None:
            mode = ldap.MOD_REPLACE
        else:
            mode = ldap.MOD_ADD

        try:
            if isinstance(value, int):
                value = (str)(value)

            self.ldap.modify(user['dn'], [(mode, attribute, value)])
        except ldap.LDAPError, e:
            log.warning(
                    _("LDAP modification of attribute %s for %s to value " + \
                    "%s failed: %r") % (attribute,user_dn,value,e.message['info'])
                )

    def _list_domains(self):
        """
            Find the domains related to this Kolab setup, and return a list of
            DNS domain names.

            Returns a list of tuples, each tuple containing the primary domain
            name and a list of secondary domain names.
        """

        log.debug(_("Listing domains..."), level=8)

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
                [ 'associateddomain' ],
                override_search='_regular_search'
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

        log.debug(_("Finding domain root dn for domain %s") % (domain), level=8)

        bind_dn = conf.get('ldap', 'bind_dn')
        bind_pw = conf.get('ldap', 'bind_pw')

        domain_base_dn = conf.get('ldap', 'domain_base_dn', quiet=True)

        if not domain_base_dn == "":

            # If we haven't returned already, let's continue searching
            domain_name_attribute = conf.get('ldap', 'domain_name_attribute')

            _results = self._search(
                    domain_base_dn,
                    ldap.SCOPE_SUBTREE,
                    "(%s=%s)" % (domain_name_attribute,domain),
                    override_search='_regular_search'
                )

            domains = []
            for _domain in _results:
                (domain_dn, _domain_attrs) = _domain
                domain_rootdn_attribute = conf.get(
                        'ldap',
                        'domain_rootdn_attribute'
                    )
                _domain_attrs = utils.normalize(_domain_attrs)
                if _domain_attrs.has_key(domain_rootdn_attribute):
                    return _domain_attrs[domain_rootdn_attribute]

        else:
            if conf.has_option('ldap', 'base_dn'):
                return conf.get('ldap', 'base_dn')

        return utils.standard_root_dn(domain)

    def _list_users(self, primary_domain, secondary_domains=[], callback=None):

        # Track state for psearch and paged searches.
        self._initial_sync_done = False

        log.info(_("Listing users for domain %s (and %s)")
            % (primary_domain, ', '.join(secondary_domains)))

        self._bind()

        # TODO: Bind with read-only credentials, perhaps even domain-specific
        bind_dn = conf.get('ldap', 'bind_dn')
        #bind_dn = conf.get('ldap', 'ro_bind_dn')
        bind_pw = conf.get('ldap', 'bind_pw')
        #bind_pw = conf.get('ldap', 'ro_bind_pw')

        if conf.has_option(primary_domain, 'user_base_dn'):
            section = primary_domain
        else:
            section = 'ldap'

        domain_root_dn = self._kolab_domain_root_dn(primary_domain)

        user_base_dn = conf.get_raw(
                section,
                'user_base_dn'
            ) % ({'base_dn': domain_root_dn})

        if conf.has_option(primary_domain, 'kolab_user_filter'):
            section = primary_domain
        else:
            section = 'ldap'

        kolab_user_filter = conf.get(section, 'kolab_user_filter', quiet=True)

        if conf.has_option(primary_domain, 'kolab_user_scope'):
            section = primary_domain
        else:
            section = 'ldap'

        _kolab_user_scope = conf.get(section, 'kolab_user_scope', quiet=True)

        if LDAP_SCOPE.has_key(_kolab_user_scope):
            kolab_user_scope = LDAP_SCOPE[_kolab_user_scope]
        else:
            log.warning(
                    _("LDAP Search scope %s not found, using 'sub'") % (
                            _kolab_user_scope
                        )
                )

            kolab_user_scope = ldap.SCOPE_SUBTREE

        # TODO: Is, perhaps, a domain specific setting
        result_attribute = conf.get(
                'cyrus-sasl',
                'result_attribute',
                quiet=True
            )

        try:
            self.ldap.simple_bind_s(bind_dn, bind_pw)
        except ldap.SERVER_DOWN, e:
            error = eval("%s" % (e))
            log.error(_("Error binding to LDAP: %s") % (error['desc']))
            # TODO: Exit the fork (if fork!)
            return

        # TODO: The quota and alternative address attributes are actually
        # supposed to be settings.
        _search = self._search(
                user_base_dn,
                kolab_user_scope,
                kolab_user_filter,
                attrlist=[
                        'dn',
                        result_attribute,
                        'sn',
                        'givenname',
                        'cn',
                        'uid'
                    ],
                attrsonly=0,
                callback=callback,
                primary_domain=primary_domain,
                secondary_domains=secondary_domains
            )

        if callback == None:
            log.info(_("Found %d users") % (len(_search)))

            log.debug(_("Iterating over %d users, making sure we have the " + \
                "necessary attributes...") % (len(_search)), level=6)

            users = []

            num_users = len(_search)
            num_user = 0

            for user_dn, user_attrs in _search:
                num_user += 1

                # Placeholder for the user attributes
                user = user_attrs
                user['dn'] = user_dn

                user = self._get_user_details(
                        user,
                        primary_domain,
                        secondary_domains
                    )

                if user:
                    users.append(user)

                if (num_user % 1000) == 0:
                    log.debug(
                            _("Done iterating over user %d of %d")
                                % (num_user,num_users),
                            level=3
                        )

            return users

    def _get_user_details(self, user, primary_domain, secondary_domains=[]):

        # TODO: Is, perhaps, a domain specific setting
        result_attribute = conf.get(
                'cyrus-sasl',
                'result_attribute',
                quiet=True
            )

        if not user.has_key('standard_domain'):
            user['standard_domain'] = (primary_domain, secondary_domains)

        user = utils.normalize(user)

        _get_attrs = []
        _wanted_attributes = [
                result_attribute,
                'mail',
                'mailalternateaddress',
                'sn',
                'givenname',
                'cn',
                'uid',
                'preferredLanguage'
            ]

        for attribute in _wanted_attributes:
            if not user.has_key(attribute):
                _get_attrs.append(attribute)
                #user[attribute] = self._get_user_attribute(user, attribute)

        if len(_get_attrs) > 0:
            _user_attrs = self._get_user_attributes(user, _get_attrs)
            for key in _user_attrs.keys():
                user[key] = _user_attrs[key]

        user = utils.normalize(user)

        if not user.has_key('preferredlanguage') or user['preferredlanguage'] == None:
            if conf.has_option(primary_domain, 'default_locale'):
                default_locale = conf.get(primary_domain, 'default_locale')
            else:
                default_locale = conf.get('kolab','default_locale')

            self._set_user_attribute(user, 'preferredlanguage', default_locale)
            user['preferredlanguage'] = default_locale

        # Check to see if we want to apply a primary mail recipient policy
        if conf.has_option(primary_domain, 'primary_mail'):
            primary_mail = conf.plugins.exec_hook(
                    "set_primary_mail",
                    kw={
                            'primary_mail':
                                conf.get_raw(
                                        primary_domain,
                                        'primary_mail'
                                    ),
                            'user_attrs': user,
                            'primary_domain': primary_domain,
                            'secondary_domains': secondary_domains
                        }
                )

            i = 1
            _primary_mail = primary_mail

            done = False
            while not done:
                results = self._search_mail_address(
                        primary_domain,
                        _primary_mail
                    )

                # Length of results should be 0 (no entry found)
                # or 1 (which should be the entry we're looking at here)
                if len(results) == 0:
                    log.debug(
                            _("No results for mail address %s found") % (
                                    _primary_mail
                                ),
                            level=8
                        )

                    done = True
                    continue

                if len(results) == 1:
                    log.debug(
                            _("1 result for address %s found, verifying") % (
                                    _primary_mail
                                ),
                            level=8
                        )

                    almost_done = True
                    for result in results:
                        if not result[0] == user['dn']:
                            log.debug(
                                    _("Too bad, primary email address %s " + \
                                    "already in use for %s (we are %s)") % (
                                            _primary_mail,
                                            result[0],
                                            user['dn']
                                        ),
                                    level=8
                                )

                            almost_done = False

                    if almost_done:
                        done = True
                        continue

                i += 1
                _primary_mail = "%s%d@%s" % (
                        primary_mail.split('@')[0],
                        i,
                        primary_mail.split('@')[1]
                    )

            primary_mail = _primary_mail

            if not primary_mail == None:
                if not user.has_key('mail'):
                    self._set_user_attribute(user, 'mail', primary_mail)
                    user['mail'] = primary_mail
                else:
                    if not primary_mail == user['mail']:
                        self._set_user_attribute(user, 'mail', primary_mail)

                        if not user['mail'] == None:
                            user['old_mail'] = user['mail']

                        user['mail'] = primary_mail

            # Check to see if we want to apply a secondary mail recipient
            # policy.
            section = None

            if conf.has_option(primary_domain, 'secondary_mail'):
                section = primary_domain
            elif conf.has_option('kolab', 'secondary_mail'):
                section = 'kolab'

            if not section == None:
                # Execute the plugin hook
                suggested_secondary_mail = conf.plugins.exec_hook(
                        "set_secondary_mail",
                        kw={
                                'secondary_mail':
                                    conf.get_raw(
                                            primary_domain,
                                            'secondary_mail'
                                        ),
                                'user_attrs': user,
                                'primary_domain': primary_domain,
                                'secondary_domains': secondary_domains
                            }
                    ) # end of conf.plugins.exec_hook() call

                secondary_mail = []

                for _secondary_mail in suggested_secondary_mail:
                    i = 1
                    __secondary_mail = _secondary_mail

                    done = False
                    while not done:
                        results = self._search_mail_address(
                                primary_domain,
                                __secondary_mail
                            )

                        # Length of results should be 0 (no entry found)
                        # or 1 (which should be the entry we're looking at here)
                        if len(results) == 0:
                            log.debug(
                                    _("No results for address %s found") % (
                                            __secondary_mail
                                        ),
                                    level=8
                                )

                            done = True
                            continue

                        if len(results) == 1:
                            log.debug(
                                    _("1 result for address %s found, " + \
                                    "verifying...") % (
                                            __secondary_mail
                                        ),
                                    level=8
                                )

                            almost_done = True
                            for result in results:
                                if not result[0] == user['dn']:
                                    log.debug(
                                            _("Too bad, secondary email " + \
                                            "address %s already in use for " + \
                                            "%s (we are %s)") % (
                                                    __secondary_mail,
                                                    result[0],
                                                    user['dn']
                                                ),
                                            level=8
                                        )

                                    almost_done = False

                            if almost_done:
                                done = True
                                continue

                        i += 1
                        __secondary_mail = "%s%d@%s" % (
                                _secondary_mail.split('@')[0],
                                i,
                                _secondary_mail.split('@')[1]
                            )

                    secondary_mail.append(__secondary_mail)

                if not secondary_mail == None:
                    secondary_mail = list(set(secondary_mail))
                    # Avoid duplicates
                    while primary_mail in secondary_mail:
                        secondary_mail.pop(secondary_mail.index(primary_mail))

                    if not user.has_key('mailalternateaddress'):
                        if not len(secondary_mail) == 0:
                            self._set_user_attribute(
                                    user,
                                    'mailalternateaddress',
                                    secondary_mail
                                )

                            user['mailalternateaddress'] = secondary_mail
                    else:
                        if not secondary_mail == user['mailalternateaddress']:
                            self._set_user_attribute(
                                    user,
                                    'mailalternateaddress',
                                    secondary_mail
                                )

                            user['mailalternateaddress'] = secondary_mail

        return user

    def sync_user(self, *args, **kw):
        # See if kw['dn'] has been set.

        if kw.has_key('dn'):
            self.sync_ldap_user(*args, **kw)
        elif kw.has_key('user'):
            for user_dn, user_attrs in kw['user']:
                _user = utils.normalize(user_attrs)
                _user['dn'] = user_dn
                kw['user'] = _user
                self.sync_ldap_user(*args, **kw)
        else:
            # TODO: Not yet implemented
            pass

    def sync_ldap_user(self, *args, **kw):
        user = None

        done = False

        if kw.has_key('change_type'):
            # This is a EntryChangeControl notification
            user = utils.normalize(kw['entry'])
            user['dn'] = kw['dn']

            if kw['change_type'] == None:
                # This user has not been changed, but existed already.
                user = self._get_user_details(
                        user,
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                pykolab.imap.synchronize(
                        users=[user],
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                done = True

            elif kw['change_type'] == 1:
                user = self._get_user_details(
                        user,
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                pykolab.imap.synchronize(
                        users=[user],
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                done = True

            elif kw['change_type'] == 4:
                # TODO: How do we know what has changed?
                user = self._get_user_details(
                        user,
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                pykolab.imap.synchronize(
                        users=[user],
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                done = True

            elif kw['change_type'] == 2:
                # TODO: Use Cyrus SASL authorization ID
                folder = 'user/%s' % (user['mail'].lower())
                # TODO: Verify if folder exists
                pykolab.imap.delete_mailfolder(folder)
                done = True

            elif kw['change_type'] == 8:
                # Object has had its rdn changed
                user = self._get_user_details(
                        user,
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                pykolab.imap.synchronize(
                        users=[user],
                        primary_domain=kw['primary_domain'],
                        secondary_domains=kw['secondary_domains']
                    )

                done = True

        if kw.has_key('user'):
            user = kw['user']

        if user and not done:
            pykolab.imap.synchronize(
                    users=[user],
                    primary_domain=kw['primary_domain'],
                    secondary_domains=kw['secondary_domains']
                )
