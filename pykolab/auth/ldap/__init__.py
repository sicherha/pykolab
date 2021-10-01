# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# pylint: disable=too-many-lines

from __future__ import print_function

import datetime
# Catch python-ldap-2.4 changes
from distutils import version
import logging
import time
import traceback

import ldap
import ldap.controls
try:
    from ldap.controls import psearch
except ImportError:
    pass

from ldap.dn import explode_dn

import ldap.filter

from six import string_types
import _ldap

import pykolab

from pykolab import utils
from pykolab.base import Base
from pykolab.constants import SUPPORTED_LDAP_CONTROLS
from pykolab.errors import *
from pykolab.translate import _ as _l

import auth_cache
import cache

# pylint: disable=invalid-name
log = pykolab.getLogger('pykolab.auth')
conf = pykolab.getConf()


class LDAP(Base):
    """
        Abstraction layer for the LDAP authentication / authorization backend,
        for use with Kolab.
    """

    def __init__(self, domain=None):
        """
            Initialize the LDAP object for domain. If no domain is specified,
            domain name space configured as 'kolab'.'primary_domain' is used.
        """
        Base.__init__(self, domain=domain)

        self.ldap = None
        self.ldap_priv = None
        self.bind = None

        if domain is None:
            self.domain = conf.get('kolab', 'primary_domain')
        else:
            self.domain = domain

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-statements
    def authenticate(self, login, realm):
        """
            Find the entry corresponding to login, and attempt a bind.

            login is a tuple with 4 values. In order of appearance;

            [0] - the login username.

            [1] - the password

            [2] - the service (optional)

            [3] - the realm

            Called from pykolab.auth.Auth, the realm parameter is derived, while
            login[3] preserves the originally specified realm.
        """

        try:
            log.debug(
                _l("Attempting to authenticate user %s in realm %s") % (
                    login[0],
                    realm
                ),
                level=8
            )

        except Exception:
            pass

        self.connect(immediate=True)
        self._bind()

        # See if we know a base_dn for the domain
        base_dn = None

        try:
            base_dn = auth_cache.get_entry(self.domain)
        except Exception as errmsg:
            log.error(_l("Authentication cache failed: %r") % (errmsg))

        if base_dn is None:
            config_base_dn = self.config_get('base_dn')
            ldap_base_dn = self._kolab_domain_root_dn(self.domain)

            if ldap_base_dn is not None and not ldap_base_dn == config_base_dn:
                base_dn = ldap_base_dn
            else:
                base_dn = config_base_dn

            try:
                auth_cache.set_entry(self.domain, base_dn)
            except Exception as errmsg:
                log.error(_l("Authentication cache failed: %r") % (errmsg))

        try:
            user_filter = self.config_get_raw('user_filter') % (
                {'base_dn': base_dn}
            )

        except TypeError:
            user_filter = self.config_get_raw('user_filter')

        _filter = '(&(|'

        auth_attrs = self.config_get_list('auth_attributes')

        for attr in auth_attrs:
            _filter += "(%s=%s)" % (attr, login[0])
            _filter += "(%s=%s@%s)" % (attr, login[0], realm)

        _filter += ')%s)' % (user_filter)

        entry_dn = None

        # Attempt to obtain an entry_dn from cache.
        try:
            entry_dn = auth_cache.get_entry(_filter)
        except Exception as errmsg:
            log.error(_l("Authentication cache failed: %r") % (errmsg))

        retval = False
        timeout = float(self.config_get('ldap', 'timeout', default=10))

        if entry_dn is None:
            _search = self.ldap.search_ext(
                base_dn,
                ldap.SCOPE_SUBTREE,
                filterstr=_filter,
                attrlist=['entrydn'],
                attrsonly=True,
                timeout=timeout
            )

            try:
                (
                    _result_type,
                    _result_data,
                    _result_msgid,
                    _result_controls
                ) = self.ldap.result3(_search)

            except ldap.INVALID_CREDENTIALS:
                log.error(
                    _l("Invalid DN, username and/or password for '%s'.") % (
                        _filter
                    )
                )

                return False

            except ldap.NO_SUCH_OBJECT:
                log.error(
                    _l("Invalid DN, username and/or password for '%s'.") % (
                        _filter
                    )
                )

                return False

            except ldap.SERVER_DOWN as errmsg:
                log.error(_l("LDAP server unavailable: %r") % (errmsg))
                log.error(traceback.format_exc())
                self._disconnect()

                return False

            except ldap.TIMEOUT:
                log.error(_l("LDAP timeout."))
                self._disconnect()

                return False

            except Exception as errmsg:
                log.error(_l("Exception occurred: %r") % (errmsg))
                log.error(traceback.format_exc())
                self._disconnect()

                return False

            log.debug(
                _l("Length of entries found: %r") % (
                    len(_result_data)
                ),
                level=8
            )

            # Remove referrals
            _result_data = [_e for _e in _result_data if _e[0] is not None]

            if len(_result_data) == 1:
                (entry_dn, _) = _result_data[0]

            elif len(_result_data) > 1:
                try:
                    log.info(
                        _l("Authentication for %r failed (multiple entries)") % (
                            login[0]
                        )
                    )

                except Exception:
                    pass

                self._disconnect()
                return False

            else:
                try:
                    log.info(
                        _l("Authentication for %r failed (no entry)") % (
                            login[0]
                        )
                    )

                except Exception:
                    pass

                self._disconnect()
                return False

            if entry_dn is None:
                try:
                    log.info(
                        _l("Authentication for %r failed (LDAP error?)") % (
                            login[0]
                        )
                    )

                except Exception:
                    pass

                self._disconnect()
                return False

            try:
                # Needs to be synchronous or succeeds and continues setting
                # retval to True!!
                retval = self._bind(entry_dn, login[1])

                if retval:
                    try:
                        log.info(
                            _l("Authentication for %r succeeded") % (
                                login[0]
                            )
                        )

                    except Exception:
                        pass

                else:
                    try:
                        log.info(
                            _l("Authentication for %r failed (error)") % (
                                login[0]
                            )
                        )

                    except Exception:
                        pass

                    self._disconnect()
                    return False

                try:
                    auth_cache.set_entry(_filter, entry_dn)
                except Exception as errmsg:
                    log.error(_l("Authentication cache failed: %r") % (errmsg))

            except ldap.SERVER_DOWN:
                log.error(_l("Authentication failed, LDAP server unavailable"))
                self._disconnect()

                return False

            except Exception:
                try:
                    log.debug(
                        _l("Failed to authenticate as user %r") % (
                            login[0]
                        ),
                        level=8
                    )

                except Exception:
                    pass

                self._disconnect()
                return False

        else:
            try:
                # Needs to be synchronous or succeeds and continues setting
                # retval to True!!
                retval = self._bind(entry_dn, login[1])

                if retval:
                    log.info(_l("Authentication for %r succeeded") % (login[0]))
                else:
                    log.info(
                        _l("Authentication for %r failed (password)") % (
                            login[0]
                        )
                    )

                    self._disconnect()
                    return False

            except ldap.NO_SUCH_OBJECT as errmsg:
                log.debug(
                    _l("Error occured, there is no such object: %r") % (
                        errmsg
                    ),
                    level=8
                )

                self.bind = None

                try:
                    auth_cache.del_entry(_filter)

                except Exception:
                    log.error(_l("Authentication cache failed to clear entry"))

                retval = self.authenticate(login, realm)

            except Exception as errmsg:
                log.debug(_l("Exception occured: %r") % (errmsg))

                try:
                    log.debug(
                        _l("Failed to authenticate as user %r") % (
                            login[0]
                        ),
                        level=8
                    )

                except Exception:
                    pass

                self._disconnect()
                return False

        self._disconnect()

        return retval

    def connect(self, priv=None, immediate=False):
        """
            Connect to the LDAP server through the uri configured.
        """
        # Already connected
        if priv is None and self.ldap is not None:
            return

        # Already connected
        if priv is not None and self.ldap_priv is not None:
            return

        log.debug(_l("Connecting to LDAP..."), level=8)

        uri = self.config_get('ldap_uri')

        log.debug(_l("Attempting to use LDAP URI %s") % (uri), level=8)

        trace_level = 0

        if conf.debuglevel > 8:
            trace_level = 1

        if immediate:
            retry_max = 1
            retry_delay = 1.0
        else:
            retry_max = 200
            retry_delay = 3.0

        conn = ldap.ldapobject.ReconnectLDAPObject(
            uri,
            trace_level=trace_level,
            trace_file=pykolab.logger.StderrToLogger(log),
            retry_max=retry_max,
            retry_delay=retry_delay
        )

        if immediate:
            conn.set_option(ldap.OPT_TIMEOUT, 10)

        conn.protocol_version = 3
        conn.supported_controls = []

        if priv is None:
            self.ldap = conn
        else:
            self.ldap_priv = conn

    def entry_dn(self, entry_id):
        """
            Get a entry's distinguished name for an entry ID.

            The entry ID may be any of:

            - an entry's value for the configured unique_attribute,
            - a (syntactically valid) Distinguished Name,
            - a dictionary such as previously returned as (part of) the result
              of a search.
        """
        entry_dn = None

        if self._entry_dn(entry_id):
            return entry_id

        if self._entry_dict(entry_id):
            return entry_id['dn']

        unique_attribute = self.config_get('unique_attribute')
        config_base_dn = self.config_get('base_dn')
        ldap_base_dn = self._kolab_domain_root_dn(self.domain)

        if ldap_base_dn is not None and not ldap_base_dn == config_base_dn:
            base_dn = ldap_base_dn
        else:
            base_dn = config_base_dn

        _filter = "(%s=%s)" % (unique_attribute, ldap.filter.escape_filter_chars(entry_id))

        _search = self.ldap.search_ext(
            base_dn,
            ldap.SCOPE_SUBTREE,
            _filter,
            ['entrydn']
        )

        (
            _result_type,
            _result_data,
            _result_msgid,
            _result_controls
        ) = self.ldap.result3(_search)

        if len(_result_data) >= 1:
            (entry_dn, _) = _result_data[0]

        return entry_dn

    def get_entry_attribute(self, entry_id, attribute):
        """
            Get an attribute for an entry.

            Return the attribute value if successful, or None if not.
        """

        entry_attrs = self.get_entry_attributes(entry_id, [attribute])

        if attribute in entry_attrs:
            return entry_attrs[attribute]

        if attribute.lower() in entry_attrs:
            return entry_attrs[attribute.lower()]

        return None

    def get_entry_attributes(self, entry_id, attributes):
        """
            Get multiple attributes for an entry.
        """

        self._bind()

        log.debug(_l("Entry ID: %r") % (entry_id), level=8)
        entry_dn = self.entry_dn(entry_id)
        log.debug(_l("Entry DN: %r") % (entry_dn), level=8)

        log.debug(
            _l("ldap search: (%r, %r, filterstr='(objectclass=*)', attrlist=[ 'dn' ] + %r") % (
                entry_dn,
                ldap.SCOPE_BASE,
                attributes
            ),
            level=8
        )

        _search = self.ldap.search_ext(
            entry_dn,
            ldap.SCOPE_BASE,
            filterstr='(objectclass=*)',
            attrlist=['dn'] + attributes
        )

        (
            _result_type,
            _result_data,
            _result_msgid,
            _result_controls
        ) = self.ldap.result3(_search)

        if len(_result_data) >= 1:
            (_entry_dn, _entry_attrs) = _result_data[0]
        else:
            return None

        return utils.normalize(_entry_attrs)

    def list_recipient_addresses(self, entry_id):
        """
            Give a list of all valid recipient addresses for an LDAP entry
            identified by its ID.
        """
        mail_attributes = conf.get_list('ldap', 'mail_attributes')
        entry = self.get_entry_attributes(entry_id, mail_attributes)

        return self.extract_recipient_addresses(entry) if entry is not None else []

    # pylint: disable=no-self-use
    def extract_recipient_addresses(self, entry):
        """
            Extact a list of all valid recipient addresses for the given LDAP entry.
            This includes all attributes configured for ldap.mail_attributes
        """
        recipient_addresses = []
        mail_attributes = conf.get_list('ldap', 'mail_attributes')

        for attr in mail_attributes:
            if attr in entry:
                if isinstance(entry[attr], list):
                    recipient_addresses.extend(entry[attr])
                elif isinstance(entry[attr], string_types):
                    recipient_addresses.append(entry[attr])

        return recipient_addresses

    def list_delegators(self, entry_id):
        """
            Get a list of user records the given user is set to be a delegatee
        """
        delegators = []

        mailbox_attribute = conf.get('cyrus-sasl', 'result_attribute')
        if mailbox_attribute is None:
            mailbox_attribute = 'mail'

        for __delegator in self.search_entry_by_attribute('kolabDelegate', entry_id):
            (_dn, _delegator) = __delegator
            _delegator['dn'] = _dn

            if mailbox_attribute in _delegator:
                _delegator['_mailbox_basename'] = _delegator[mailbox_attribute]
            else:
                _delegator['_mailbox_basename'] = None

            if isinstance(_delegator['_mailbox_basename'], list):
                _delegator['_mailbox_basename'] = _delegator['_mailbox_basename'][0]
            delegators.append(_delegator)

        return delegators

    def find_folder_resource(self, folder="*", exclude_entry_id=None):
        """
            Given a shared folder name or list of folder names, find one or more valid
            resources.

            Specify an additional entry_id to exclude to exclude matches.
        """

        self._bind()

        if exclude_entry_id is not None:
            __filter_prefix = "(&"
            __filter_suffix = "(!(%s=%s)))" % (
                self.config_get('unique_attribute'),
                exclude_entry_id
            )
        else:
            __filter_prefix = ""
            __filter_suffix = ""

        resource_filter = self.config_get('resource_filter')
        if resource_filter is not None:
            __filter_prefix = "(&%s" % resource_filter
            __filter_suffix = ")"

        recipient_address_attrs = self.config_get_list("mail_attributes")

        result_attributes = recipient_address_attrs
        result_attributes.append(self.config_get('unique_attribute'))
        result_attributes.append('kolabTargetFolder')

        _filter = "(|"

        if isinstance(folder, string_types):
            _filter += "(kolabTargetFolder=%s)" % (folder)
        else:
            for _folder in folder:
                _filter += "(kolabTargetFolder=%s)" % (_folder)

        _filter += ")"

        _filter = "%s%s%s" % (__filter_prefix, _filter, __filter_suffix)

        log.debug(_l("Finding resource with filter %r") % (_filter), level=8)

        if len(_filter) <= 6:
            return None

        resource_base_dn = self._object_base_dn('resource')

        _results = self.ldap.search_s(
            resource_base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=_filter,
            attrlist=result_attributes,
            attrsonly=True
        )

        _entry_dns = []

        for _result in _results:
            (_entry_id, _entry_attrs) = _result
            _entry_dns.append(_entry_id)

        return _entry_dns

    def find_recipient(self, address="*", exclude_entry_id=None, search_attrs=None):
        """
            Given an address string or list of addresses, find one or more valid
            recipients.

            Use this function only to detect whether an address is already in
            use by any entry in the tree.

            Specify an additional entry_id to exclude to exclude matches against
            the current entry.

            In search_attrs you can specify list of search attributes. By default
            mail_attributes are used.
        """

        self._bind()

        if exclude_entry_id is not None:
            __filter_prefix = "(&"
            __filter_suffix = "(!(%s=%s)))" % (
                self.config_get('unique_attribute'),
                ldap.filter.escape_filter_chars(exclude_entry_id)
            )

        else:
            __filter_prefix = ""
            __filter_suffix = ""

        if search_attrs is not None:
            recipient_address_attrs = search_attrs
        else:
            recipient_address_attrs = self.config_get_list("mail_attributes")

        result_attributes = recipient_address_attrs
        result_attributes.append(self.config_get('unique_attribute'))

        _filter = "(|"

        for recipient_address_attr in recipient_address_attrs:
            if isinstance(address, string_types):
                _filter += "(%s=%s)" % (recipient_address_attr, address)
            else:
                for _address in address:
                    _filter += "(%s=%s)" % (recipient_address_attr, _address)

        _filter += ")"

        _filter = "%s%s%s" % (__filter_prefix, _filter, __filter_suffix)

        log.debug(_l("Finding recipient with filter %r") % (_filter), level=8)

        if len(_filter) <= 6:
            return None

        config_base_dn = self.config_get('base_dn')
        ldap_base_dn = self._kolab_domain_root_dn(self.domain)

        if ldap_base_dn is not None and not ldap_base_dn == config_base_dn:
            base_dn = ldap_base_dn
        else:
            base_dn = config_base_dn

        _results = self.ldap.search_s(
            base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=_filter,
            attrlist=result_attributes,
            attrsonly=True
        )

        _entry_dns = []

        for _result in _results:
            (_entry_id, _entry_attrs) = _result

            # Prevent Active Directory referrals
            if _entry_id is not None:
                _entry_dns.append(_entry_id)

        return _entry_dns

    def find_resource(self, address="*", exclude_entry_id=None):
        """
            Given an address string or list of addresses, find one or more valid
            resources.

            Specify an additional entry_id to exclude to exclude matches.
        """

        self._bind()

        if exclude_entry_id is not None:
            __filter_prefix = "(&"
            __filter_suffix = "(!(%s=%s)))" % (
                self.config_get('unique_attribute'),
                ldap.filter.escape_filter_chars(exclude_entry_id)
            )

        else:
            __filter_prefix = ""
            __filter_suffix = ""

        resource_filter = self.config_get('resource_filter')
        if resource_filter is not None:
            __filter_prefix = "(&%s" % resource_filter
            __filter_suffix = ")"

        recipient_address_attrs = self.config_get_list("mail_attributes")

        result_attributes = recipient_address_attrs
        result_attributes.append(self.config_get('unique_attribute'))

        _filter = "(|"

        for recipient_address_attr in recipient_address_attrs:
            if isinstance(address, string_types):
                _filter += "(%s=%s)" % (recipient_address_attr, address)
            else:
                for _address in address:
                    _filter += "(%s=%s)" % (recipient_address_attr, _address)

        _filter += ")"

        _filter = "%s%s%s" % (__filter_prefix, _filter, __filter_suffix)

        log.debug(_l("Finding resource with filter %r") % (_filter), level=8)

        if len(_filter) <= 6:
            return None

        resource_base_dn = self._object_base_dn('resource')

        _results = self.ldap.search_s(
            resource_base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=_filter,
            attrlist=result_attributes,
            attrsonly=True
        )

        # Remove referrals
        _entry_dns = [_e[0] for _e in _results if _e[0] is not None]

        return _entry_dns

    def get_latest_sync_timestamp(self):
        timestamp = cache.last_modify_timestamp(self.domain)
        log.debug(_l("Using timestamp %r") % (timestamp), level=8)
        return timestamp

    def list_secondary_domains(self):
        """
            List alias domain name spaces for the current domain name space.
        """
        if self.domains is not None:
            return [s for s in self.domains.keys() if s not in self.domains.values()]

        return []

    def recipient_policy(self, entry):
        """
            Apply a recipient policy, if configured.

            Given an entry, returns the entry's attribute values to be set.
        """
        entry_dn = self.entry_dn(entry)
        entry_modifications = {}
        entry_type = self._entry_type(entry)
        mail_attributes = self.config_get_list('mail_attributes')
        primary_mail = None
        primary_mail_attribute = None
        secondary_mail = None
        secondary_mail_attribute = None

        if len(mail_attributes) >= 1:
            primary_mail_attribute = mail_attributes[0]

        if len(mail_attributes) >= 2:
            secondary_mail_attribute = mail_attributes[1]

        daemon_rcpt_policy = self.config_get('daemon_rcpt_policy')
        if not utils.true_or_false(daemon_rcpt_policy) and daemon_rcpt_policy is not None:
            log.debug(
                _l("Not applying recipient policy for %s (disabled through configuration)") % (
                    entry_dn
                ),
                level=1
            )

            return entry_modifications

        want_attrs = []

        log.debug(_l("Applying recipient policy to %r") % (entry_dn), level=8)

        # See which mail attributes we would want to control.
        #
        # 'mail' is considered for primary_mail,
        # 'alias' and 'mailalternateaddress' are considered for secondary mail.
        #
        primary_mail = self.config_get_raw('%s_primary_mail' % (entry_type))
        if primary_mail is None and entry_type == 'user':
            primary_mail = self.config_get_raw('primary_mail')

        if secondary_mail_attribute is not None:
            secondary_mail = self.config_get_raw('%s_secondary_mail' % (entry_type))
            if secondary_mail is None and entry_type == 'user':
                secondary_mail = self.config_get_raw('secondary_mail')

        log.debug(
            _l("Using mail attributes: %r, with primary %r and secondary %r") % (
                mail_attributes,
                primary_mail_attribute,
                secondary_mail_attribute
            ),
            level=8
        )

        for _mail_attr in mail_attributes:
            if _mail_attr not in entry:
                log.debug(_l("key %r not in entry") % (_mail_attr), level=8)
                if _mail_attr == primary_mail_attribute:
                    log.debug(_l("key %r is the prim. mail attr.") % (_mail_attr), level=8)
                    if primary_mail is not None:
                        log.debug(_l("prim. mail pol. is not empty"), level=8)
                        want_attrs.append(_mail_attr)
                elif _mail_attr == secondary_mail_attribute:
                    log.debug(_l("key %r is the sec. mail attr.") % (_mail_attr), level=8)
                    if secondary_mail is not None:
                        log.debug(_l("sec. mail pol. is not empty"), level=8)
                        want_attrs.append(_mail_attr)

        if want_attrs:
            log.debug(
                _l("Attributes %r are not yet available for entry %r") % (
                    want_attrs,
                    entry_dn
                ),
                level=8
            )

        # Also append the preferredlanguage or 'native tongue' configured
        # for the entry.
        if 'preferredlanguage' not in entry:
            want_attrs.append('preferredlanguage')

        # If we wanted anything, now is the time to get it.
        if want_attrs:
            log.debug(
                _l("Attributes %r are not yet available for entry %r") % (
                    want_attrs,
                    entry_dn
                ),
                level=8
            )

            attributes = self.get_entry_attributes(entry_dn, want_attrs)

            for attribute in attributes.keys():
                entry[attribute] = attributes[attribute]

        if 'preferredlanguage' not in entry:
            entry['preferredlanguage'] = conf.get('kolab', 'default_locale')

        # Primary mail address
        if primary_mail is not None:
            primary_mail_address = conf.plugins.exec_hook(
                "set_primary_mail",
                kw={
                    'primary_mail': primary_mail,
                    'entry': entry,
                    'primary_domain': self.domain
                }
            )

            if primary_mail_address is None:
                return entry_modifications

            i = 1
            _primary_mail = primary_mail_address

            done = False
            while not done:
                results = self.find_recipient(_primary_mail, entry['id'])

                # Length of results should be 0 (no entry found)
                # or 1 (which should be the entry we're looking at here)
                if not results:
                    log.debug(
                        _l("No results for mail address %s found") % (
                            _primary_mail
                        ),
                        level=8
                    )

                    done = True
                    continue

                if len(results) == 1:
                    log.debug(
                        _l("1 result for address %s found, verifying") % (
                            _primary_mail
                        ),
                        level=8
                    )

                    almost_done = True
                    for result in results:
                        if not result == entry_dn:
                            log.debug(
                                _l(
                                    "Too bad, primary email address %s "
                                    + "already in use for %s (we are %s)"
                                ) % (
                                    _primary_mail,
                                    result,
                                    entry_dn
                                ),
                                level=8
                            )

                            almost_done = False
                        else:
                            log.debug(_l("Address assigned to us"), level=8)

                    if almost_done:
                        done = True
                        continue

                i += 1
                _primary_mail = "%s%d@%s" % (
                    primary_mail_address.split('@')[0],
                    i,
                    primary_mail_address.split('@')[1]
                )

            primary_mail_address = _primary_mail

            ###
            # FIXME
            ###
            if primary_mail_address is not None:
                if primary_mail_attribute not in entry:
                    self.set_entry_attribute(entry, primary_mail_attribute, primary_mail_address)
                    entry_modifications[primary_mail_attribute] = primary_mail_address
                else:
                    if not primary_mail_address == entry[primary_mail_attribute]:
                        self.set_entry_attribute(
                            entry,
                            primary_mail_attribute,
                            primary_mail_address
                        )

                        entry_modifications[primary_mail_attribute] = primary_mail_address

        # pylint: disable=too-many-nested-blocks
        if secondary_mail is not None:
            # Execute the plugin hook
            suggested_secondary_mail = conf.plugins.exec_hook(
                "set_secondary_mail",
                kw={
                    'secondary_mail': secondary_mail,
                    'entry': entry,
                    'domain': self.domain,
                    'primary_domain': self.domain,
                    'secondary_domains': self.list_secondary_domains()
                }
            )  # end of conf.plugins.exec_hook() call

            secondary_mail_addresses = []

            for _secondary_mail in suggested_secondary_mail:
                i = 1
                __secondary_mail = _secondary_mail

                done = False
                while not done:
                    results = self.find_recipient(__secondary_mail, entry['id'])

                    # Length of results should be 0 (no entry found)
                    # or 1 (which should be the entry we're looking at here)
                    if not results:
                        log.debug(
                            _l("No results for address %s found") % (
                                __secondary_mail
                            ),
                            level=8
                        )

                        done = True
                        continue

                    if len(results) == 1:
                        log.debug(
                            _l("1 result for address %s found, verifying...") % (
                                __secondary_mail
                            ),
                            level=8
                        )

                        almost_done = True
                        for result in results:
                            if not result == entry_dn:
                                log.debug(
                                    _l(
                                        "Too bad, secondary email "
                                        + "address %s already in use for "
                                        + "%s (we are %s)"
                                    ) % (
                                        __secondary_mail,
                                        result,
                                        entry_dn
                                    ),
                                    level=8
                                )

                                almost_done = False
                            else:
                                log.debug(_l("Address assigned to us"), level=8)

                        if almost_done:
                            done = True
                            continue

                    i += 1
                    __secondary_mail = "%s%d@%s" % (
                        _secondary_mail.split('@')[0],
                        i,
                        _secondary_mail.split('@')[1]
                    )

                secondary_mail_addresses.append(__secondary_mail)

            log.debug(
                _l(
                    "Recipient policy composed the following set of secondary email addresses: %r"
                ) % (
                    secondary_mail_addresses
                ),
                level=8
            )

            if secondary_mail_attribute in entry:
                if isinstance(entry[secondary_mail_attribute], list):
                    secondary_mail_addresses.extend(entry[secondary_mail_attribute])
                else:
                    secondary_mail_addresses.append(entry[secondary_mail_attribute])

            if secondary_mail_addresses is not None:
                log.debug(
                    _l("Secondary mail addresses that we want is not None: %r") % (
                        secondary_mail_addresses
                    ),
                    level=8
                )

                secondary_mail_addresses = list(set(secondary_mail_addresses))

                # Avoid duplicates
                while primary_mail_address in secondary_mail_addresses:
                    log.debug(
                        _l(
                            "Avoiding the duplication of the primary mail "
                            + "address %r in the list of secondary mail "
                            + "addresses"
                        ) % (primary_mail_address),
                        level=8
                    )

                    secondary_mail_addresses.pop(
                        secondary_mail_addresses.index(primary_mail_address)
                    )

                log.debug(
                    _l("Entry is getting secondary mail addresses: %r") % (
                        secondary_mail_addresses
                    ),
                    level=8
                )

                if secondary_mail_attribute not in entry:
                    log.debug(
                        _l("Entry did not have any secondary mail addresses in %r") % (
                            secondary_mail_attribute
                        ),
                        level=8
                    )

                    if secondary_mail_addresses:
                        self.set_entry_attribute(
                            entry,
                            secondary_mail_attribute,
                            secondary_mail_addresses
                        )

                        entry_modifications[secondary_mail_attribute] = secondary_mail_addresses
                else:
                    if isinstance(entry[secondary_mail_attribute], string_types):
                        entry[secondary_mail_attribute] = [entry[secondary_mail_attribute]]

                    log.debug(
                        _l("secondary_mail_addresses: %r") % (secondary_mail_addresses),
                        level=8
                    )

                    log.debug(
                        _l("entry[%s]: %r") % (
                            secondary_mail_attribute,
                            entry[secondary_mail_attribute]
                        ),
                        level=8
                    )

                    secondary_mail_addresses.sort()
                    entry[secondary_mail_attribute].sort()

                    log.debug(
                        _l("secondary_mail_addresses: %r") % (secondary_mail_addresses),
                        level=8
                    )

                    log.debug(
                        _l("entry[%s]: %r") % (
                            secondary_mail_attribute,
                            entry[secondary_mail_attribute]
                        ),
                        level=8
                    )

                    smas = list(set(secondary_mail_addresses))
                    if smas != list(set(entry[secondary_mail_attribute])):
                        self.set_entry_attribute(
                            entry,
                            secondary_mail_attribute,
                            smas
                        )

                        entry_modifications[secondary_mail_attribute] = smas

        log.debug(_l("Entry modifications list: %r") % (entry_modifications), level=8)

        return entry_modifications

    def reconnect(self):
        bind = self.bind
        self._disconnect()
        self.connect()
        if bind is not None:
            self._bind(bind['dn'], bind['pw'])

    def search_entry_by_attribute(self, attr, value, **kw):
        self._bind()

        _filter = "(%s=%s)" % (attr, ldap.filter.escape_filter_chars(value))

        config_base_dn = self.config_get('base_dn')
        ldap_base_dn = self._kolab_domain_root_dn(self.domain)

        if ldap_base_dn is not None and not ldap_base_dn == config_base_dn:
            base_dn = ldap_base_dn
        else:
            base_dn = config_base_dn

        _results = self._search(
            base_dn,
            filterstr=_filter,
            attrlist=[
                '*',
            ],
            override_search='_regular_search'
        )

        # Remove referrals
        _entry_dns = [_e for _e in _results if _e[0] is not None]

        return _entry_dns

    def set_entry_attribute(self, entry_id, attribute, value):
        log.debug(
            _l("Setting entry attribute %r to %r for %r") % (attribute, value, entry_id),
            level=8
        )

        self.set_entry_attributes(entry_id, {attribute: value})

    def set_entry_attributes(self, entry_id, attributes):
        self._bind()

        entry_dn = self.entry_dn(entry_id)

        entry = self.get_entry_attributes(entry_dn, ['*'])

        attrs = {}

        for attribute in attributes.keys():
            attrs[attribute.lower()] = attributes[attribute]

        modlist = []

        for attribute, value in attrs.items():
            if attribute not in entry:
                entry[attribute] = self.get_entry_attribute(entry_id, attribute)

            if attribute in entry and entry[attribute] is None:
                modlist.append((ldap.MOD_ADD, attribute, value))
            elif attribute in entry and entry[attribute] is not None:
                if value is None:
                    modlist.append((ldap.MOD_DELETE, attribute, entry[attribute]))
                else:
                    modlist.append((ldap.MOD_REPLACE, attribute, value))

        dn = entry_dn

        if modlist and self._bind_priv() is True:
            try:
                self.ldap_priv.modify_s(dn, modlist)
            except Exception as errmsg:
                log.error(
                    _l("Could not update dn:\nDN: %r\nModlist: %r\nError Message: %r") % (
                        dn,
                        modlist,
                        errmsg
                    )
                )

                log.error(traceback.format_exc())

    def synchronize(self, mode=0, callback=None):
        """
            Synchronize with LDAP
        """
        self._bind()

        _filter = self._kolab_filter()

        modified_after = None

        if hasattr(conf, 'resync'):
            if not conf.resync:
                modified_after = self.get_latest_sync_timestamp()
            else:
                modifytimestamp_format = conf.get_raw(
                    'ldap',
                    'modifytimestamp_format',
                    default="%Y%m%d%H%M%SZ"
                ).replace('%%', '%')

                modified_after = datetime.datetime(1900, 1, 1, 00, 00, 00).strftime(
                    modifytimestamp_format
                )

        else:
            modified_after = self.get_latest_sync_timestamp()

        _filter = "(&%s(modifytimestamp>=%s))" % (_filter, modified_after)

        log.debug(_l("Synchronization is using filter %r") % (_filter), level=8)

        if mode != 0:
            override_search = mode
        else:
            override_search = False

        config_base_dn = self.config_get('base_dn')
        ldap_base_dn = self._kolab_domain_root_dn(self.domain)

        if ldap_base_dn is not None and not ldap_base_dn == config_base_dn:
            base_dn = ldap_base_dn
        else:
            base_dn = config_base_dn

        log.debug(_l("Synchronization is searching against base DN: %s") % (base_dn), level=8)

        if callback is None:
            callback = self._synchronize_callback

        try:
            self._search(
                base_dn,
                filterstr=_filter,
                attrlist=[
                    '*',
                    self.config_get('unique_attribute'),
                    conf.get('cyrus-sasl', 'result_attribute'),
                    'modifytimestamp'
                ],
                override_search=override_search,
                callback=callback,
            )
        except Exception as errmsg:
            log.error("An error occurred: %r" % (errmsg))
            log.error(_l("%s") % (traceback.format_exc()))

    def user_quota(self, entry_id, folder):
        default_quota = self.config_get('default_quota')
        quota_attribute = self.config_get('quota_attribute')

        if quota_attribute is None:
            return

        # The default quota may be None, but LDAP quota could still be set
        if default_quota is None:
            default_quota = 0

        self._bind()

        entry_dn = self.entry_dn(entry_id)

        current_ldap_quota = self.get_entry_attribute(entry_dn, quota_attribute)
        _imap_quota = self.imap.get_quota(folder)

        if _imap_quota is None:
            used = None
            current_imap_quota = None
        else:
            (used, current_imap_quota) = _imap_quota

        log.debug(
            _l(
                "About to consider the user quota for %r (used: %r, "
                + "imap: %r, ldap: %r, default: %r)"
            ) % (
                entry_dn,
                used,
                current_imap_quota,
                current_ldap_quota,
                default_quota
            ),
            level=8
        )

        new_quota = conf.plugins.exec_hook(
            "set_user_folder_quota",
            kw={
                'used': used,
                'imap_quota': current_imap_quota,
                'ldap_quota': current_ldap_quota,
                'default_quota': default_quota
            }
        )

        try:
            current_ldap_quota = (int)(current_ldap_quota)
        except Exception:
            current_ldap_quota = None

        # If the new quota is zero, get out
        if new_quota == 0:
            return

        if current_ldap_quota is not None:
            if not new_quota == (int)(current_ldap_quota):
                self.set_entry_attribute(
                    entry_dn,
                    quota_attribute,
                    "%s" % (new_quota)
                )
        else:
            if new_quota is not None:
                self.set_entry_attribute(
                    entry_dn,
                    quota_attribute,
                    "%s" % (new_quota)
                )

        if current_imap_quota is not None:
            if not new_quota == current_imap_quota:
                self.imap.set_quota(folder, new_quota)

        else:
            if new_quota is not None:
                self.imap.set_quota(folder, new_quota)

    ###
    # API depth level increasing!
    ###

    def _bind(self, bind_dn=None, bind_pw=None):
        # If we have no LDAP, we have no previous state.
        if self.ldap is None:
            self.bind = None
            self.connect()

        # If the bind_dn is None and the bind_pw is not... fail
        if bind_dn is None and bind_pw is not None:
            log.error(_l("Attempting to bind without a DN but with a password"))
            return False

        # and the same vice-versa
        if bind_dn is None and bind_pw is not None:
            log.error(_l("Attempting to bind with a DN but without a password"))
            return False

        # If we are to bind as foo, we have no state.
        if bind_dn is not None:
            self.bind = None

        # Only if we have no state and no bind credentials specified in the
        # function call.
        if self.bind is None:

            if bind_dn is None:
                bind_dn = self.config_get('service_bind_dn')

            if bind_pw is None:
                bind_pw = self.config_get('service_bind_pw')

        if bind_dn is not None:
            log.debug(
                _l("Binding with bind_dn: %s and password: %s") % (
                    bind_dn,
                    '*' * len(bind_pw)
                ),
                level=8
            )

            # TODO: Binding errors control
            try:
                # Must be synchronous
                self.ldap.simple_bind_s(bind_dn, bind_pw)
                self.bind = {'dn': bind_dn, 'pw': bind_pw}

                return True

            except ldap.SERVER_DOWN as errmsg:
                log.error(_l("LDAP server unavailable: %r") % (errmsg))
                log.error(_l("%s") % (traceback.format_exc()))

                return False

            except ldap.NO_SUCH_OBJECT:
                log.error(
                    _l("Invalid DN, username and/or password for '%s'.") % (
                        bind_dn
                    )
                )

                return False

            except ldap.INVALID_CREDENTIALS:
                log.error(
                    _l("Invalid DN, username and/or password for '%s'.") % (
                        bind_dn
                    )
                )

                return False

        else:
            log.debug(_l("bind() called but already bound"), level=8)

            return True

    def _bind_priv(self):
        if self.ldap_priv is None:
            self.connect(True)

            bind_dn = self.config_get('bind_dn')
            bind_pw = self.config_get('bind_pw')

            try:
                self.ldap_priv.simple_bind_s(bind_dn, bind_pw)
                return True
            except ldap.SERVER_DOWN as errmsg:
                log.error(_l("LDAP server unavailable: %r") % (errmsg))
                log.error(_l("%s") % (traceback.format_exc()))
                return False
            except ldap.INVALID_CREDENTIALS:
                log.error(
                    _l("Invalid DN, username and/or password for '%s'.") % (
                        bind_dn
                    )
                )

                return False
        else:
            log.debug(_l("bind_priv() called but already bound"), level=8)
            return True

    def _change_add_group(self, entry, change):
        """
            An entry of type group was added.

            The Kolab daemon has little to do for this type of action on this
            type of entry.
        """
        pass

    def _change_add_None(self, entry, change):
        """
            Redirect to _change_add_unknown
        """
        self._change_add_unknown(entry, change)

    def _change_add_resource(self, entry, change):
        """
            An entry of type resource was added.

            The Kolab daemon has little to do for this type of action on this
            type of entry.
        """
        pass

    def _change_add_role(self, entry, change):
        """
            An entry of type role was added.

            The Kolab daemon has little to do for this type of action on this
            type of entry.
        """
        pass

    def _change_add_sharedfolder(self, entry, change):
        """
            An entry of type sharedfolder was added.
        """
        self.imap.connect(domain=self.domain)

        server = None

        # Get some configuration values
        mailserver_attribute = self.config_get('mailserver_attribute')
        if mailserver_attribute in entry:
            server = entry[mailserver_attribute]

        foldertype_attribute = self.config_get('sharedfolder_type_attribute')
        if foldertype_attribute is not None:
            if foldertype_attribute not in entry:
                entry[foldertype_attribute] = self.get_entry_attribute(
                    entry['id'],
                    foldertype_attribute
                )

            if entry[foldertype_attribute] is not None:
                entry['kolabfoldertype'] = entry[foldertype_attribute]

        if 'kolabfoldertype' not in entry:
            entry['kolabfoldertype'] = self.get_entry_attribute(
                entry['id'],
                'kolabfoldertype'
            )

        # A delivery address is postuser+targetfolder
        delivery_address_attribute = self.config_get('sharedfolder_delivery_address_attribute')
        if delivery_address_attribute is None:
            delivery_address_attribute = 'mail'

        if delivery_address_attribute not in entry:
            entry[delivery_address_attribute] = self.get_entry_attribute(
                entry['id'],
                delivery_address_attribute
            )

        if entry[delivery_address_attribute] is not None:
            if len(entry[delivery_address_attribute].split('+')) > 1:
                entry['kolabtargetfolder'] = entry[delivery_address_attribute].split('+')[1]

        if 'kolabtargetfolder' not in entry:
            entry['kolabtargetfolder'] = self.get_entry_attribute(
                entry['id'],
                'kolabtargetfolder'
            )

        if 'kolabtargetfolder' in entry and entry['kolabtargetfolder'] is not None:
            folder_path = entry['kolabtargetfolder']
        else:
            # TODO: What is *the* way to see if we need to create an @domain
            # shared mailbox?
            # TODO^2: self.domain, really? Presumes any mail attribute is
            # set to the primary domain name space...
            # TODO^3: Test if the cn is already something@domain
            result_attribute = conf.get('cyrus-sasl', 'result_attribute')
            if result_attribute in ['mail']:
                folder_path = "%s@%s" % (entry['cn'], self.domain)
            else:
                folder_path = entry['cn']

        if not folder_path.startswith('shared/'):
            folder_path = "shared/%s" % folder_path

        folderacl_entry_attribute = self.config_get('sharedfolder_acl_entry_attribute')
        if folderacl_entry_attribute is None:
            folderacl_entry_attribute = 'acl'

        if folderacl_entry_attribute not in entry:
            entry[folderacl_entry_attribute] = self.get_entry_attribute(
                entry['id'],
                folderacl_entry_attribute
            )

        if not self.imap.shared_folder_exists(folder_path):
            self.imap.shared_folder_create(folder_path, server)

        if 'kolabfoldertype' in entry and entry['kolabfoldertype'] is not None:

            self.imap.shared_folder_set_type(folder_path, entry['kolabfoldertype'])

        entry['kolabfolderaclentry'] = self._parse_acl(entry[folderacl_entry_attribute])

        # pylint: disable=protected-access
        self.imap._set_kolab_mailfolder_acls(entry['kolabfolderaclentry'], folder_path)

        if delivery_address_attribute in entry:
            if entry[delivery_address_attribute] is not None:
                self.imap.set_acl(folder_path, 'anyone', '+p')

        # if server is None:
            # self.entry_set_attribute(mailserver_attribute, server)

    def _change_add_unknown(self, entry, change):
        """
            An entry has been add, and we do not know of what object type
            the entry was - user, group, role or sharedfolder.
        """
        success = None

        result_attribute = conf.get('cyrus-sasl', 'result_attribute')

        if result_attribute not in entry:
            return None

        if entry[result_attribute] is None:
            return None

        for _type in ['user', 'group', 'role', 'sharedfolder']:
            try:
                func = getattr(self, '_change_add_%s' % (_type))
                func(entry, change)
                success = True
            except Exception:
                success = False

            if success:
                break

        return success

    def _change_add_user(self, entry, change):
        """
            An entry of type user was added.
        """
        mailserver_attribute = self.config_get('mailserver_attribute')
        if mailserver_attribute is None:
            mailserver_attribute = 'mailhost'

        mailserver_attribute = mailserver_attribute.lower()

        result_attribute = conf.get('cyrus-sasl', 'result_attribute')
        if result_attribute is None:
            result_attribute = 'mail'

        result_attribute = result_attribute.lower()

        if mailserver_attribute not in entry:
            entry[mailserver_attribute] = \
                self.get_entry_attribute(entry, mailserver_attribute)

        rcpt_addrs = self.recipient_policy(entry)
        for key in rcpt_addrs:
            entry[key] = rcpt_addrs[key]

        if result_attribute not in entry:
            return

        if entry[result_attribute] is None:
            return

        if entry[result_attribute] == '':
            return

        cache.get_entry(self.domain, entry)

        self.imap.connect(domain=self.domain)

        if not self.imap.user_mailbox_exists(entry[result_attribute].lower()):
            folder = self.imap.user_mailbox_create(
                entry[result_attribute],
                entry[mailserver_attribute]
            )

        else:
            folder = "user%s%s" % (self.imap.get_separator(), entry[result_attribute].lower())

        server = self.imap.user_mailbox_server(folder)

        log.debug(
            _l("Entry %s attribute value: %r") % (
                mailserver_attribute,
                entry[mailserver_attribute]
            ),
            level=8
        )

        log.debug(
            _l("imap.user_mailbox_server(%r) result: %r") % (
                folder,
                server
            ),
            level=8
        )

        if not entry[mailserver_attribute] == server:
            self.set_entry_attribute(entry, mailserver_attribute, server)

        self.user_quota(entry, folder)

    def _change_delete_group(self, entry, change):
        """
            An entry of type group was deleted.
        """

        result_attribute = conf.get('cyrus-sasl', 'result_attribute')

        if result_attribute not in entry:
            return None

        if entry[result_attribute] is None:
            return None

        return self.imap.cleanup_acls(entry[result_attribute])

    def _change_delete_None(self, entry, change):
        """
            Redirect to _change_delete_unknown
        """
        self._change_delete_unknown(entry, change)

    def _change_delete_resource(self, entry, change):
        pass

    def _change_delete_role(self, entry, change):
        pass

    def _change_delete_sharedfolder(self, entry, change):
        pass

    def _change_delete_unknown(self, entry, change):
        """
            An entry has been deleted, and we do not know of what object type
            the entry was - user, group, resource, role or sharedfolder.
        """
        result_attribute = conf.get('cyrus-sasl', 'result_attribute')

        if result_attribute not in entry:
            return None

        if entry[result_attribute] is None:
            return None

        success = True
        for _type in ['user', 'group', 'resource', 'role', 'sharedfolder']:
            try:
                func = getattr(self, '_change_delete_%s' % (_type))
                success = func(entry, change)
            except Exception as errmsg:
                log.error(_l("An error occured: %r") % (errmsg))
                log.error(_l("%s") % (traceback.format_exc()))

                success = False

            if success:
                break

        return success

    def _change_delete_user(self, entry, change):
        """
            An entry of type user was deleted.
        """
        result_attribute = conf.get('cyrus-sasl', 'result_attribute')

        if result_attribute not in entry:
            return None

        if entry[result_attribute] is None:
            return None

        cache.delete_entry(self.domain, entry)

        self.imap.user_mailbox_delete(entry[result_attribute])
        self.imap.cleanup_acls(entry[result_attribute])

        # let plugins act upon this deletion
        conf.plugins.exec_hook(
            'user_delete',
            kw={
                'user': entry,
                'domain': self.domain
            }
        )

        return True

    def _change_moddn_group(self, entry, change):
        # TODO: If the rdn attribute is the same as the result attribute...
        pass

    def _change_moddn_role(self, entry, change):
        pass

    def _change_moddn_user(self, entry, change):
        old_dn = change['previous_dn']
        new_dn = change['dn']

        old_rdn = explode_dn(old_dn)[0].split('=')[0]
        new_rdn = explode_dn(new_dn)[0].split('=')[0]

        result_attribute = conf.get('cyrus-sasl', 'result_attribute')

        old_canon_attr = None

        cache_entry = cache.get_entry(self.domain, entry)
        if cache_entry is not None:
            old_canon_attr = cache_entry.result_attribute

        # See if we have to trigger the recipient policy. Only really applies to
        # situations in which the result_attribute is used in the old or in the
        # new DN.
        trigger_recipient_policy = False

        if old_rdn == result_attribute:
            if new_rdn == result_attribute:
                if new_rdn == old_rdn:
                    trigger_recipient_policy = True
            else:
                if not new_rdn == old_rdn:
                    trigger_recipient_policy = True
        else:
            if new_rdn == result_attribute:
                if not new_rdn == old_rdn:
                    trigger_recipient_policy = True

        if trigger_recipient_policy:
            entry_changes = self.recipient_policy(entry)

            for key, value in entry_changes.items():
                entry[key] = value

            if result_attribute not in entry:
                return

            if entry[result_attribute] is None:
                return

            if entry[result_attribute] == '':
                return

            # Now look at entry_changes and old_canon_attr, and see if they're
            # the same value.
            if result_attribute in entry_changes:
                if old_canon_attr is not None:
                    self.imap.user_mailbox_create(entry_changes[result_attribute])

                elif not entry_changes[result_attribute] == old_canon_attr:
                    self.imap.user_mailbox_rename(old_canon_attr, entry_changes[result_attribute])

        cache.get_entry(self.domain, entry)

    def _change_moddn_sharedfolder(self, entry, change):
        result_attribute = 'cn'

        old_cn = explode_dn(change['previous_dn'], True)[0]

        if 'kolabtargetfolder' in entry and entry['kolabtargetfolder'] is not None:
            new_folder_path = entry['kolabtargetfolder']
            old_folder_path = old_cn

            if '@' in entry['kolabtargetfolder']:
                old_folder_path = "%s@%s" % (
                    old_folder_path,
                    entry['kolabtargetfolder'].split('@')[1]
                )

        else:
            result_attribute = conf.get('cyrus-sasl', 'result_attribute')
            if result_attribute in ['mail']:
                new_folder_path = "%s@%s" % (entry['cn'], self.domain)
                old_folder_path = "%s@%s" % (old_cn, self.domain)
            else:
                new_folder_path = "%s" % (entry['cn'])
                old_folder_path = old_cn

        if not new_folder_path.startswith('shared/'):
            new_folder_path = "shared/%s" % (new_folder_path)

        if not old_folder_path.startswith('shared/'):
            old_folder_path = "shared/%s" % (old_folder_path)

        log.debug("old folder path: %r" % (old_folder_path))
        log.debug("new folder path: %r" % (new_folder_path))

        self.imap.shared_folder_rename(old_folder_path, new_folder_path)

    def _change_modify_None(self, entry, change):
        pass

    def _change_modify_group(self, entry, change):
        pass

    def _change_modify_role(self, entry, change):
        pass

    def _change_modify_sharedfolder(self, entry, change):
        """
            A shared folder was modified.
        """
        self.imap.connect(domain=self.domain)

        server = None

        # Get some configuration values
        mailserver_attribute = self.config_get('mailserver_attribute')
        if mailserver_attribute in entry:
            server = entry[mailserver_attribute]

        foldertype_attribute = self.config_get('sharedfolder_type_attribute')
        if foldertype_attribute is not None:
            if foldertype_attribute not in entry:
                entry[foldertype_attribute] = self.get_entry_attribute(
                    entry['id'],
                    foldertype_attribute
                )

            if entry[foldertype_attribute] is not None:
                entry['kolabfoldertype'] = entry[foldertype_attribute]

        if 'kolabfoldertype' not in entry:
            entry['kolabfoldertype'] = self.get_entry_attribute(
                entry['id'],
                'kolabfoldertype'
            )

        # A delivery address is postuser+targetfolder
        delivery_address_attribute = self.config_get('sharedfolder_delivery_address_attribute')
        if delivery_address_attribute is not None:
            if delivery_address_attribute not in entry:
                entry[delivery_address_attribute] = self.get_entry_attribute(
                    entry['id'],
                    delivery_address_attribute
                )

            if entry[delivery_address_attribute] is not None:
                if len(entry[delivery_address_attribute].split('+')) > 1:
                    entry['kolabtargetfolder'] = entry[delivery_address_attribute].split('+')[1]

        if 'kolabtargetfolder' not in entry:
            entry['kolabtargetfolder'] = self.get_entry_attribute(
                entry['id'],
                'kolabtargetfolder'
            )

        if 'kolabtargetfolder' in entry and entry['kolabtargetfolder'] is not None:
            folder_path = entry['kolabtargetfolder']
        else:
            # TODO: What is *the* way to see if we need to create an @domain
            # shared mailbox?
            # TODO^2: self.domain, really? Presumes any mail attribute is
            # set to the primary domain name space...
            # TODO^3: Test if the cn is already something@domain
            result_attribute = conf.get('cyrus-sasl', 'result_attribute')
            if result_attribute in ['mail']:
                folder_path = "%s@%s" % (entry['cn'], self.domain)
            else:
                folder_path = entry['cn']

        if not folder_path.startswith('shared/'):
            folder_path = "shared/%s" % folder_path

        folderacl_entry_attribute = self.config_get('sharedfolder_acl_entry_attribute')
        if folderacl_entry_attribute is None:
            folderacl_entry_attribute = 'acl'

        if folderacl_entry_attribute not in entry:
            entry[folderacl_entry_attribute] = self.get_entry_attribute(
                entry['id'],
                folderacl_entry_attribute
            )

        if not self.imap.shared_folder_exists(folder_path):
            self.imap.shared_folder_create(folder_path, server)

        if 'kolabfoldertype' in entry and entry['kolabfoldertype'] is not None:
            self.imap.shared_folder_set_type(
                folder_path,
                entry['kolabfoldertype']
            )

        entry['kolabfolderaclentry'] = self._parse_acl(entry[folderacl_entry_attribute])

        # pylint: disable=protected-access
        self.imap._set_kolab_mailfolder_acls(entry['kolabfolderaclentry'], folder_path, True)

        if delivery_address_attribute in entry and entry[delivery_address_attribute] is not None:
            self.imap.set_acl(folder_path, 'anyone', '+p')

    def _change_modify_user(self, entry, change):
        """
            Handle the changes for an object of type user.

            Expects the new entry.
        """

        # Initialize old_canon_attr (#1701)
        old_canon_attr = None

        result_attribute = conf.get('cyrus-sasl', 'result_attribute')

        _entry = cache.get_entry(self.domain, entry, update=False)

        # We do not necessarily have a synchronisation cache entry (#1701)
        if _entry is not None:
            if 'result_attribute' in _entry.__dict__ and not _entry.result_attribute == '':
                old_canon_attr = _entry.result_attribute

        entry_changes = self.recipient_policy(entry)

        log.debug(
            _l("Result from recipient policy: %r") % (entry_changes),
            level=8
        )

        if result_attribute in entry_changes:
            if not entry_changes[result_attribute] == old_canon_attr:
                if old_canon_attr is None:
                    self.imap.user_mailbox_create(
                        entry_changes[result_attribute]
                    )

                else:
                    self.imap.user_mailbox_rename(
                        old_canon_attr,
                        entry_changes[result_attribute]
                    )

                entry[result_attribute] = entry_changes[result_attribute]
                cache.get_entry(self.domain, entry)
        elif result_attribute in entry:
            if not entry[result_attribute] == old_canon_attr:
                if old_canon_attr is None:
                    self.imap.user_mailbox_create(
                        entry[result_attribute]
                    )

                else:
                    self.imap.user_mailbox_rename(
                        old_canon_attr,
                        entry[result_attribute]
                    )

                cache.get_entry(self.domain, entry)
            else:
                if not self.imap.user_mailbox_exists(entry[result_attribute]):
                    self.imap.user_mailbox_create(
                        entry[result_attribute]
                    )

        self.user_quota(
            entry,
            "user%s%s" % (
                self.imap.get_separator(),
                entry[result_attribute]
            )
        )

        if conf.has_option(self.domain, 'sieve_mgmt'):
            sieve_mgmt_enabled = conf.get(self.domain, 'sieve_mgmt')
            if utils.true_or_false(sieve_mgmt_enabled):
                conf.plugins.exec_hook(
                    'sieve_mgmt_refresh',
                    kw={
                        'user': entry[result_attribute]
                    }
                )

    def _change_none_group(self, entry, change):
        """
            A group entry as part of the initial search result set.

            The Kolab daemon has little to do for this type of action on this
            type of entry.
        """
        pass

    def _change_none_None(self, entry, change):
        pass

    def _change_none_role(self, entry, change):
        """
            A role entry as part of the initial search result set.

            The Kolab daemon has little to do for this type of action on this
            type of entry.
        """
        pass

    def _change_none_sharedfolder(self, entry, change):
        """
            A sharedfolder entry as part of the initial search result set.
        """
        self.imap.connect(domain=self.domain)

        server = None
        mailserver_attribute = self.config_get('mailserver_attribute')

        if mailserver_attribute in entry:
            server = entry[mailserver_attribute]

        if 'kolabtargetfolder' not in entry:
            entry['kolabtargetfolder'] = self.get_entry_attribute(
                entry['id'],
                'kolabtargetfolder'
            )

        if 'kolabfoldertype' not in entry:
            entry['kolabfoldertype'] = self.get_entry_attribute(
                entry['id'],
                'kolabfoldertype'
            )

        folderacl_entry_attribute = conf.get('ldap', 'sharedfolder_acl_entry_attribute')
        if folderacl_entry_attribute is None:
            folderacl_entry_attribute = 'acl'

        if folderacl_entry_attribute not in entry:
            entry['kolabfolderaclentry'] = self.get_entry_attribute(
                entry['id'],
                folderacl_entry_attribute
            )
        else:
            entry['kolabfolderaclentry'] = entry[folderacl_entry_attribute]
            del entry[folderacl_entry_attribute]

        if 'kolabtargetfolder' in entry and entry['kolabtargetfolder'] is not None:

            folder_path = entry['kolabtargetfolder']
        else:
            # TODO: What is *the* way to see if we need to create an @domain
            # shared mailbox?
            # TODO^2: self.domain, really? Presumes any mail attribute is
            # set to the primary domain name space...
            # TODO^3: Test if the cn is already something@domain
            result_attribute = conf.get('cyrus-sasl', 'result_attribute')
            if result_attribute in ['mail']:
                folder_path = "%s@%s" % (entry['cn'], self.domain)
            else:
                folder_path = entry['cn']

        if not folder_path.startswith('shared/'):
            folder_path = "shared/%s" % folder_path

        if not self.imap.shared_folder_exists(folder_path):
            self.imap.shared_folder_create(folder_path, server)

        if 'kolabfoldertype' in entry and entry['kolabfoldertype'] is not None:

            self.imap.shared_folder_set_type(
                folder_path,
                entry['kolabfoldertype']
            )

        entry['kolabfolderaclentry'] = self._parse_acl(entry['kolabfolderaclentry'])

        self.imap._set_kolab_mailfolder_acls(
            entry['kolabfolderaclentry'], folder_path, True
        )

        delivery_address_attribute = self.config_get('sharedfolder_delivery_address_attribute')
        if delivery_address_attribute in entry and \
                entry[delivery_address_attribute] is not None:
            self.imap.set_acl(folder_path, 'anyone', '+p')

        # if server is None:
            # self.entry_set_attribute(mailserver_attribute, server)

    def _change_none_user(self, entry, change):
        """
            A user entry as part of the initial search result set.
        """
        mailserver_attribute = self.config_get('mailserver_attribute')
        if mailserver_attribute is None:
            mailserver_attribute = 'mailhost'

        mailserver_attribute = mailserver_attribute.lower()

        result_attribute = conf.get('cyrus-sasl', 'result_attribute')
        if result_attribute is None:
            result_attribute = 'mail'

        result_attribute = result_attribute.lower()

        old_canon_attr = None

        _entry = cache.get_entry(self.domain, entry, update=False)

        if _entry is not None and \
                'result_attribute' in _entry.__dict__ and \
                not _entry.result_attribute == '':

            old_canon_attr = _entry.result_attribute

        entry_changes = self.recipient_policy(entry)

        if result_attribute in entry and result_attribute in entry_changes:
            if not entry[result_attribute] == entry_changes[result_attribute]:
                old_canon_attr = entry[result_attribute]

        log.debug(
            _l("Result from recipient policy: %r") % (entry_changes),
            level=8
        )

        if result_attribute in entry_changes and old_canon_attr is not None:
            if not entry_changes[result_attribute] == old_canon_attr:
                self.imap.user_mailbox_rename(
                    old_canon_attr,
                    entry_changes[result_attribute]
                )

        for key in entry_changes.keys():
            entry[key] = entry_changes[key]
            self.set_entry_attribute(entry, key, entry[key])

        cache.get_entry(self.domain, entry)

        self.imap.connect(domain=self.domain)

        server = None

        if mailserver_attribute not in entry:
            entry[mailserver_attribute] = self.get_entry_attribute(entry, mailserver_attribute)

        if entry[mailserver_attribute] == "" or entry[mailserver_attribute] is None:
            server = None
        else:
            server = entry[mailserver_attribute].lower()

        if result_attribute in entry and entry[result_attribute] is not None:
            if not self.imap.user_mailbox_exists(entry[result_attribute]):
                folder = self.imap.user_mailbox_create(entry[result_attribute], server=server)
                server = self.imap.user_mailbox_server(folder)
            else:
                folder = "user%s%s" % (
                    self.imap.get_separator(),
                    entry[result_attribute]
                )

                server = self.imap.user_mailbox_server(folder)

            self.user_quota(entry, folder)

            mailserver_attr = self.config_get('mailserver_attribute')
            if mailserver_attr not in entry:
                self.set_entry_attribute(entry, mailserver_attr, server)
            else:
                if not entry[mailserver_attr] == server:
                    # TODO: Should actually transfer mailbox
                    self.set_entry_attribute(entry, mailserver_attr, server)

        else:
            log.warning(
                _l("Kolab user %s does not have a result attribute %r") % (
                    entry['id'],
                    result_attribute
                )
            )

    def _disconnect(self):
        del self.ldap
        del self.ldap_priv
        self.ldap = None
        self.ldap_priv = None
        self.bind = None

    def _domain_naming_context(self, domain):
        self._bind()

        # The list of naming contexts in the LDAP server
        attrs = self.get_entry_attributes("", ['namingContexts'])

        # Lower case of naming contexts - primarily for AD
        naming_contexts = utils.normalize(attrs['namingcontexts'])

        if isinstance(naming_contexts, string_types):
            naming_contexts = [naming_contexts]

        log.debug(
            _l("Naming contexts found: %r") % (naming_contexts),
            level=8
        )

        self._kolab_domain_root_dn(domain)

        log.debug(
            _l("Domains/Root DNs found: %r") % (
                self.domain_rootdns
            ),
            level=8
        )

        # If we have a 1:1 match, continue as planned
        for naming_context in naming_contexts:
            if self.domain_rootdns[domain].lower().endswith(naming_context):
                return naming_context

    def _primary_domain_for_naming_context(self, naming_context):
        self._bind()

        _domain = '.'.join(naming_context.split(',dc='))[3:]

        _naming_context = self._kolab_domain_root_dn(_domain)

        if naming_context == _naming_context:
            return _domain

    def _entry_dict(self, value):
        """
            Tests if 'value' is a valid entry dictionary with a DN contained
            within key 'dn'.

            Returns True or False
        """
        if isinstance(value, dict):
            if 'dn' in value:
                return True

        return False

    def _entry_dn(self, value):
        """
            Tests if 'value' is a valid DN.

            Returns True or False
        """

        # Only basestrings can be DNs
        if not isinstance(value, string_types):
            return False

        try:
            explode_dn(value)
        except ldap.DECODING_ERROR:
            # This is not a DN.
            return False

        return True

    def _entry_type(self, entry_id):
        """
            Return the type of object for an entry.
        """
        self._bind()

        entry_dn = self.entry_dn(entry_id)

        config_base_dn = self.config_get('base_dn')
        ldap_base_dn = self._kolab_domain_root_dn(self.domain)

        if ldap_base_dn is not None and not ldap_base_dn == config_base_dn:
            base_dn = ldap_base_dn
        else:
            base_dn = config_base_dn

        for _type in ['user', 'group', 'sharedfolder']:
            __filter = self.config_get('kolab_%s_filter' % (_type))
            if __filter is None:
                __filter = self.config_get('%s_filter' % (_type))

            if __filter is not None:
                try:
                    result = self._regular_search(entry_dn, filterstr=__filter)
                except Exception:
                    result = self._regular_search(
                        base_dn,
                        filterstr="(%s=%s)" % (
                            self.config_get('unique_attribute'),
                            entry_id['id']
                        )
                    )

                if not result:
                    continue
                else:
                    return _type

        return None

    def _find_user_dn(self, login, kolabuser=False):
        """
            Find the distinguished name (DN) for a (Kolab) user entry in LDAP.
        """

        conf_prefix = 'kolab_' if kolabuser else ''

        user_base_dn = self._object_base_dn('user', conf_prefix)

        auth_attrs = self.config_get_list('auth_attributes')

        auth_search_filter = ['(|']

        for auth_attr in auth_attrs:
            auth_search_filter.append('(%s=%s)' % (auth_attr, login))
            if '@' not in login:
                auth_search_filter.append(
                    '(%s=%s@%s)' % (
                        auth_attr,
                        login,
                        self.domain
                    )
                )

        auth_search_filter.append(')')

        auth_search_filter = ''.join(auth_search_filter)

        user_filter = self.config_get(conf_prefix + 'user_filter')

        search_filter = "(&%s%s)" % (
            auth_search_filter,
            user_filter
        )

        _results = self._search(
            user_base_dn,
            filterstr=search_filter,
            attrlist=['dn'],
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
                    attrlist=['dn']
                )

                if len(_results) == 1:
                    (_user_dn, _user_attrs) = _results[0]
                else:
                    # Overall fail
                    return False
            else:
                return False

        return _user_dn

    def _kolab_domain_root_dn(self, domain):
        log.debug(_l("Searching root dn for domain %r") % (domain), level=8)
        if not hasattr(self, 'domain_rootdns'):
            self.domain_rootdns = {}

        if domain in self.domain_rootdns:
            log.debug(_l("Returning from cache: %r") % (self.domain_rootdns[domain]), level=8)
            return self.domain_rootdns[domain]

        self._bind()

        log.debug(_l("Finding domain root dn for domain %s") % (domain), level=8)

        domain_base_dn = conf.get('ldap', 'domain_base_dn', quiet=True)
        domain_filter = conf.get('ldap', 'domain_filter')

        if domain_filter is not None:
            if domain is not None:
                domain_filter = domain_filter.replace('*', domain)

            if not domain_base_dn == "":

                _results = self._search(
                    domain_base_dn,
                    ldap.SCOPE_SUBTREE,
                    domain_filter,
                    override_search='_regular_search'
                )

                for _domain in _results:
                    (domain_dn, _domain_attrs) = _domain
                    domain_rootdn_attribute = conf.get(
                        'ldap',
                        'domain_rootdn_attribute'
                    )

                    _domain_attrs = utils.normalize(_domain_attrs)

                    if domain_rootdn_attribute in _domain_attrs:
                        log.debug(
                            _l("Setting domain root dn from LDAP for domain %r: %r") % (
                                domain,
                                _domain_attrs[domain_rootdn_attribute]
                            ),
                            level=8
                        )

                        self.domain_rootdns[domain] = _domain_attrs[domain_rootdn_attribute]
                        return _domain_attrs[domain_rootdn_attribute]

                    else:
                        domain_name_attribute = self.config_get('domain_name_attribute')
                        if domain_name_attribute is None:
                            domain_name_attribute = 'associateddomain'

                        if isinstance(_domain_attrs[domain_name_attribute], list):
                            domain = _domain_attrs[domain_name_attribute][0]
                        else:
                            domain = _domain_attrs[domain_name_attribute]

            else:
                if conf.has_option('ldap', 'base_dn'):
                    return conf.get('ldap', 'base_dn')

        self.domain_rootdns[domain] = utils.standard_root_dn(domain)

        return self.domain_rootdns[domain]

    def _kolab_filter(self):
        """
            Compose a filter using the relevant settings from configuration.
        """
        _filter = "(|"
        for _type in ['user', 'group', 'resource', 'sharedfolder']:
            __filter = self.config_get('kolab_%s_filter' % (_type))
            if __filter is None:
                __filter = self.config_get('%s_filter' % (_type))

            if __filter is not None:
                _filter = "%s%s" % (_filter, __filter)

        _filter = "%s)" % (_filter)

        return _filter

    def _list_domains(self, domain=None):
        """
            Find the domains related to this Kolab setup, and return a list of
            DNS domain names.

            Returns a list of tuples, each tuple containing the primary domain
            name and a list of secondary domain names.

            This function should only be called by the primary instance of Auth.
        """

        log.debug(_l("Listing domains..."), level=8)

        self.connect()
        self._bind()

        domain_base_dn = conf.get('ldap', 'domain_base_dn', quiet=True)

        if domain_base_dn == "":
            # No domains are to be found in LDAP, return an empty list.
            # Note that the Auth() base itself handles this case.
            return []

        # If we haven't returned already, let's continue searching
        domain_filter = conf.get('ldap', 'domain_filter')

        if domain is not None:
            domain_filter = domain_filter.replace('*', domain)

        if domain_base_dn is None or domain_filter is None:
            return []

        dna = self.config_get('domain_name_attribute')
        if dna is None:
            dna = 'associateddomain'

        try:
            _search = self._search(
                domain_base_dn,
                ldap.SCOPE_SUBTREE,
                domain_filter,
                # TODO: Where we use associateddomain is actually
                # configurable
                [dna],
                override_search='_regular_search'
            )

        except Exception:
            return []

        domains = []

        for domain_dn, domain_attrs in _search:
            primary_domain = None
            secondary_domains = []

            domain_attrs = utils.normalize(domain_attrs)

            # TODO: Where we use associateddomain is actually configurable
            if type(domain_attrs[dna]) == list:
                primary_domain = domain_attrs[dna].pop(0).lower()
                secondary_domains = [x.lower() for x in domain_attrs[dna]]
            else:
                primary_domain = domain_attrs[dna].lower()

            domains.append((primary_domain, secondary_domains))

        return domains

    def _object_base_dn(self, objectType, prefix=''):
        """
           Get configured base DN for specified Kolab object type
        """
        object_base_dn = self.config_get(prefix + objectType + '_base_dn')
        config_base_dn = self.config_get('base_dn')
        ldap_base_dn = self._kolab_domain_root_dn(self.domain)

        if ldap_base_dn is not None and not ldap_base_dn == config_base_dn:
            base_dn = ldap_base_dn
        else:
            base_dn = config_base_dn

        if object_base_dn is None:
            object_base_dn = base_dn
        else:
            object_base_dn = object_base_dn % ({'base_dn': base_dn})

        return object_base_dn

    def _synchronize_callback(self, *args, **kw):
        """
           Determine the characteristics of the callback being placed, and
           what data is contained within *args and **kw exactly.

           The exact form and shape of the feedback very much depends on the
           supportedControl used to even get the data.
        """

        log.debug(
            "auth.ldap.LDAP._synchronize_callback(args %r, kw %r)" % (
                args,
                kw
            ),
            level=8
        )

        # Typical for Persistent Change Control EntryChangeNotification
        if 'change_type' in kw:
            log.debug(
                _l(
                    "change_type defined, typical for Persistent Change "
                    + "Control EntryChangeNotification"
                ),
                level=5
            )

            change_dict = {
                'change_type': kw['change_type'],
                'previous_dn': kw['previous_dn'],
                'change_number': kw['change_number'],
                'dn': kw['dn']
            }

            entry = utils.normalize(kw['entry'])

            # Ignore nstombstone objects
            if 'objectclass' in entry:
                if 'nstombstone' in entry['objectclass']:
                    return None

            entry['dn'] = kw['dn']

            unique_attr = self.config_get('unique_attribute')
            entry['id'] = entry[unique_attr]

            try:
                entry['type'] = self._entry_type(entry)
            except Exception:
                entry['type'] = None

            log.debug(_l("Entry type: %s") % (entry['type']), level=8)

            if change_dict['change_type'] is None:
                # This entry was in the start result set
                eval("self._change_none_%s(entry, change_dict)" % (entry['type']))
            else:
                if isinstance(change_dict['change_type'], int):
                    change = psearch.CHANGE_TYPES_STR[change_dict['change_type']]
                    change = change.lower()
                else:
                    change = change_dict['change_type']

                # See if we can find the cache entry - this way we can get to
                # the value of a (former, on a deleted entry) result_attribute
                result_attribute = conf.get('cyrus-sasl', 'result_attribute')
                if result_attribute not in entry:
                    cache_entry = cache.get_entry(self.domain, entry, update=False)

                    if hasattr(cache_entry, 'result_attribute') and change == 'delete':
                        entry[result_attribute] = cache_entry.result_attribute

                eval(
                    "self._change_%s_%s(entry, change_dict)" % (
                        change,
                        entry['type']
                    )
                )

        # Typical for Paged Results Control
        elif 'entry' in kw and isinstance(kw['entry'], list):
            log.debug(_l("No change_type, typical for Paged Results Control"), level=5)

            for entry_dn, entry_attrs in kw['entry']:
                # This is a referral
                if entry_dn is None:
                    continue

                entry = {'dn': entry_dn}
                entry_attrs = utils.normalize(entry_attrs)
                for attr in entry_attrs.keys():
                    entry[attr.lower()] = entry_attrs[attr]

                # Ignore nstombstone objects
                if 'objectclass' in entry:
                    if 'nstombstone' in entry['objectclass']:
                        return None

                unique_attr = self.config_get('unique_attribute').lower()
                entry['id'] = entry[unique_attr]

                try:
                    entry['type'] = self._entry_type(entry)
                except Exception:
                    entry['type'] = "unknown"

                log.debug(_l("Entry type for dn: %s is: %s") % (entry['dn'], entry['type']), level=8)

                eval("self._change_none_%s(entry, None)" % (entry['type']))

#                result_attribute = conf.get('cyrus-sasl', 'result_attribute')
#
#                rcpt_addrs = self.recipient_policy(entry)
#
#                log.debug(_l("Recipient Addresses: %r") % (rcpt_addrs), level=8)
#
#                for key in rcpt_addrs.keys():
#                    entry[key] = rcpt_addrs[key]
#
#                cache.get_entry(self.domain, entry)
#
#                self.imap.connect(domain=self.domain)
#
#                if not self.imap.user_mailbox_exists(entry[result_attribute]):
#                    folder = self.imap.user_mailbox_create(
#                            entry[result_attribute]
#                        )
#
#                    server = self.imap.user_mailbox_server(folder)

    ###
    # Backend search functions
    ###

    def _persistent_search(
        self,
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

        psearch_server_controls = []

        psearch_server_controls.append(
            ldap.controls.psearch.PersistentSearchControl(
                criticality=True,
                changeTypes=['add', 'delete', 'modify', 'modDN'],
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
            res_type, res_data, res_msgid, _None, _None, _None = self.ldap.result4(
                _search,
                all=0,
                add_ctrls=1,
                add_intermediates=1,
                resp_ctrl_classes={ecnc.controlType: ecnc}
            )

            change_type = None
            previous_dn = None
            change_number = None

            for dn, entry, srv_ctrls in res_data:
                log.debug(_l("LDAP Search Result Data Entry:"), level=8)
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
                        _l("Entry Change Notification attributes:"),
                        level=8
                    )

                    log.debug(
                        "    " + _l("Change Type: %r (%r)") % (
                            change_type,
                            change_type_desc
                        ),
                        level=8
                    )

                    log.debug(
                        "    " + _l("Previous DN: %r") % (previous_dn),
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

    def _paged_search(
        self,
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
        _results = []

        server_page_control = ldap.controls.libldap.SimplePagedResultsControl(size=page_size,cookie='')

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

            except ldap.NO_SUCH_OBJECT:
                log.warning(
                    _l("Object %s searched no longer exists") % (base_dn)
                )

                break

            # Remove referrals
            _result_data = [_e for _e in _result_data if _e[0] is not None]

            if callback:
                callback(entry=_result_data)

            _results.extend(_result_data)
            if (pages % 2) == 0:
                log.debug(_l("%d results...") % (len(_results)))

            pctrls = [
                c for c in _result_controls
                if c.controlType == ldap.controls.libldap.SimplePagedResultsControl.controlType
            ]

            if pctrls:
                if hasattr(pctrls[0], 'size'):
                    size = pctrls[0].size
                    cookie = pctrls[0].cookie
                else:
                    size, cookie = pctrls[0].controlValue

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
                print("Warning:  Server ignores RFC 2696 control.")
                break

        return _results

    def _vlv_search(
        self,
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

    def _sync_repl(
        self,
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

        import ldapurl
        import syncrepl

        ldap_url = ldapurl.LDAPUrl(self.config_get('ldap_uri'))

        ldap_sync_conn = syncrepl.DNSync(
            '/var/lib/kolab/syncrepl_%s.db' % (self.domain),
            ldap_url.initializeUrl(),
            trace_level=2,
            trace_file=pykolab.logger.StderrToLogger(log),
            callback=self._synchronize_callback
        )

        bind_dn = self.config_get('bind_dn')
        bind_pw = self.config_get('bind_pw')

        ldap_sync_conn.simple_bind_s(bind_dn, bind_pw)

        msgid = ldap_sync_conn.syncrepl_search(
            base_dn,
            scope,
            mode='refreshAndPersist',
            filterstr=filterstr,
            attrlist=attrlist,
        )

        try:
            # Here's where returns need to be taken into account...
            while ldap_sync_conn.syncrepl_poll(all=1, msgid=msgid):
                pass
        except KeyboardInterrupt:
            pass

    def _regular_search(
        self,
        base_dn,
        scope=ldap.SCOPE_SUBTREE,
        filterstr="(objectClass=*)",
        attrlist=None,
        attrsonly=0,
        timeout=None,
        callback=False,
        primary_domain=None,
        secondary_domains=[]
    ):

        if timeout is None:
            timeout = float(self.config_get('ldap', 'timeout', default=10))

        log.debug(_l("Searching with filter %r") % (filterstr), level=8)

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

            if _result is not None:
                for result in _result:
                    _results.append(result)

        return _results

    def _search(
        self,
        base_dn,
        scope=ldap.SCOPE_SUBTREE,
        filterstr="(objectClass=*)",
        attrlist=None,
        attrsonly=0,
        timeout=None,
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

        if timeout is None:
            timeout = float(self.config_get('ldap', 'timeout', default=10))

        supported_controls = conf.get_list('ldap', 'supported_controls')

        if supported_controls is not None and not len(supported_controls) < 1:
            for control_num in [(int)(x) for x in supported_controls]:
                self.ldap.supported_controls.append(
                    SUPPORTED_LDAP_CONTROLS[control_num]['func']
                )

        if len(self.ldap.supported_controls) < 1:
            for control_num in SUPPORTED_LDAP_CONTROLS.keys():
                log.debug(
                    _l("Checking for support for %s on %s") % (
                        SUPPORTED_LDAP_CONTROLS[control_num]['desc'],
                        self.domain
                    ),
                    level=8
                )

            _search = self.ldap.search_s(
                '',
                scope=ldap.SCOPE_BASE,
                attrlist=['supportedControl']
            )

            for (_result, _supported_controls) in _search:
                supported_controls = _supported_controls.values()[0]
                for control_num in SUPPORTED_LDAP_CONTROLS.keys():
                    if SUPPORTED_LDAP_CONTROLS[control_num]['oid'] in \
                            supported_controls:

                        log.debug(
                            _l("Found support for %s") % (
                                SUPPORTED_LDAP_CONTROLS[control_num]['desc'],
                            ),
                            level=8
                        )

                        self.ldap.supported_controls.append(
                            SUPPORTED_LDAP_CONTROLS[control_num]['func']
                        )

        _results = []

        if override_search is not False:
            _use_ldap_controls = [override_search]
        else:
            _use_ldap_controls = self.ldap.supported_controls

        for supported_control in _use_ldap_controls:
            # Repeat the same supported control until
            # a failure (Exception) occurs that been
            # recognized as not an error related to the
            # supported control (such as ldap.SERVER_DOWN).
            failed_ok = False

            while not failed_ok:
                try:
                    exec(
                        """_results = self.%s(
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

                    break

                except ldap.SERVER_DOWN as errmsg:
                    log.error(_l("LDAP server unavailable: %r") % (errmsg))
                    log.error(_l("%s") % (traceback.format_exc()))
                    log.error(_l("-- reconnecting in 10 seconds."))

                    self._disconnect()

                    time.sleep(10)
                    self.reconnect()

                except ldap.TIMEOUT:
                    log.error(_l("LDAP timeout in searching for '%s'") % (filterstr))

                    self._disconnect()

                    time.sleep(10)
                    self.reconnect()

                except Exception as errmsg:
                    failed_ok = True

                    log.error(_l("An error occured using %s: %r") % (supported_control, errmsg))
                    log.error(_l("%s") % (traceback.format_exc()))

                    continue

        return _results

    def _parse_acl(self, acl):
        """
            Parse LDAP ACL specification for use in IMAP
        """

        results = []

        if acl is not None:
            if not isinstance(acl, list):
                acl = [acl]

            for acl_entry in acl:
                # entry already converted to IMAP format?
                if acl_entry[0] == "(":
                    results.append(acl_entry)
                    continue

                acl_access = acl_entry.split()[-1]
                acl_subject = acl_entry.split(', ')

                if len(acl_subject) > 1:
                    acl_subject = ', '.join(acl_subject[:-1])
                else:
                    acl_subject = acl_entry.split()[0]

                results.append("(%r, %r)" % (acl_subject, acl_access))

        return results
