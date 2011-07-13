#!/usr/bin/python
#
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

import os
import sys
import time

from optparse import OptionParser
from ConfigParser import SafeConfigParser

sys.path.append('..')
sys.path.append('../..')

import pykolab

from pykolab.auth import Auth
from pykolab.constants import KOLAB_LIB_PATH
from pykolab.translate import _

# TODO: Figure out how to make our logger do some syslogging as well.
log = pykolab.getLogger('pykolab.smtp_access_policy')

# TODO: Removing the stdout handler would mean one can no longer test by
# means of manual execution in debug mode.
#log.remove_stdout_handler()

conf = pykolab.getConf()

auth = Auth()

#
# Caching routines using buzhug.
#
# If creating the cache fails, we continue without any caching, significantly
# increasing the load on LDAP.
#

# TODO: This should be a configuration item.
cache_expire = 3600

try:
    from buzhug import TS_Base

    if os.access(
            os.path.join(KOLAB_LIB_PATH, 'kolab_smtp_access_policy'),
            os.W_OK
        ):
        cache_path = os.path.join(
                KOLAB_LIB_PATH,
                'kolab_smtp_access_policy',
                'cache'
            )

    elif os.access('/tmp/', os.W_OK):
        cache_path = os.path.join(
                '/tmp/',
                'kolab_smtp_access_policy'
            )
    else:
        raise OSError, _("No writeable path for cache found, bailing out")

    if os.path.exists(cache_path):
        mode = "open"
    else:
        mode = "override"

    cache = TS_Base(cache_path)
    try:
        log.debug(_("Attempting to use cache in %s") %(cache_path), level=8)
        cache.create(
                ('sender', str),
                ('recipient', str),
                ('sasl_username', str),
                ('sasl_sender', str),
                ('function', str),
                ('result', int),
                ('expire', float),
                mode=mode
            )

    except:
        log.debug(_("Using cache in %s failed") %(cache_path), level=8)
        try:
            log.debug(
                    _("Attempting to create cache in %s") %(cache_path),
                    level=8
                )

            cache.create(
                    ('sender', str),
                    ('recipient', str),
                    ('sasl_username', str),
                    ('sasl_sender', str),
                    ('function', str),
                    ('result', int),
                    ('expire', float),
                    mode="override"
                )

        except:
            log.error(_("Kolab SMTP Access Policy Cache not writeable!"))
            cache = False

except ImportError:
    log.warning(_("Could not import caching library, caching disabled"))
    cache = False

except OSError, e:
    log.warning(_("%s, caching disabled") %(e))
    cache = False

def defer_if_permit(message, policy_request=None):
    log.info(_("Returning action DEFER_IF_PERMIT: %s") %(message))
    print "action=DEFER_IF_PERMIT %s\n\n" %(message)

def dunno(message, policy_request=None):
    log.info(_("Returning action DUNNO: %s") %(message))
    print "action=DUNNO %s\n\n" %(message)

def hold(message, policy_request=None):
    log.info(_("Returning action HOLD: %s") %(message))
    print "action=HOLD %s\n\n" %(message)

def permit(message, policy_request=None):
    log.info(_("Returning action PERMIT: %s") %(message))
    print "action=PERMIT\n\n"

def reject(message, policy_request=None):
    log.info(_("Returning action REJECT: %s") %(message))
    print "action=REJECT %s\n\n" %(message)

def parse_address(email_address):
    """
        Parse an address; Strip off anything after a recipient delimiter.
    """

    # TODO: Recipient delimiter is configurable!
    if len(email_address.split("+")) > 1:
        # Take the first part split by recipient delimiter and the last part
        # split by '@'.
        return "%s@%s" %(
                email_address.split("+")[0],
                # TODO: Under some conditions, the recipient may not be fully
                # qualified. We'll cross that bridge when we get there, though.
                email_address.split('@')[1]
            )
    else:
        return email_address

def parse_policy(sender, recipient, policy):
    rules = { 'allow': [], 'deny': [] }

    for rule in policy:
        if rule.startswith("-"):
            rules['deny'].append(rule[1:])
        else:
            rules['allow'].append(rule)

    #print "From:", sender, "To:", recipient, "Rules:", rules

    allowed = False
    for rule in rules['allow']:
        deny_override = False
        if recipient.endswith(rule):
            #print "Matched allow rule:", rule
            for deny_rule in rules['deny']:
                if deny_rule.endswith(rule):
                    deny_override = True

            if not deny_override:
                allowed = True

    denied = False
    for rule in rules['deny']:
        allow_override = False
        if recipient.endswith(rule):
            #print "Matched deny rule:", rule
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

def read_request_input():
    """
        Read a single policy request from sys.stdin, and return a dictionary
        containing the request.
    """

    policy_request = {}

    end_of_request = False
    while not end_of_request:
        request_line = sys.stdin.readline().strip()
        if request_line == '':
            end_of_request = True
        else:
            policy_request[request_line.split('=')[0]] = \
                '='.join(request_line.split('=')[1:])

    return policy_request

def verify_domain(domain):
    """
        Verify whether the domain is internal (mine) or external.
    """

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

def verify_delegate(policy_request, sender_domain, sender_user):
    """
        Use the information passed along to determine whether the authenticated
        user can send on behalf of the envelope sender, using the kolabDelegate
        attribute value on the envelope sender's LDAP object.

        Returns True in case the user is a delegate of the sender, and False in
        case the user is NOT a delegate of the sender.
    """

    sender_is_delegate = None

    # TODO: Whether or not a domain name is in the sasl_username depends on
    # whether or not a default realm is specified elsewhere. In other words,
    # only attempt to do this and fall back to the primary_domain configured
    # for Kolab.
    sasl_domain = policy_request['sasl_username'].split('@')[1]

    sender_delegates = auth.get_user_attribute(
            sender_domain,
            sender_user,
            'kolabDelegate'
        )

    if sender_delegates == None:
        # No delegates for this sender could be found. The user is definitely
        # NOT a delegate of the sender.
        log.warning(
            _("User %s attempted to use envelope sender address %s without " + \
                "authorization") %(
                        policy_request["sasl_username"],
                        policy_request["sender"]
                    )
            )

        # Got a final answer here, do the cachking thing.
        if not cache == False:
            result_set = cache.select(
                    sender=policy_request['sender'],
                    recipient=policy_request['recipient'],
                    sasl_username=policy_request['sasl_username'],
                    sasl_sender=policy_request['sasl_sender'],
                    function='verify_sender'
                )

            if len(result_set) < 1:
                record_id = cache.insert(
                        sender=policy_request['sender'],
                        recipient=policy_request['recipient'],
                        sasl_username=policy_request['sasl_username'],
                        sasl_sender=policy_request['sasl_sender'],
                        function='verify_sender',
                        result=0,
                        expire=time.time() + cache_expire
                    )

        sender_is_delegate = False

    else:
        # See if we can match the value of the envelope sender delegates to
        # the actual sender sasl_username
        sasl_user = {
                'dn': auth.find_user(
                        # TODO: Use the configured cyrus-sasl result attribute.
                        'mail',
                        parse_address(policy_request['sasl_username']),
                        domain=sasl_domain
                    )
            }

        # Possible values for the kolabDelegate attribute are:
        # a 'uid', a 'dn'.
        sasl_user['uid'] = auth.get_user_attribute(
                sasl_domain,
                sasl_user,
                'uid'
            )

        if not type(sender_delegates) == list:
            sender_delegates = [ sender_delegates ]

        for sender_delegate in sender_delegates:
            if sasl_user['dn'] == sender_delegate:
                log.debug(
                        _("Found user %s to be a valid delegate user of %s") %(
                                policy_request["sasl_username"],
                                policy_request["sender"]
                            ),
                        level=8
                    )

                sender_is_delegate = True

            elif sasl_user['uid'] == sender_delegate:
                log.debug(
                        _("Found user %s to be a valid delegate user of %s") %(
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

def verify_recipient(policy_request):
    """
        Verify whether the sender is allowed send to this recipient, using the
        recipient's kolabAllowSMTPSender.
    """

    if not policy_request['sasl_username'] == '':
        log.info(_("Verifying authenticated sender '%(sender)s' with " + \
                "sasl_username '%(sasl_username)s' for recipient " + \
                "'%(recipient)s'") %(policy_request)
            )
    else:
        log.info(_("Verifying unauthenticated sender '%(sender)s' " + \
                "for recipient '%(recipient)s'") %(policy_request)
            )

    recipient_verified = False

    if not cache == False:
        records = cache(
                sender=policy_request['sender'],
                recipient=policy_request['recipient'],
                sasl_username=policy_request['sasl_username'],
                sasl_sender=policy_request['sasl_sender'],
                function='verify_recipient'
            )

        for record in records:
            if record.expire < time.time():
                # Purge record
                cache.delete(record)
                cache.cleanup()
            else:
                log.info(_("Reproducing verify_recipient(%r) from cache, " + \
                        "saving you queries, time and thus money.") %(
                                policy_request
                            )
                    )

                return record.result

    # TODO: Under some conditions, the recipient may not be fully qualified.
    # We'll cross that bridge when we get there, though.
    domain = policy_request['recipient'].split('@')[1]

    if verify_domain(domain):
        if auth.secondary_domains.has_key(domain):
            log.debug(_("Using authentication domain %s instead of %s") %(auth.secondary_domains[domain],domain), level=8)
            domain = auth.secondary_domains[domain]
        else:
            log.debug(_("Domain %s is a primary domain") %(domain), level=8)
    else:
        log.warning(_("Checking the recipient for domain %s that is not ours") %(domain))

    # Attr search list
    # TODO: Use the configured filter
    attr_search = [ 'mail', 'alias', 'mailalternateaddress' ]
    user = {
            'dn': auth.find_user(
                    attr_search,
                    parse_address(policy_request['recipient']),
                    domain=domain,
                    additional_filter="(&(objectclass=kolabinetorgperson)%(search_filter)s)"
                )
        }

    recipient_policy = auth.get_user_attribute(
            domain,
            user,
            'kolabAllowSMTPSender'
        )

    # If no such attribute has been specified, allow
    if recipient_policy == None:
        recipient_verified = True

    # Otherwise, match the values in allowed_senders to the actual sender
    else:
        recipient_verified = parse_policy(
                policy_request['sasl_username'],
                policy_request['recipient'],
                recipient_policy
            )

    if not cache == False:
        result_set = cache.select(
                sender=policy_request['sender'],
                recipient=policy_request['recipient'],
                sasl_username=policy_request['sasl_username'],
                sasl_sender=policy_request['sasl_sender'],
                function='verify_recipient'
            )

        if len(result_set) < 1:
            record_id = cache.insert(
                    sender=policy_request['sender'],
                    recipient=policy_request['recipient'],
                    sasl_username=policy_request['sasl_username'],
                    sasl_sender=policy_request['sasl_sender'],
                    function='verify_recipient',
                    result=(int)(recipient_verified),
                    expire=time.time() + cache_expire
                )

    return recipient_verified

def verify_sender(policy_request):
    """
        Verify the sender's access policy.

        1) Verify whether the sasl_username is allowed to send using the
        envelope sender address, with the kolabDelegate attribute associated
        with the LDAP object that has the envelope sender address.

        2) Verify whether the sender is allowed to send to recipient(s) listed
        on the sender's object.

        A third potential action could be to check the recipient object to see
        if the sender is allowed to send to the recipient by the recipient's
        kolabAllowSMTPSender, but this is done in verify_recipient().
    """

    if not policy_request['sasl_username'] == '':
        log.info(_("Verifying authenticated sender '%(sender)s' with " + \
                "sasl_username '%(sasl_username)s'") %(policy_request)
            )
    else:
        log.info(_("Verifying unauthenticated sender '%(sender)s'") %(
                    policy_request
                )
            )

    sender_verified = False

    sender_is_delegate = None

    sasl_user = False

    if not cache == False:
        records = cache(
                sender=policy_request['sender'],
                recipient=policy_request['recipient'],
                sasl_username=policy_request['sasl_username'],
                sasl_sender=policy_request['sasl_sender'],
                function='verify_sender'
            )

        for record in records:
            if record.expire < time.time():
                # Purge record
                cache.delete(record)
                cache.cleanup()
            else:
                log.info(_("Reproducing verify_sender(%r) from cache, " + \
                        "saving you queries, time and thus money.") %(
                                policy_request
                            )
                    )

                return record.result

    sender_domain = policy_request['sender'].split('@')[1]

    # Obtain 'kolabDelegate' from the envelope sender.
    log.debug(
            _("Obtaining envelope sender dn for %s") %(
                    policy_request['sender']
                ),
            level=8
        )

    sender_user = {
            'dn': auth.find_user(
                    # TODO: Use the configured cyrus-sasl result attribute
                    'mail',
                    parse_address(policy_request['sender']),
                    domain=sender_domain
                )
        }

    log.debug(_("Found user object %(dn)s") %(sender_user), level=8)

    # Only when a user is authenticated do we have the means to check for
    # kolabDelegate functionality.
    if not policy_request['sasl_username'] == '':
        sender_is_delegate = verify_delegate(
                policy_request,
                sender_domain,
                sender_user
            )

    # If the authenticated user is using delegate functionality, apply the
    # recipient policy attribute for the envelope sender.
    if sender_is_delegate == False:
        return False

    elif sender_is_delegate:
        recipient_policy_domain = sender_domain
        recipient_policy_sender = parse_address(policy_request['sender'])
        recipient_policy_user = sender_user
    elif not policy_request['sasl_username'] == '':
        sasl_domain = policy_request['sasl_username'].split('@')[1]
        recipient_policy_domain = sasl_domain
        recipient_policy_sender = policy_request['sasl_username']
        if not sasl_user:
            sasl_user = {
                    'dn': auth.find_user(
                            # TODO: Use the configured cyrus-sasl result
                            # attribute
                            'mail',
                            parse_address(policy_request['sasl_username']),
                            domain=sasl_domain
                        )
                }

        recipient_policy_user = sasl_user
    else:
        if not conf.allow_unauthenticated:
            reject(_("Could not verify sender"))
        else:
            recipient_policy_domain = sender_domain
            recipient_policy_sender = parse_address(policy_request['sender'])
            recipient_policy_user = sender_user

    log.debug(_("Verifying whether sender is allowed to send to recipient " + \
            "using sender policy"), level=8)

    recipient_policy = auth.get_user_attribute(
            recipient_policy_domain,
            recipient_policy_user,
            'kolabAllowSMTPRecipient'
        )

    log.debug(_("Result is '%r'") %(recipient_policy), level=8)

    # If no such attribute has been specified, allow
    if recipient_policy == None:
        log.debug(
                _("No recipient policy restrictions exist for this sender"),
                level=8
            )

        sender_verified = True

    # Otherwise, match the values in allowed_recipients to the actual recipients
    else:
        log.debug(
                _("Found a recipient policy to apply for this sender."),
                level=8
            )

        sender_verified = parse_policy(
                recipient_policy_sender,
                policy_request['recipient'],
                recipient_policy
            )

        log.debug(
                _("Recipient policy evaluated to '%r'.") %(sender_verified),
                level=8
            )

    if not cache == False:
        result_set = cache.select(
                sender=policy_request['sender'],
                recipient=policy_request['recipient'],
                sasl_username=policy_request['sasl_username'],
                sasl_sender=policy_request['sasl_sender'],
                function='verify_sender'
            )

        if len(result_set) < 1:
            record_id = cache.insert(
                    sender=policy_request['sender'],
                    recipient=policy_request['recipient'],
                    sasl_username=policy_request['sasl_username'],
                    sasl_sender=policy_request['sasl_sender'],
                    function='verify_sender',
                    result=(int)(sender_verified),
                    expire=time.time() + cache_expire
                )

    return sender_verified

if __name__ == "__main__":
    access_policy_group = conf.add_cli_parser_option_group(
            _("Access Policy Options")
        )

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

    # Start the work
    while True:
        policy_request = read_request_input()
        break
    # Set the overall default policy in case nothing attracts any particular
    # type of action.
    #
    # When either is configured or specified to be verified, negate
    # that policy to be false by default.
    #
    sender_allowed = True
    recipient_allowed = True

    if conf.verify_sender:
        sender_allowed = False

        log.debug(_("Verifying sender."), level=8)

        # If no sender is specified, we bail out.
        if policy_request['sender'] == "":
            log.debug(_("No sender specified."), level=8)
            reject(_("Invalid sender"))

        # If no sasl username exists, ...
        if policy_request['sasl_username'] == "":
            log.debug(_("No SASL username in request."), level=8)

            if not conf.allow_unauthenticated:
                log.debug(
                        _("Not allowing unauthenticated senders."),
                        level=8
                    )

                reject(_("Access denied for unauthenticated senders"))

            else:
                log.debug(_("Allowing unauthenticated senders."), level=8)

                if not verify_domain(policy_request['sender'].split('@')[1]):
                    sender_allowed = True
                    permit(_("External sender"))

                else:
                    sender_allowed = verify_sender(policy_request)

        # If the authenticated username is the sender...
        elif policy_request["sasl_username"] == policy_request["sender"]:
            log.debug(
                    _("Allowing authenticated sender %s to send as %s.") %(
                            policy_request["sasl_username"],
                            policy_request["sender"]
                        ),
                    level=8
                )

            sender_allowed = True

            permit(
                    _("Authenticated as sender %s") %(
                            policy_request['sender']
                        )
                )

        # Or if the authenticated username is the sender but the sender address
        # lists an address with a recipient delimiter...
        #
        # TODO: The recipient delimiter is configurable!
        elif policy_request["sasl_username"] == \
                parse_address(
                        policy_request["sender"]
                    ):

            sender_allowed = True

            permit(
                    _("Authenticated as sender %s") %(
                            parse_address(policy_request["sender"])
                        )
                )

        else:
            sender_allowed = verify_sender(policy_request)

    if conf.verify_recipient:
        recipient_allowed = False

        log.debug(_("Verifying recipient."), level=8)

        if policy_request['recipient'] == "":
            reject(_("Invalid recipient"))

        if policy_request['sasl_username'] == "":
            log.debug(_("No SASL username in request."), level=8)

            if not conf.allow_unauthenticated:
                log.debug(_("Not allowing unauthenticated senders."), level=8)
                reject(_("Access denied for unauthenticated senders"))

            else:
                recipient_allowed = verify_recipient(policy_request)
        else:
            recipient_allowed = verify_recipient(policy_request)

    # TODO: Insert whitelists.
    if conf.verify_sender and not sender_allowed:
        reject(_("Sender access denied"), policy_request)

    elif conf.verify_recipient and not recipient_allowed:
        reject(_("Recipient access denied"), policy_request)

    else:
        permit(_("No objections"))