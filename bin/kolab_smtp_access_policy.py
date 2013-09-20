#!/usr/bin/python
#
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3 or, at your option, any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Library General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place - Suite 330, Boston, MA 02111-1307, USA.
#

import datetime
import os
import sys
import time

from optparse import OptionParser
from ConfigParser import SafeConfigParser

cache = None

import sqlalchemy
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table

from sqlalchemy import create_engine
from sqlalchemy.orm import mapper
try:
    from sqlalchemy.orm import sessionmaker
except:
    from sqlalchemy.orm import create_session

from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint

sys.path = ['..','.'] + sys.path

import pykolab

from pykolab import utils
from pykolab.auth import Auth
from pykolab.constants import *
from pykolab.translate import _

# TODO: Figure out how to make our logger do some syslogging as well.
log = pykolab.getLogger('pykolab.smtp_access_policy')

# TODO: Removing the stdout handler would mean one can no longer test by
# means of manual execution in debug mode.
#log.remove_stdout_handler()

conf = pykolab.getConf()

mydomains = None

#
# Caching routines using SQLAlchemy.
#
# If creating the cache fails, we continue without any caching, significantly
# increasing the load on LDAP.
#
cache_expire = 86400
try:
    metadata = MetaData()
except:
    cache = False

session = None
policy_result_table = Table(
        'policy_result', metadata,
        Column('id', Integer, primary_key=True),
        Column('key', String(16), nullable=False),
        Column('value', Boolean, nullable=False),
        Column('sender', String(64), nullable=False),
        Column('recipient', String(64), nullable=False),
        Column('sasl_username', String(64)),
        Column('sasl_sender', String(64)),
        Column('created', Integer, nullable=False),
    )

Index(
        'fsrss',
        policy_result_table.c.key,
        policy_result_table.c.sender,
        policy_result_table.c.recipient,
        policy_result_table.c.sasl_username,
        policy_result_table.c.sasl_sender,
        unique=True
    )

class PolicyResult(object):
    def __init__(
            self,
            key=None,
            value=None,
            sender=None,
            recipient=None,
            sasl_username=None,
            sasl_sender=None
        ):

        self.key = key
        self.value = value
        self.sender = sender
        self.sasl_username = sasl_username
        self.sasl_sender = sasl_sender
        self.recipient = recipient
        self.created = (int)(time.time())

mapper(PolicyResult, policy_result_table)

statistic_table = Table(
        'statistic', metadata,
        Column('id', Integer, primary_key=True),
        Column('sender', String(64), nullable=False),
        Column('recipient', String(64), nullable=False),
        Column('date', Date, nullable=False),
        Column('count', Integer, nullable=False),
    )

Index(
        'srd',
        statistic_table.c.sender,
        statistic_table.c.recipient,
        statistic_table.c.date,
        unique=True
    )

class Statistic(object):
    def __init__(self, sender, recipient, date=datetime.date.today(), count=0):
        self.sender = sender
        self.recipient = recipient
        self.date = date
        self.count = count

mapper(Statistic, statistic_table)

class PolicyRequest(object):
    email_address_keys = [ 'sender', 'recipient' ]
    recipients = []

    auth = None

    sasl_domain = None
    sasl_user = None
    sender_domain = None
    sender_user = None

    sasl_user_uses_alias = False
    sasl_user_is_delegate = False

    def __init__(self, policy_request={}):
        """
            Creates a new policy request object. Pass it a policy_request
            dictionary as described in the Postfix documentation on:

                http://www.postfix.org/SMTPD_POLICY_README.html
        """
        for key in policy_request.keys():

            # Normalize email addresses (they may contain recipient delimiters)
            if key in self.email_address_keys:
                policy_request[key] = normalize_address(policy_request[key])

            if not key == 'recipient':
                if policy_request[key] == '':
                    setattr(self, key, None)
                else:
                    setattr(self, key, policy_request[key])

            else:
                if not policy_request['recipient'].strip() == '':
                    self.recipients = list(set(self.recipients + [policy_request['recipient']]))

    def add_request(self, policy_request={}):
        """
            Add subsequent policy requests to the existing policy request.

            All data in the request should be the same as the initial policy
            request, but for the recipient - with destination limits set over
            1, Postfix may attempt to deliver messages to more then one
            recipient during a single delivery attempt, and during submission,
            the policy will receive one policy request per recipient.
        """

        # Check instance. Not sure what to do if the instance is not the same.
        if hasattr(self, 'instance'):
            if not policy_request['instance'] == self.instance:
                # TODO: We need to empty our pockets
                pass

        log.debug(
                _("Adding policy request to instance %s") % (self.instance),
                level=8
            )

        # Normalize email addresses (they may contain recipient delimiters)
        if policy_request.has_key('recipient'):
            policy_request['recipient'] = normalize_address(
                    policy_request['recipient']
                )

            if not policy_request['recipient'].strip() == '':
                self.recipients = list(set(self.recipients + [policy_request['recipient']]))

    def parse_ldap_dn(self, dn):
        """
            See if parameter 'dn' is a basestring LDAP dn, and if so, return
            the results we can obtain from said DN. Return a list of relevant
            attribute values.

            If not a DN, return None.
        """
        values = []

        try:
            import ldap.dn

            ldap_dn = ldap.dn.explode_dn(dn)

        except ldap.DECODING_ERROR:
            # This is not a DN.
            return None

        if len(ldap_dn) > 0:
            search_attrs = conf.get_list(
                    'kolab_smtp_access_policy',
                    'address_search_attrs'
                )

            rule_subject = self.auth.get_user_attributes(
                    self.sasl_domain,
                    { 'dn': dn },
                    search_attrs + [ 'objectclass' ]
                )

            for search_attr in search_attrs:
                if rule_subject.has_key(search_attr):
                    if isinstance(rule_subject[search_attr], basestring):
                        values.append(rule_subject[search_attr])
                    else:
                        values.extend(rule_subject[search_attr])

            return values

        else:
            # ldap.dn.explode_dn didn't error out, but it also didn't split
            # the DN properly.
            return None

    def parse_ldap_uri(self, uri):
        values = []

        parsed_uri = utils.parse_ldap_uri(uri)

        if parsed_uri == None:
            return None

        (_protocol, _server, _port, _base_dn, _attrs, _scope, _filter) = \
                parsed_uri

        if len(_attrs) == 0:
            search_attrs = conf.get_list(
                    'kolab_smtp_access_policy',
                    'address_search_attrs'
                )
        else:
            search_attrs = [ _attrs ]

        users = []

        self.auth._auth._bind()
        _users = self.auth._auth._search(
                _base_dn,
                scope=LDAP_SCOPE[_scope],
                filterstr=_filter,
                attrlist=search_attrs + [ 'objectclass' ],
                override_search="_regular_search"
            )

        for _user in _users:
            for search_attr in search_attrs:
                values.extend(_user[1][search_attr])

        return values

    def parse_policy(self, _subject, _object, policy):
        """
            Parse policy to apply on _subject, for object _object.

            The policy is a list of rules.

            The _subject is a sender for kolabAllowSMTPRecipient checks, and
            a recipient for kolabAllowSMTPSender checks.

            The _object is a recipient for kolabAllowSMTPRecipient checks, and
            a sender for kolabAllowSMTPSender checks.
        """

        special_rule_values = {
            '$mydomains': expand_mydomains
        }

        rules = { 'allow': [], 'deny': [] }

        if isinstance(policy, basestring):
            policy = [policy]

        for rule in policy:
            # Find rules that are actually special values, simply by
            # mapping the rule onto a key in "special_rule_values", a
            # dictionary with the corresponding value set to a function to
            # execute.
            if rule in special_rule_values.keys():
                special_rules = special_rule_values[rule]()
                if rule.startswith("-"):
                    rules['deny'].extend(special_rules)
                else:
                    rules['allow'].extend(special_rules)

                continue

            # Lower-case the rule
            rule = rule.lower()

            # Also note the '-' cannot be passed on to the functions that
            # follow, so store the rule separately from the prefix that is
            # prepended to deny rules.
            if rule.startswith("-"):
                _prefix = '-'
                _rule = rule[1:]
            else:
                _prefix = ''
                _rule = rule

            # See if the value is an LDAP DN
            ldap_dn = self.parse_ldap_dn(_rule)

            if not ldap_dn == None and len(ldap_dn) > 0:
                if _prefix == '-':
                    rules['deny'].extend(ldap_dn)
                else:
                    rules['allow'].extend(ldap_dn)
            else:
                ldap_uri = self.parse_ldap_uri(_rule)

                if not ldap_uri == None and len(ldap_uri) > 0:
                    if _prefix == '-':
                        rules['deny'].extend(ldap_uri)
                    else:
                        rules['allow'].extend(ldap_uri)

                else:
                    if rule.startswith("-"):
                        rules['deny'].append(rule[1:])
                    else:
                        rules['allow'].append(rule)

        allowed = False
        for rule in rules['allow']:
            deny_override = False

            if _object.endswith(rule):
                for deny_rule in rules['deny']:
                    if deny_rule.endswith(rule):
                        deny_override = True

                if not deny_override:
                    allowed = True

        denied = False

        for rule in rules['deny']:
            allow_override = False
            if _object.endswith(rule):
                if not allowed:
                    denied = True
                    continue
                else:
                    for allow_rule in rules['allow']:
                        if allow_rule.endswith(rule):
                            allow_override = True

                    if not allow_override:
                        denied = True

        if not denied:
            allowed = True

        return allowed

    def verify_alias(self):
        """
            Verify whether the user authenticated for this policy request is
            using an alias of its primary authentication ID / attribute.

            John.Doe@example.org (mail) for example could be sending with
            envelope sender jdoe@example.org (mailAlternateAddress, alias).
        """

        search_attrs = conf.get_list(self.sasl_domain, 'address_search_attrs')

        if search_attrs == None or \
                (isinstance(search_attrs, list) and len(search_attrs) == 0):

            search_attrs = conf.get_list(self.sasl_domain, 'mail_attributes')

        if search_attrs == None or \
                (isinstance(search_attrs, list) and len(search_attrs) == 0):

            search_attrs = conf.get_list(
                    'kolab_smtp_access_policy',
                    'address_search_attrs'
                )

        if search_attrs == None or \
                (isinstance(search_attrs, list) and len(search_attrs) == 0):


            search_attrs = conf.get_list(
                    conf.get('kolab', 'auth_mechanism'),
                    'mail_attributes'
                )

        want_attrs = []

        for search_attr in search_attrs:
            if not self.sasl_user.has_key(search_attr):
                want_attrs.append(search_attr)

        if len(want_attrs) > 0:
            self.sasl_user.update(
                    self.auth.get_user_attributes(
                            self.sasl_domain,
                            self.sasl_user,
                            want_attrs
                        )
                )

        # Catch a user using one of its own alias addresses.
        for search_attr in search_attrs:
            if self.sasl_user.has_key(search_attr):
                if isinstance(self.sasl_user[search_attr], list):
                    if self.sender.lower() in [x.lower() for x in self.sasl_user[search_attr]]:
                        return True
                elif self.sasl_user[search_attr].lower() == self.sender.lower():
                    return True

        return False

    def verify_authenticity(self):
        """
            Verify that the SASL username or lack thereof corresponds with
            allowing or disallowing authenticated users.

            If an SASL username is supplied, use it to obtain the authentication
            database user object including all attributes we may find ourselves
            interested in.
        """

        if self.sasl_username == None:
            if not conf.allow_unauthenticated:
                reject(_("Unauthorized access not allowed"))
            else:
                # If unauthenticated is allowed, I have nothing to do here.
                return True

        sasl_username = self.sasl_username

        # If we have an sasl_username, find the user object in the
        # authentication database, along with the attributes we are
        # interested in.
        if self.sasl_domain == None:
            if len(self.sasl_username.split('@')) > 1:
                self.sasl_domain = self.sasl_username.split('@')[1]
            else:
                self.sasl_domain = conf.get('kolab', 'primary_domain')
                sasl_username = "%s@%s" % (self.sasl_username, self.sasl_domain)

        if self.auth == None:
            self.auth = Auth(self.sasl_domain)
        elif not self.auth.domain == self.sasl_domain:
            self.auth = Auth(self.sasl_domain)

        sasl_users = self.auth.find_recipient(
                sasl_username,
                domain=self.sasl_domain
            )

        if isinstance(sasl_users, list):
            if len(sasl_users) == 0:
                log.error(_("Could not find recipient"))
                return False
            else:
                self.sasl_user = { 'dn': sasl_users[0] }
        elif isinstance(sasl_users, basestring):
            self.sasl_user = { 'dn': sasl_users }

        if not self.sasl_user['dn']:
            # Got a final answer here, do the caching thing.
            cache_update(
                    function='verify_sender',
                    sender=self.sender,
                    recipients=self.recipients,
                    result=(int)(False),
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender
                )

            reject(
                    _("Could not find envelope sender user %s (511)") % (
                            self.sasl_username
                        )
                )

        attrs = conf.get_list(self.sasl_domain, 'auth_attributes')

        if attrs == None or (isinstance(attrs, list) and len(attrs) == 0):
            attrs = conf.get_list(
                    conf.get('kolab', 'auth_mechanism'),
                    'auth_attributes'
                )

        mail_attrs = conf.get_list(self.sasl_domain, 'mail_attributes')
        if mail_attrs == None or \
                (isinstance(mail_attrs, list) and len(mail_attrs) == 0):

            mail_attrs = conf.get_list(
                    conf.get('kolab', 'auth_mechanism'),
                    'mail_attributes'
                )

        if not mail_attrs == None:
            attrs.extend(mail_attrs)

        attrs.extend(
                [
                        'kolabAllowSMTPRecipient',
                        'kolabAllowSMTPSender'
                    ]
            )

        attrs = list(set(attrs))

        user_attrs = self.auth.get_user_attributes(
                self.sasl_domain,
                self.sasl_user,
                attrs
            )

        user_attrs['dn'] = self.sasl_user['dn']
        self.sasl_user = utils.normalize(user_attrs)
        log.debug(
                _("Obtained authenticated user details for %r: %r") % (
                        self.sasl_user['dn'],
                        self.sasl_user.keys()
                    ),
                level=8
            )

    def verify_delegate(self):
        """
            Verify whether the authenticated user is a delegate of the envelope
            sender.
        """

        if self.sender_domain == None:
            if len(self.sender.split('@')) > 1:
                self.sender_domain = self.sender.split('@')[1]
            else:
                self.sender_domain = conf.get('kolab', 'primary_domain')

        if self.sender == self.sasl_username:
            return True

        search_attrs = conf.get_list(self.sender_domain, 'mail_attributes')
        if search_attrs == None:
            search_attrs = conf.get_list(
                    conf.get('kolab', 'auth_mechanism'),
                    'mail_attributes'
                )

        sender_users = self.auth.find_recipient(
                self.sender,
                domain=self.sender_domain
            )

        if isinstance(sender_users, list):
            if len(sender_users) > 1:
                # More then one sender user with this recipient address.
                # TODO: check each of the sender users found.
                self.sender_user = { 'dn': sender_users[0] }
            elif len(sender_users) == 1:
                self.sender_user = { 'dn': sender_users }
            else:
                self.sender_user = { 'dn': False }

        elif isinstance(sender_users, basestring):
            self.sender_user = { 'dn': sender_users }

        if not self.sender_user['dn']:
            cache_update(
                    function='verify_sender',
                    sender=self.sender,
                    recipients=self.recipients,
                    result=(int)(False),
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender
                )

            reject(_("Could not find envelope sender user %s") % (self.sender))

        attrs = search_attrs
        attrs.extend(
                [
                        'kolabAllowSMTPRecipient',
                        'kolabAllowSMTPSender',
                        'kolabDelegate'
                    ]
            )

        user_attrs = self.auth.get_user_attributes(
                self.sender_domain,
                self.sender_user,
                attrs
            )

        user_attrs['dn'] = self.sender_user['dn']
        self.sender_user = utils.normalize(user_attrs)

        if not self.sender_user.has_key('kolabdelegate'):
            reject(
                    _("%s is unauthorized to send on behalf of %s") % (
                            self.sasl_user['dn'],
                            self.sender_user['dn']
                        )
                )

        elif self.sender_user['kolabdelegate'] == None:
            # No delegates for this sender could be found. The user is
            # definitely NOT a delegate of the sender.
            log.warning(
                _("User %s attempted to use envelope sender address %s without authorization") % (
                            policy_request["sasl_username"],
                            policy_request["sender"]
                        )
                )

            # Got a final answer here, do the caching thing.
            if not cache == False:
                record_id = cache_update(
                        function='verify_sender',
                        sender=self.sender,
                        recipients=self.recipients,
                        result=(int)(False),
                        sasl_username=self.sasl_username,
                        sasl_sender=self.sasl_sender
                    )

            sender_is_delegate = False

        else:
            # See if we can match the value of the envelope sender delegates to
            # the actual sender sasl_username
            if self.sasl_user == None:
                sasl_users = self.auth.find_recipient(
                        self.sasl_username,
                        domain=self.sasl_domain
                    )

                if isinstance(sasl_users, list):
                    if len(sasl_users) == 0:
                        log.error(_("Could not find recipient"))
                        return False
                    else:
                        self.sasl_user = { 'dn': sasl_users[0] }
                elif isinstance(sasl_users, basestring):
                    self.sasl_user = { 'dn': sasl_users }

            # Possible values for the kolabDelegate attribute are:
            # a 'uid', a 'dn'.
            if not self.sasl_user.has_key('uid'):
                self.sasl_user['uid'] = self.auth.get_user_attribute(
                        self.sasl_domain,
                        self.sasl_user,
                        'uid'
                    )

            sender_delegates = self.sender_user['kolabdelegate']

            if not type(sender_delegates) == list:
                sender_delegates = [ sender_delegates ]

            for sender_delegate in sender_delegates:
                if self.sasl_user['dn'] == sender_delegate:
                    log.debug(
                            _("Found user %s to be a delegate user of %s") % (
                                    policy_request["sasl_username"],
                                    policy_request["sender"]
                                ),
                            level=8
                        )

                    sender_is_delegate = True

                elif self.sasl_user['uid'] == sender_delegate:
                    log.debug(
                            _("Found user %s to be a delegate user of %s") % (
                                    policy_request["sasl_username"],
                                    policy_request["sender"]
                                ),
                            level=8
                        )

                    sender_is_delegate = True

            # If nothing matches sender_is_delegate is still None.
            if not sender_is_delegate == True:
                sender_is_delegate = False

        return sender_is_delegate

    def verify_recipient(self, recipient):
        """
            Verify whether the sender is allowed send to this recipient, using
            the recipient's kolabAllowSMTPSender.
        """

        self.recipient = recipient

        if not self.sasl_username == '' and not self.sasl_username == None:
            log.debug(_("Verifying authenticated sender '%(sender)s' with sasl_username '%(sasl_username)s' for recipient '%(recipient)s'") % (self.__dict__)
                )
        else:
            log.debug(_("Verifying unauthenticated sender '%(sender)s' for recipient '%(recipient)s'") % (self.__dict__)
                )

        recipient_verified = False

        if not cache == False:
            records = cache_select(
                    function='verify_recipient',
                    sender=self.sender,
                    recipient=recipient,
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender,
                )

            if not records == None and len(records) == 1:
                log.info(
                        _("Reproducing verify_recipient(%s, %s) from cache") % (
                                self.sender,
                                recipient
                            )
                    )

                return records[0].value

        # TODO: Under some conditions, the recipient may not be fully qualified.
        # We'll cross that bridge when we get there, though.
        if len(recipient.split('@')) > 1:
            sasl_domain = recipient.split('@')[1]
        else:
            sasl_domain = conf.get('kolab', 'primary_domain')
            recipient = "%s@%s" % (recipient,sasl_domain)

        if not verify_domain(sasl_domain):
            if not cache == False:
                cache_update(
                        function='verify_recipient',
                        sender=self.sender,
                        recipient=recipient,
                        result=(int)(True),
                        sasl_username=self.sasl_username,
                        sasl_sender=self.sasl_sender
                    )

            return True

        if self.auth == None:
            self.auth = Auth(sasl_domain)
        elif not self.auth.domain == sasl_domain:
            self.auth = Auth(sasl_domain)

        if verify_domain(sasl_domain):
            if self.auth.secondary_domains.has_key(sasl_domain):
                log.debug(
                        _("Using authentication domain %s instead of %s") % (
                                self.auth.secondary_domains[sasl_domain],
                                sasl_domain
                            ),
                        level=8
                    )

                sasl_domain = self.auth.secondary_domains[sasl_domain]
            else:
                log.debug(
                        _("Domain %s is a primary domain") % (
                                sasl_domain
                        ),
                        level=8
                    )

        else:
            log.warning(
                    _("Checking the recipient for domain %s that is not ours. This is probably a configuration error.") % (
                            sasl_domain
                        )
                )

            return True

        recipients = self.auth.find_recipient(
                normalize_address(recipient),
                domain=sasl_domain,
            )

        if isinstance(recipients, list):
            if len(recipients) > 1:
                log.info(
                        _("This recipient address is related to multiple object entries and the SMTP Access Policy can therefore not restrict message flow")
                    )

                cache_update(
                        function='verify_recipient',
                        sender=self.sender,
                        recipient=normalize_address(recipient),
                        result=(int)(True),
                        sasl_username=self.sasl_username,
                        sasl_sender=self.sasl_sender
                    )

                return True
            elif len(recipients) == 1:
                _recipient = { 'dn': recipients[0] }
            else:
                log.debug(
                        _("Recipient address %r not found. Allowing since the MTA was configured to accept the recipient.") % (
                                normalize_address(recipient)
                            ),
                        level=3
                    )

                cache_update(
                        function='verify_recipient',
                        sender=self.sender,
                        recipient=normalize_address(recipient),
                        result=(int)(True),
                        sasl_username=self.sasl_username,
                        sasl_sender=self.sasl_sender
                    )

                return True

        elif isinstance(recipients, basestring):
            _recipient = {
                    'dn': recipients
                }

        # We have gotten an invalid recipient. We need to catch this case,
        # because testing can input invalid recipients, and so can faulty
        # applications, or misconfigured servers.
        if not _recipient['dn']:
            if not conf.allow_unauthenticated:
                cache_update(
                        function='verify_recipient',
                        sender=self.sender,
                        recipient=normalize_address(recipient),
                        result=(int)(False),
                        sasl_username=self.sasl_username,
                        sasl_sender=self.sasl_sender
                    )

                reject(_("Invalid recipient"))
            else:
                cache_update(
                        function='verify_recipient',
                        sender=self.sender,
                        recipient=normalize_address(recipient),
                        result=(int)(True),
                        sasl_username=self.sasl_username,
                        sasl_sender=self.sasl_sender
                    )

                log.debug(_("Could not find this user, accepting"), level=8)
                return True

        if not _recipient['dn'] == False:
            recipient_policy = self.auth.get_entry_attribute(
                    sasl_domain,
                    _recipient['dn'],
                    'kolabAllowSMTPSender'
                )

        # If no such attribute has been specified, allow
        if recipient_policy == None:
            cache_update(
                    function='verify_recipient',
                    sender=self.sender,
                    recipient=normalize_address(recipient),
                    result=(int)(True),
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender
                )

            recipient_verified = True

        # Otherwise, parse the policy obtained with the subject of the policy
        # being the recipient, and the object to apply the policy to being the
        # sender.
        else:
            recipient_verified = self.parse_policy(
                    recipient,
                    self.sender,
                    recipient_policy
                )

            cache_update(
                    function='verify_recipient',
                    sender=self.sender,
                    recipient=normalize_address(recipient),
                    result=(int)(recipient_verified),
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender
                )

        return recipient_verified

    def verify_recipients(self):
        """
            Verify whether the sender is allowed send to the recipients in this
            policy request, using each recipient's kolabAllowSMTPSender.

            Note there may be multiple recipients in this policy request, and
            therefor self.recipients is a list - walk through that list.
        """

        recipients_verified = True

        if not cache == False:
            records = cache_select(
                    function='verify_recipient',
                    sender=self.sender,
                    recipients=self.recipients,
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender,
                )

            if not records == None and len(records) == len(self.recipients):
                log.debug("Euh, what am I doing here?")
                for record in records:
                    recipient_found = False
                    for recipient in self.recipients:
                        if recipient == record.recipient:
                            recipient_found = True

                    if not recipient_found:
                        reject(_("Sender %s is not allowed to send to recipient %s") % (self.sender,recipient))

        for recipient in self.recipients:
            recipient_verified = self.verify_recipient(recipient)
            if not recipient_verified:
                recipients_verified = False

        return recipients_verified

    def verify_sender(self):
        """
            Verify the sender's access policy.

            1) Verify whether the sasl_username is allowed to send using the
            envelope sender address, with the kolabDelegate attribute
            associated with the LDAP object that has the envelope sender
            address.

            2) Verify whether the sender is allowed to send to recipient(s)
            listed on the sender's object.

            A third potential action could be to check the recipient object to
            see if the sender is allowed to send to the recipient by the
            recipient's kolabAllowSMTPSender, but this is done in
            verify_recipients().
        """

        sender_verified = False

        if not cache == False:
            records = cache_select(
                    sender=self.sender,
                    recipients=self.recipients,
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender,
                    function='verify_sender'
                )

            if not records == None and len(records) == len(self.recipients):
                log.info(_("Reproducing verify_sender(%r) from cache") % (
                                self.__dict__
                            )
                    )

                for record in records:
                    recipient_found = False
                    for recipient in self.recipients:
                        if recipient == record.recipient:
                            recipient_found = True

                    if recipient_found and not record.value:
                        reject(_("Sender %s is not allowed to send to recipient %s") % (self.sender,recipient))

                return True

        self.verify_authenticity()
        self.sasl_user_uses_alias = self.verify_alias()


        if not self.sasl_user_uses_alias:
            log.debug(_("Sender is not using an alias"), level=8)
            self.sasl_user_is_delegate = self.verify_delegate()

        # If the authenticated user is using delegate functionality, apply the
        # recipient policy attribute for the envelope sender.
        if self.sasl_user_is_delegate == False and \
            self.sasl_user_uses_alias == False:

            reject(_("Sender uses unauthorized envelope sender address"))

        elif self.sasl_user_is_delegate:
            # Apply the recipient policy for the sender using the envelope
            # sender user object.
            recipient_policy_domain = self.sender_domain
            recipient_policy_sender = self.sender
            recipient_policy_user = self.sender_user

        elif not self.sasl_user == None:
            # Apply the recipient policy from the authenticated user.
            recipient_policy_domain = self.sasl_domain
            recipient_policy_sender = self.sasl_username
            recipient_policy_user = self.sasl_user

        else:
            if not conf.allow_unauthenticated:
                reject(_("Could not verify sender"))
            else:
                recipient_policy_domain = self.sender_domain
                recipient_policy_sender = self.sender
                recipient_policy_user = self.sender_user

        log.debug(
                _("Verifying whether sender is allowed to send to recipient using sender policy"),
                level=8
            )

        if recipient_policy_user.has_key('kolaballowsmtprecipient'):
            recipient_policy = recipient_policy_user['kolaballowsmtprecipient']
        else:
            recipient_policy = self.auth.get_user_attribute(
                    recipient_policy_domain,
                    recipient_policy_user,
                    'kolabAllowSMTPRecipient'
                )

        log.debug(_("Result is %r") % (recipient_policy), level=8)

        # If no such attribute has been specified, allow
        if recipient_policy == None:
            log.debug(
                    _("No recipient policy restrictions exist for this sender"),
                    level=8
                )

            sender_verified = True

        # Otherwise,parse the policy obtained.
        else:
            log.debug(
                    _("Found a recipient policy to apply for this sender."),
                    level=8
                )

            recipient_allowed = None

            for recipient in self.recipients:
                recipient_allowed = self.parse_policy(
                        recipient_policy_sender,
                        recipient,
                        recipient_policy
                    )

                if not recipient_allowed:
                    reject(
                            _("Sender %s not allowed to send to recipient %s") % (recipient_policy_user['dn'],recipient)
                        )

            sender_verified = True

        if not cache == False:
            record_id = cache_update(
                    function='verify_sender',
                    sender=self.sender,
                    recipients=self.recipients,
                    result=(int)(sender_verified),
                    sasl_username=self.sasl_username,
                    sasl_sender=self.sasl_sender
                )

        return sender_verified

def cache_cleanup():
    if not cache == True:
        return

    log.debug(_("Cleaning up the cache"), level=8)
    session.query(
            PolicyResult
        ).filter(
                PolicyResult.created < ((int)(time.time()) - cache_expire)
            ).delete()

def cache_init():
    global cache, cache_expire, session

    if conf.has_section('kolab_smtp_access_policy'):
        if conf.has_option('kolab_smtp_access_policy', 'cache_uri'):
            cache_uri = conf.get('kolab_smtp_access_policy', 'cache_uri')
            cache = True
            if conf.has_option('kolab_smtp_access_policy', 'retention'):
                cache_expire = (int)(
                        conf.get(
                                'kolab_smtp_access_policy',
                                'retention'
                            )
                    )
        elif conf.has_option('kolab_smtp_access_policy', 'uri'):
            log.warning(_("The 'uri' setting in the kolab_smtp_access_policy section is soon going to be deprecated in favor of 'cache_uri'"))
            cache_uri = conf.get('kolab_smtp_access_policy', 'uri')
            cache = True
        else:
            return False
    else:
        return False

    if conf.debuglevel > 8:
        engine = create_engine(cache_uri, echo=True)
    else:
        engine = create_engine(cache_uri, echo=False)

    try:
        metadata.create_all(engine)
    except sqlalchemy.exc.OperationalError, e:
        log.error(_("Operational Error in caching: %s" % (e)))
        return False

    Session = sessionmaker(bind=engine)
    session = Session()
    cache_cleanup()

    return cache

def cache_select(
        function,
        sender,
        recipient='',
        recipients=[],
        sasl_username='',
        sasl_sender=''
    ):

    if not cache == True:
        return None

    if not recipient == '' and recipients == []:
        recipients = [recipient]

    return session.query(
            PolicyResult
        ).filter_by(
                key=function,
                sender=sender,
                sasl_username=sasl_username,
                sasl_sender=sasl_sender
            ).filter(
                    PolicyResult.recipient.in_(recipients)
                ).filter(
                        PolicyResult.created >= \
                            ((int)(time.time()) - cache_expire)
                    ).all()

def cache_insert(
        function,
        sender,
        recipient='',
        recipients=[],
        result=None,
        sasl_username='',
        sasl_sender=''
    ):

    if not cache == True:
        return []

    log.debug(
            _("Caching the policy result with timestamp %d") % (
                    (int)(time.time())
                ),
            level=8
        )

    cache_cleanup()

    if not recipient == '':
        recipients.append(recipient)

    for recipient in recipients:
        session.add(
                PolicyResult(
                        key=function,
                        value=result,
                        sender=sender,
                        recipient=recipient,
                        sasl_username=sasl_username,
                        sasl_sender=sasl_sender
                    )
            )

    session.commit()

def cache_update(
        function,
        sender,
        recipient='',
        recipients=[],
        result=None,
        sasl_username='',
        sasl_sender=''
    ):

    """
        Insert an updated set of rows into the cache depending on the necessity
    """

    if not cache == True:
        return

    records = []

    _records = cache_select(
            function,
            sender,
            recipient,
            recipients,
            sasl_username,
            sasl_sender
        )

    for record in _records:
        if record.value == (int)(result):
            records.append(record)

    if not recipient == '':
        recipients.append(recipient)
        recipient = ''

    for recipient in recipients:
        recipient_found = False
        for record in records:
            if record.recipient == recipient:
                recipient_found = True
        if not recipient_found:
            cache_insert(
                    function=function,
                    sender=sender,
                    recipient=recipient,
                    result=result,
                    sasl_username=sasl_username,
                    sasl_sender=sasl_sender
                )

def defer_if_permit(message, policy_request=None):
    log.info(_("Returning action DEFER_IF_PERMIT: %s") % (message))
    print "action=DEFER_IF_PERMIT %s\n\n" % (message)
    sys.exit(0)

def dunno(message, policy_request=None):
    log.info(_("Returning action DUNNO: %s") % (message))
    print "action=DUNNO %s\n\n" % (message)
    sys.exit(0)

def hold(message, policy_request=None):
    log.info(_("Returning action HOLD: %s") % (message))
    print "action=HOLD %s\n\n" % (message)
    sys.exit(0)

def permit(message, policy_request=None):
    log.info(_("Returning action PERMIT: %s") % (message))
    if hasattr(policy_request, 'sasl_username'):
        print "action=PREPEND Sender: %s\naction=PERMIT\n\n" % (policy_request.sasl_username)
    else:
        print "action=PERMIT\n\n"
    sys.exit(0)

def reject(message, policy_request=None):
    log.info(_("Returning action REJECT: %s") % (message))
    print "action=REJECT %s\n\n" % (message)
    sys.exit(0)

def expand_mydomains():
    """
        Return a list of my domains.
    """

    global mydomains

    if not mydomains == None:
        return mydomains

    auth = Auth()
    auth.connect()

    mydomains = []

    _mydomains = auth.list_domains()

    for primary, secondaries in _mydomains:
        mydomains.append(primary)
        for secondary in secondaries:
            mydomains.append(secondary)

    return mydomains

def normalize_address(email_address):
    """
        Parse an address; Strip off anything after a recipient delimiter.
    """

    # TODO: Recipient delimiter is configurable.
    if len(email_address.split("+")) > 1:
        # Take the first part split by recipient delimiter and the last part
        # split by '@'.
        return "%s@%s" % (
                email_address.split("+")[0].lower(),
                # TODO: Under some conditions, the recipient may not be fully
                # qualified. We'll cross that bridge when we get there, though.
                email_address.split('@')[1].lower()
            )
    else:
        return email_address.lower()

def read_request_input():
    """
        Read a single policy request from sys.stdin, and return a dictionary
        containing the request.
    """

    start_time = time.time()

    log.debug(_("Starting to loop for new request"))

    policy_request = {}

    end_of_request = False
    while not end_of_request:
        if (time.time()-start_time) >= conf.timeout:
            log.warning(_("Timeout for policy request reading exceeded"))
            sys.exit(0)

        request_line = sys.stdin.readline()
        if request_line.strip() == '':
            if policy_request.has_key('request'):
                log.debug(_("End of current request"), level=8)
                end_of_request = True
        else:
            request_line = request_line.strip()
            log.debug(_("Getting line: %s") % (request_line), level=8)
            policy_request[request_line.split('=')[0]] = \
                '='.join(request_line.split('=')[1:]).lower()

    log.debug(_("Returning request"))

    return policy_request

def verify_domain(domain):
    """
        Verify whether the domain is internal (mine) or external.
    """

    global mydomains

    if not mydomains == None:
        return domain in mydomains

    auth = Auth()
    auth.connect()

    domain_verified = False

    _mydomains = auth.list_domains()

    for primary, secondaries in _mydomains:
        if primary == domain:
            domain_verified = True
        elif domain in secondaries:
            domain_verified = True

    if domain_verified == None:
        domain_verified = False

    return domain_verified

if __name__ == "__main__":
    access_policy_group = conf.add_cli_parser_option_group(
            _("Access Policy Options")
        )

    access_policy_group.add_option(  "--timeout",
                            dest    = "timeout",
                            action  = "store",
                            default = 10,
                            help    = _("SMTP Policy request timeout."))

    access_policy_group.add_option(  "--verify-recipient",
                            dest    = "verify_recipient",
                            action  = "store_true",
                            default = False,
                            help    = _("Verify the recipient access policy."))

    access_policy_group.add_option(  "--verify-sender",
                            dest    = "verify_sender",
                            action  = "store_true",
                            default = False,
                            help    = _("Verify the sender access policy."))

    access_policy_group.add_option(  "--allow-unauthenticated",
                            dest    = "allow_unauthenticated",
                            action  = "store_true",
                            default = False,
                            help    = _("Allow unauthenticated senders."))

    conf.finalize_conf()

    cache = cache_init()

    policy_requests = {}

    # Start the work
    while True:
        policy_request = read_request_input()
        instance = policy_request['instance']
        log.debug(_("Got request instance %s") % (instance))
        if policy_requests.has_key(instance):
            policy_requests[instance].add_request(policy_request)
        else:
            policy_requests[instance] = PolicyRequest(policy_request)

        protocol_state = policy_request['protocol_state'].strip().lower()

        log.debug(
                _("Request instance %s is in state %s") % (
                        instance,
                        protocol_state
                    )
            )

        if not protocol_state == 'data':
            log.debug(
                    _("Request instance %s is not yet in DATA state") % (
                            instance
                        )
                )

            print "action=DUNNO\n\n"
            sys.stdout.flush()

        # We can recognize being in the DATA part by the recipient_count being
        # set to a non-zero value and the protocol_state being set to 'data'.
        # Note that the input we're getting is a string, not an integer.
        else:
            log.debug(_("Request instance %s reached DATA state") % (instance))

            sender_allowed = False
            recipient_allowed = False

            if conf.verify_sender:
                sender_allowed = policy_requests[instance].verify_sender()
            else:
                sender_allowed = True

            if conf.verify_recipient:
                recipient_allowed = \
                        policy_requests[instance].verify_recipients()

            else:
                recipient_allowed = True

            if not sender_allowed:
                reject(_("Sender access denied"))
            elif not recipient_allowed:
                reject(_("Recipient access denied"))
            else:
                permit(_("No objections"), policy_requests[instance])
