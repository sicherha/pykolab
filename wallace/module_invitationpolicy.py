# -*- coding: utf-8 -*-
# Copyright 2014 Kolab Systems AG (http://www.kolabsys.com)
#
# Thomas Bruederli (Kolab Systems) <bruederli@kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import datetime
import os
import tempfile
import time
from urlparse import urlparse
import urllib
import hashlib
import traceback

from email import message_from_string
from email.parser import Parser
from email.utils import formataddr
from email.utils import getaddresses

import modules

import pykolab
import kolabformat

from pykolab import utils
from pykolab.auth import Auth
from pykolab.conf import Conf
from pykolab.imap import IMAP
from pykolab.xml import to_dt
from pykolab.xml import utils as xmlutils
from pykolab.xml import todo_from_message
from pykolab.xml import event_from_message
from pykolab.xml import participant_status_label
from pykolab.itip import objects_from_message
from pykolab.itip import check_event_conflict
from pykolab.itip import send_reply
from pykolab.translate import _

# define some contstants used in the code below
ACT_MANUAL         = 1
ACT_ACCEPT         = 2
ACT_DELEGATE       = 4
ACT_REJECT         = 8
ACT_UPDATE         = 16
ACT_SAVE_TO_FOLDER = 32

COND_IF_AVAILABLE  = 64
COND_IF_CONFLICT   = 128
COND_TENTATIVE     = 256
COND_NOTIFY        = 512
COND_TYPE_EVENT    = 1024
COND_TYPE_TASK     = 2048
COND_TYPE_ALL      = COND_TYPE_EVENT + COND_TYPE_TASK

ACT_TENTATIVE         = ACT_ACCEPT + COND_TENTATIVE
ACT_UPDATE_AND_NOTIFY = ACT_UPDATE + COND_NOTIFY

FOLDER_TYPE_ANNOTATION = '/vendor/kolab/folder-type'

MESSAGE_PROCESSED = 1
MESSAGE_FORWARD   = 2

policy_name_map = {
    # policy values applying to all object types
    'ALL_MANUAL':                     ACT_MANUAL + COND_TYPE_ALL,
    'ALL_ACCEPT':                     ACT_ACCEPT + COND_TYPE_ALL,
    'ALL_REJECT':                     ACT_REJECT + COND_TYPE_ALL,
    'ALL_DELEGATE':                   ACT_DELEGATE + COND_TYPE_ALL,  # not implemented
    'ALL_UPDATE':                     ACT_UPDATE + COND_TYPE_ALL,
    'ALL_UPDATE_AND_NOTIFY':          ACT_UPDATE_AND_NOTIFY + COND_TYPE_ALL,
    'ALL_SAVE_TO_FOLDER':             ACT_SAVE_TO_FOLDER + COND_TYPE_ALL,
    # event related policy values
    'EVENT_MANUAL':                   ACT_MANUAL + COND_TYPE_EVENT,
    'EVENT_ACCEPT':                   ACT_ACCEPT + COND_TYPE_EVENT,
    'EVENT_TENTATIVE':                ACT_TENTATIVE + COND_TYPE_EVENT,
    'EVENT_REJECT':                   ACT_REJECT + COND_TYPE_EVENT,
    'EVENT_DELEGATE':                 ACT_DELEGATE + COND_TYPE_EVENT,  # not implemented
    'EVENT_UPDATE':                   ACT_UPDATE + COND_TYPE_EVENT,
    'EVENT_UPDATE_AND_NOTIFY':        ACT_UPDATE_AND_NOTIFY + COND_TYPE_EVENT,
    'EVENT_ACCEPT_IF_NO_CONFLICT':    ACT_ACCEPT + COND_IF_AVAILABLE + COND_TYPE_EVENT,
    'EVENT_TENTATIVE_IF_NO_CONFLICT': ACT_ACCEPT + COND_TENTATIVE + COND_IF_AVAILABLE + COND_TYPE_EVENT,
    'EVENT_DELEGATE_IF_CONFLICT':     ACT_DELEGATE + COND_IF_CONFLICT + COND_TYPE_EVENT,
    'EVENT_REJECT_IF_CONFLICT':       ACT_REJECT + COND_IF_CONFLICT + COND_TYPE_EVENT,
    'EVENT_SAVE_TO_FOLDER':           ACT_SAVE_TO_FOLDER + COND_TYPE_EVENT,
    # task related policy values
    'TASK_MANUAL':                    ACT_MANUAL + COND_TYPE_TASK,
    'TASK_ACCEPT':                    ACT_ACCEPT + COND_TYPE_TASK,
    'TASK_REJECT':                    ACT_REJECT + COND_TYPE_TASK,
    'TASK_DELEGATE':                  ACT_DELEGATE + COND_TYPE_TASK,  # not implemented
    'TASK_UPDATE':                    ACT_UPDATE + COND_TYPE_TASK,
    'TASK_UPDATE_AND_NOTIFY':         ACT_UPDATE_AND_NOTIFY + COND_TYPE_TASK,
    'TASK_SAVE_TO_FOLDER':            ACT_SAVE_TO_FOLDER + COND_TYPE_TASK,
    # legacy values
    'ACT_MANUAL':                     ACT_MANUAL + COND_TYPE_ALL,
    'ACT_ACCEPT':                     ACT_ACCEPT + COND_TYPE_ALL,
    'ACT_ACCEPT_IF_NO_CONFLICT':      ACT_ACCEPT + COND_IF_AVAILABLE + COND_TYPE_EVENT,
    'ACT_TENTATIVE':                  ACT_TENTATIVE + COND_TYPE_EVENT,
    'ACT_TENTATIVE_IF_NO_CONFLICT':   ACT_ACCEPT + COND_TENTATIVE + COND_IF_AVAILABLE + COND_TYPE_EVENT,
    'ACT_DELEGATE':                   ACT_DELEGATE + COND_TYPE_ALL,
    'ACT_DELEGATE_IF_CONFLICT':       ACT_DELEGATE + COND_IF_CONFLICT + COND_TYPE_EVENT,
    'ACT_REJECT':                     ACT_REJECT + COND_TYPE_ALL,
    'ACT_REJECT_IF_CONFLICT':         ACT_REJECT + COND_IF_CONFLICT + COND_TYPE_EVENT,
    'ACT_UPDATE':                     ACT_UPDATE + COND_TYPE_ALL,
    'ACT_UPDATE_AND_NOTIFY':          ACT_UPDATE_AND_NOTIFY + COND_TYPE_ALL,
    'ACT_SAVE_TO_CALENDAR':           ACT_SAVE_TO_FOLDER + COND_TYPE_EVENT,
}

policy_value_map = dict([(v &~ COND_TYPE_ALL, k) for (k, v) in policy_name_map.iteritems()])

object_type_conditons = {
    'event': COND_TYPE_EVENT,
    'task':  COND_TYPE_TASK
}

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/invitationpolicy/'

auth = None
imap = None
write_locks = []

def __init__():
    modules.register('invitationpolicy', execute, description=description())

def accept(filepath):
    new_filepath = os.path.join(
        mybasepath,
        'ACCEPT',
        os.path.basename(filepath)
    )

    cleanup()
    os.rename(filepath, new_filepath)
    filepath = new_filepath
    exec('modules.cb_action_ACCEPT(%r, %r)' % ('invitationpolicy',filepath))

def reject(filepath):
    new_filepath = os.path.join(
        mybasepath,
        'REJECT',
        os.path.basename(filepath)
    )

    os.rename(filepath, new_filepath)
    filepath = new_filepath
    exec('modules.cb_action_REJECT(%r, %r)' % ('invitationpolicy',filepath))

def description():
    return """Invitation policy execution module."""

def cleanup():
    global auth, imap, write_locks

    log.debug("cleanup(): %r, %r" % (auth, imap), level=9)

    auth.disconnect()
    del auth

    # Disconnect IMAP or we lock the mailbox almost constantly
    imap.disconnect()
    del imap

    # remove remaining write locks
    for key in write_locks:
        remove_write_lock(key, False)

def execute(*args, **kw):
    global auth, imap

    # (re)set language to default
    pykolab.translate.setUserLanguage(conf.get('kolab','default_locale'))

    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT', 'REJECT', 'HOLD', 'DEFER', 'locks']:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    log.debug(_("Invitation policy called for %r, %r") % (args, kw), level=9)

    auth = Auth()
    imap = IMAP()

    filepath = args[0]

    # ignore calls on lock files
    if '/locks/' in filepath or kw.has_key('stage') and kw['stage'] == 'locks':
        return False

    log.debug("Invitation policy executing for %r, %r" % (filepath, '/locks/' in filepath), level=8)

    if kw.has_key('stage'):
        log.debug(_("Issuing callback after processing to stage %s") % (kw['stage']), level=8)

        log.debug(_("Testing cb_action_%s()") % (kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' % (kw['stage'])):
            log.debug(_("Attempting to execute cb_action_%s()") % (kw['stage']), level=8)

            exec(
                'modules.cb_action_%s(%r, %r)' % (
                    kw['stage'],
                    'invitationpolicy',
                    filepath
                )
            )

            return filepath
    else:
        # Move to incoming
        new_filepath = os.path.join(
            mybasepath,
            'incoming',
            os.path.basename(filepath)
        )

        if not filepath == new_filepath:
            log.debug("Renaming %r to %r" % (filepath, new_filepath))
            os.rename(filepath, new_filepath)
            filepath = new_filepath

    # parse full message
    message = Parser().parse(open(filepath, 'r'))

    # invalid message, skip
    if not message.get('X-Kolab-To'):
        return filepath

    recipients = [address for displayname,address in getaddresses(message.get_all('X-Kolab-To'))]
    sender_email = [address for displayname,address in getaddresses(message.get_all('X-Kolab-From'))][0]

    any_itips = False
    recipient_email = None
    recipient_user_dn = None

    # An iTip message may contain multiple events. Later on, test if the message
    # is an iTip message by checking the length of this list.
    try:
        itip_events = objects_from_message(message, ['VEVENT','VTODO'], ['REQUEST', 'REPLY', 'CANCEL'])
    except Exception, e:
        log.error(_("Failed to parse iTip objects from message: %r" % (e)))
        itip_events = []

    if not len(itip_events) > 0:
        log.info(_("Message is not an iTip message or does not contain any (valid) iTip objects."))

    else:
        any_itips = True
        log.debug(_("iTip objects attached to this message contain the following information: %r") % (itip_events), level=9)

    # See if any iTip actually allocates a user.
    if any_itips and len([x['uid'] for x in itip_events if x.has_key('attendees') or x.has_key('organizer')]) > 0:
        auth.connect()

        for recipient in recipients:
            recipient_user_dn = user_dn_from_email_address(recipient)
            if recipient_user_dn:
                recipient_email = recipient
                break

    if not any_itips:
        log.debug(_("No itips, no users, pass along %r") % (filepath), level=5)
        return filepath
    elif recipient_email is None:
        log.debug(_("iTips, but no users, pass along %r") % (filepath), level=5)
        return filepath

    # we're looking at the first itip object
    itip_event = itip_events[0]

    # for replies, the organizer is the recipient
    if itip_event['method'] == 'REPLY':
        user_attendees = [itip_event['organizer']] if str(itip_event['organizer']).split(':')[-1] == recipient_email else []

    else:
        # Limit the attendees to the one that is actually invited with the current message.
        attendees = [str(a).split(':')[-1] for a in (itip_event['attendees'] if itip_event.has_key('attendees') else [])]
        user_attendees = [a for a in attendees if a == recipient_email]

        if itip_event.has_key('organizer'):
            sender_email = itip_event['xml'].get_organizer().email()

    # abort if no attendee matches the envelope recipient
    if len(user_attendees) == 0:
        log.info(_("No user attendee matching envelope recipient %s, skip message") % (recipient_email))
        return filepath

    receiving_user = auth.get_entry_attributes(None, recipient_user_dn, ['*'])
    log.debug(_("Receiving user: %r") % (receiving_user), level=8)

    # change gettext language to the preferredlanguage setting of the receiving user
    if receiving_user.has_key('preferredlanguage'):
        pykolab.translate.setUserLanguage(receiving_user['preferredlanguage'])

    # find user's kolabInvitationPolicy settings and the matching policy values
    type_condition = object_type_conditons.get(itip_event['type'], COND_TYPE_ALL)
    policies = get_matching_invitation_policies(receiving_user, sender_email, type_condition)

    # select a processing function according to the iTip request method
    method_processing_map = {
        'REQUEST': process_itip_request,
        'REPLY':   process_itip_reply,
        'CANCEL':  process_itip_cancel
    }

    done = None
    if method_processing_map.has_key(itip_event['method']):
        processor_func = method_processing_map[itip_event['method']]

        # connect as cyrus-admin
        imap.connect()

        for policy in policies:
            log.debug(_("Apply invitation policy %r for sender %r") % (policy_value_map[policy], sender_email), level=8)
            done = processor_func(itip_event, policy, recipient_email, sender_email, receiving_user)

            # matching policy found
            if done is not None:
                break

            # remove possible write lock from this iteration
            remove_write_lock(get_lock_key(receiving_user, itip_event['uid']))

    else:
        log.debug(_("Ignoring '%s' iTip method") % (itip_event['method']), level=8)

    # message has been processed by the module, remove it
    if done == MESSAGE_PROCESSED:
        log.debug(_("iTip message %r consumed by the invitationpolicy module") % (message.get('Message-ID')), level=5)
        os.unlink(filepath)
        cleanup()
        return None

    # accept message into the destination inbox
    accept(filepath)


def process_itip_request(itip_event, policy, recipient_email, sender_email, receiving_user):
    """
        Process an iTip REQUEST message according to the given policy
    """

    # if invitation policy is set to MANUAL, pass message along
    if policy & ACT_MANUAL:
        log.info(_("Pass invitation for manual processing"))
        return MESSAGE_FORWARD

    try:
        receiving_attendee = itip_event['xml'].get_attendee_by_email(recipient_email)
        log.debug(_("Receiving Attendee: %r") % (receiving_attendee), level=9)
    except Exception, e:
        log.error("Could not find envelope attendee: %r" % (e))
        return MESSAGE_FORWARD

    # process request to participating attendees with RSVP=TRUE or PARTSTAT=NEEDS-ACTION
    is_task = itip_event['type'] == 'task'
    nonpart = receiving_attendee.get_role() == kolabformat.NonParticipant
    partstat = receiving_attendee.get_participant_status()
    save_object = not nonpart or not partstat == kolabformat.PartNeedsAction
    rsvp = receiving_attendee.get_rsvp()
    scheduling_required = rsvp or partstat == kolabformat.PartNeedsAction
    respond_with = receiving_attendee.get_participant_status(True)
    condition_fulfilled = True

    # find existing event in user's calendar
    existing = find_existing_object(itip_event['uid'], itip_event['type'], receiving_user, True)

    # compare sequence number to determine a (re-)scheduling request
    if existing is not None:
        log.debug(_("Existing %s: %r") % (existing.type, existing), level=9)
        scheduling_required = itip_event['sequence'] > 0 and itip_event['sequence'] > existing.get_sequence()
        save_object = True

    # if scheduling: check availability (skip that for tasks)
    if scheduling_required:
        if not is_task and policy & (COND_IF_AVAILABLE | COND_IF_CONFLICT):
            condition_fulfilled = check_availability(itip_event, receiving_user)
        if not is_task and policy & COND_IF_CONFLICT:
            condition_fulfilled = not condition_fulfilled

        log.debug(_("Precondition for object %r fulfilled: %r") % (itip_event['uid'], condition_fulfilled), level=5)

        respond_with = None
        if policy & ACT_ACCEPT and condition_fulfilled:
            respond_with = 'TENTATIVE' if policy & COND_TENTATIVE else 'ACCEPTED'

        elif policy & ACT_REJECT and condition_fulfilled:
            respond_with = 'DECLINED'
            # TODO: only save declined invitation when a certain config option is set?

        elif policy & ACT_DELEGATE and condition_fulfilled:
            # TODO: delegate (but to whom?)
            return None

    # auto-update changes if enabled for this user
    elif policy & ACT_UPDATE and existing:
        # compare sequence number to avoid outdated updates
        if not itip_event['sequence'] == existing.get_sequence():
            log.info(_("The iTip request sequence (%r) doesn't match the referred object version (%r). Ignoring.") % (
                itip_event['sequence'], existing.get_sequence()
            ))
            return None

        log.debug(_("Auto-updating %s %r on iTip REQUEST (no re-scheduling)") % (existing.type, existing.uid), level=8)
        save_object = True

        # retain task status and percent-complete properties from my old copy
        if is_task:
            itip_event['xml'].set_status(existing.get_status())
            itip_event['xml'].set_percentcomplete(existing.get_percentcomplete())

        if policy & COND_NOTIFY:
            send_update_notification(itip_event['xml'], receiving_user, existing, False)

    # if RSVP, send an iTip REPLY
    if rsvp or scheduling_required:
        # set attendee's CN from LDAP record if yet missing
        if not receiving_attendee.get_name() and receiving_user.has_key('cn'):
            receiving_attendee.set_name(receiving_user['cn'])

        # send iTip reply
        if respond_with is not None:
            receiving_attendee.set_participant_status(respond_with)
            send_reply(recipient_email, itip_event, invitation_response_text(itip_event['type']),
                subject=_('"%(summary)s" has been %(status)s'))

        elif policy & ACT_SAVE_TO_FOLDER:
            # copy the invitation into the user's default folder with PARTSTAT=NEEDS-ACTION
            itip_event['xml'].set_attendee_participant_status(receiving_attendee, 'NEEDS-ACTION')
            save_object = True

        else:
            # policy doesn't match, pass on to next one
            return None

    if save_object:
        targetfolder = None

        if existing:
            # delete old version from IMAP
            targetfolder = existing._imap_folder
            delete_object(existing)

        if not nonpart or existing:
            # save new copy from iTip
            if store_object(itip_event['xml'], receiving_user, targetfolder):
                return MESSAGE_PROCESSED

    return None


def process_itip_reply(itip_event, policy, recipient_email, sender_email, receiving_user):
    """
        Process an iTip REPLY message according to the given policy
    """

    # if invitation policy is set to MANUAL, pass message along
    if policy & ACT_MANUAL:
        log.info(_("Pass reply for manual processing"))
        return MESSAGE_FORWARD

    # auto-update is enabled for this user
    if policy & ACT_UPDATE:
        try:
            sender_attendee = itip_event['xml'].get_attendee_by_email(sender_email)
            log.debug(_("Sender Attendee: %r") % (sender_attendee), level=9)
        except Exception, e:
            log.error("Could not find envelope sender attendee: %r" % (e))
            return MESSAGE_FORWARD

        # find existing event in user's calendar
        # sets/checks lock to avoid concurrent wallace processes trying to update the same event simultaneously
        existing = find_existing_object(itip_event['uid'], itip_event['type'], receiving_user, True)

        if existing:
            # compare sequence number to avoid outdated replies?
            if not itip_event['sequence'] == existing.get_sequence():
                log.info(_("The iTip reply sequence (%r) doesn't match the referred object version (%r). Forwarding to Inbox.") % (
                    itip_event['sequence'], existing.get_sequence()
                ))
                remove_write_lock(existing._lock_key)
                return MESSAGE_FORWARD

            log.debug(_("Auto-updating %s %r on iTip REPLY") % (existing.type, existing.uid), level=8)
            try:
                existing_attendee = existing.get_attendee(sender_email)
                existing.set_attendee_participant_status(sender_email, sender_attendee.get_participant_status(), rsvp=False)
            except Exception, e:
                log.error("Could not find corresponding attende in organizer's copy: %r" % (e))

                # append delegated-from attendee ?
                if len(sender_attendee.get_delegated_from()) > 0:
                    existing._attendees.append(sender_attendee)
                    existing.event.setAttendees(existing._attendees)
                else:
                    # TODO: accept new participant if ACT_ACCEPT ?
                    remove_write_lock(existing._lock_key)
                    return MESSAGE_FORWARD

            # append delegated-to attendee
            if len(sender_attendee.get_delegated_to()) > 0:
                try:
                    delegatee_email = sender_attendee.get_delegated_to(True)[0]
                    sender_delegatee = itip_event['xml'].get_attendee_by_email(delegatee_email)
                    existing_delegatee = existing.find_attendee(delegatee_email)

                    if not existing_delegatee:
                        existing._attendees.append(sender_delegatee)
                        log.debug(_("Add delegatee: %r") % (sender_delegatee.to_dict()), level=9)
                    else:
                        existing_delegatee.copy_from(sender_delegatee)
                        log.debug(_("Update existing delegatee: %r") % (existing_delegatee.to_dict()), level=9)

                    # copy all parameters from replying attendee (e.g. delegated-to, role, etc.)
                    existing_attendee.copy_from(sender_attendee)
                    existing.event.setAttendees(existing._attendees)
                    log.debug(_("Update delegator: %r") % (existing_attendee.to_dict()), level=9)

                except Exception, e:
                    log.error("Could not find delegated-to attendee: %r" % (e))

            # update the organizer's copy of the object
            if update_object(existing, receiving_user):
                if policy & COND_NOTIFY:
                    send_update_notification(existing, receiving_user, existing, True)

                # update all other attendee's copies
                if conf.get('wallace','invitationpolicy_autoupdate_other_attendees_on_reply'):
                    propagate_changes_to_attendees_accounts(existing)

                return MESSAGE_PROCESSED

        else:
            log.error(_("The object referred by this reply was not found in the user's folders. Forwarding to Inbox."))
            return MESSAGE_FORWARD

    return None


def process_itip_cancel(itip_event, policy, recipient_email, sender_email, receiving_user):
    """
        Process an iTip CANCEL message according to the given policy
    """

    # if invitation policy is set to MANUAL, pass message along
    if policy & ACT_MANUAL:
        log.info(_("Pass cancellation for manual processing"))
        return MESSAGE_FORWARD

    # auto-update the local copy with STATUS=CANCELLED
    if policy & ACT_UPDATE:
        # find existing object in user's folders
        existing = find_existing_object(itip_event['uid'], itip_event['type'], receiving_user, True)

        if existing:
            existing.set_status('CANCELLED')
            existing.set_transparency(True)
            if update_object(existing, receiving_user):
                # send cancellation notification
                if policy & ACT_UPDATE_AND_NOTIFY:
                    send_cancel_notification(existing, receiving_user)

                return MESSAGE_PROCESSED

        else:
            log.error(_("The object referred by this reply was not found in the user's folders. Forwarding to Inbox."))
            return MESSAGE_FORWARD

    return None


def user_dn_from_email_address(email_address):
    """
        Resolves the given email address to a Kolab user entity
    """
    global auth

    if not auth:
        auth = Auth()
        auth.connect()

    # return cached value
    if user_dn_from_email_address.cache.has_key(email_address):
        return user_dn_from_email_address.cache[email_address]

    local_domains = auth.list_domains()

    if not local_domains == None:
        local_domains = list(set(local_domains.keys()))

    if not email_address.split('@')[1] in local_domains:
        user_dn_from_email_address.cache[email_address] = None
        return None

    log.debug(_("Checking if email address %r belongs to a local user") % (email_address), level=8)

    user_dn = auth.find_user_dn(email_address, True)

    if isinstance(user_dn, basestring):
        log.debug(_("User DN: %r") % (user_dn), level=8)
    else:
        log.debug(_("No user record(s) found for %r") % (email_address), level=9)

    # remember this lookup
    user_dn_from_email_address.cache[email_address] = user_dn

    return user_dn

user_dn_from_email_address.cache = {}


def get_matching_invitation_policies(receiving_user, sender_email, type_condition=COND_TYPE_ALL):
    # get user's kolabInvitationPolicy settings
    policies = receiving_user['kolabinvitationpolicy'] if receiving_user.has_key('kolabinvitationpolicy') else []
    if policies and not isinstance(policies, list):
        policies = [policies]

    if len(policies) == 0:
        policies = conf.get_list('wallace', 'kolab_invitation_policy')

    # match policies agains the given sender_email
    matches = []
    for p in policies:
        if ':' in p:
            (value, domain) = p.split(':')
        else:
            value = p
            domain = ''

        if domain == '' or domain == '*' or str(sender_email).endswith(domain):
            value = value.upper()
            if policy_name_map.has_key(value):
                val = policy_name_map[value]
                # append if type condition matches
                if val & type_condition:
                    matches.append(val &~ COND_TYPE_ALL)

    # add manual as default action
    if len(matches) == 0:
        matches.append(ACT_MANUAL)

    return matches


def imap_proxy_auth(user_rec):
    """
        Perform IMAP login using proxy authentication with admin credentials
    """
    global imap

    mail_attribute = conf.get('cyrus-sasl', 'result_attribute')
    if mail_attribute == None:
        mail_attribute = 'mail'

    mail_attribute = mail_attribute.lower()

    if not user_rec.has_key(mail_attribute):
        log.error(_("User record doesn't have the mailbox attribute %r set" % (mail_attribute)))
        return False

    # do IMAP prox auth with the given user
    backend = conf.get('kolab', 'imap_backend')
    admin_login = conf.get(backend, 'admin_login')
    admin_password = conf.get(backend, 'admin_password')

    try:
        imap.disconnect()
        imap.connect(login=False)
        imap.login_plain(admin_login, admin_password, user_rec[mail_attribute])
    except Exception, errmsg:
        log.error(_("IMAP proxy authentication failed: %r") % (errmsg))
        return False

    return True


def list_user_folders(user_rec, type):
    """
        Get a list of the given user's private calendar/tasks folders
    """
    global imap

    # return cached list
    if user_rec.has_key('_imap_folders'):
        return user_rec['_imap_folders'];

    result = []

    if not imap_proxy_auth(user_rec):
        return result

    folders = imap.list_folders('*')
    log.debug(_("List %r folders for user %r: %r") % (type, user_rec['mail'], folders), level=8)

    (ns_personal, ns_other, ns_shared) = imap.namespaces()

    if isinstance(ns_shared, list):
        ns_shared = ns_shared[0]
    if isinstance(ns_other, list):
        ns_other = ns_other[0]

    for folder in folders:
        # exclude shared and other user's namespace
        # TODO: list shared folders the user has write privileges ?
        if folder.startswith(ns_other) or folder.startswith(ns_shared):
            continue;

        metadata = imap.get_metadata(folder)
        log.debug(_("IMAP metadata for %r: %r") % (folder, metadata), level=9)
        if metadata.has_key(folder) and ( \
            metadata[folder].has_key('/shared' + FOLDER_TYPE_ANNOTATION) and metadata[folder]['/shared' + FOLDER_TYPE_ANNOTATION].startswith(type) \
            or metadata[folder].has_key('/private' + FOLDER_TYPE_ANNOTATION) and metadata[folder]['/private' + FOLDER_TYPE_ANNOTATION].startswith(type)):
            result.append(folder)

            if metadata[folder].has_key('/private' + FOLDER_TYPE_ANNOTATION):
                # store default folder in user record
                if metadata[folder]['/private' + FOLDER_TYPE_ANNOTATION].endswith('.default'):
                    user_rec['_default_folder'] = folder

                # store confidential folder in user record
                if metadata[folder]['/private' + FOLDER_TYPE_ANNOTATION].endswith('.confidential') and not user_rec.has_key('_confidential_folder'):
                    user_rec['_confidential_folder'] = folder

    # cache with user record
    user_rec['_imap_folders'] = result

    return result


def find_existing_object(uid, type, user_rec, lock=False):
    """
        Search user's private folders for the given object (by UID+type)
    """
    global imap

    lock_key = None

    if lock:
        lock_key = get_lock_key(user_rec, uid)
        set_write_lock(lock_key)

    event = None
    for folder in list_user_folders(user_rec, type):
        log.debug(_("Searching folder %r for %s %r") % (folder, type, uid), level=8)
        imap.imap.m.select(imap.folder_utf7(folder))

        typ, data = imap.imap.m.search(None, '(UNDELETED HEADER SUBJECT "%s")' % (uid))
        for num in reversed(data[0].split()):
            typ, data = imap.imap.m.fetch(num, '(RFC822)')

            try:
                if type == 'task':
                    event = todo_from_message(message_from_string(data[0][1]))
                else:
                    event = event_from_message(message_from_string(data[0][1]))

                setattr(event, '_imap_folder', folder)
                setattr(event, '_lock_key', lock_key)
            except Exception, e:
                log.error(_("Failed to parse %s from message %s/%s: %s") % (type, folder, num, traceback.format_exc()))
                continue

            if event and event.uid == uid:
                return event

    if lock_key is not None:
        remove_write_lock(lock_key)

    return event


def check_availability(itip_event, receiving_user):
    """
        For the receiving user, determine if the event in question is in conflict.
    """

    start = time.time()
    num_messages = 0
    conflict = False

    # return previously detected conflict
    if itip_event.has_key('_conflicts'):
        return not itip_event['_conflicts']

    for folder in list_user_folders(receiving_user, 'event'):
        log.debug(_("Listing events from folder %r") % (folder), level=8)
        imap.imap.m.select(imap.folder_utf7(folder))

        typ, data = imap.imap.m.search(None, '(UNDELETED HEADER X-Kolab-Type "application/x-vnd.kolab.event")')
        num_messages += len(data[0].split())

        for num in reversed(data[0].split()):
            event = None
            typ, data = imap.imap.m.fetch(num, '(RFC822)')

            try:
                event = event_from_message(message_from_string(data[0][1]))
            except Exception, e:
                log.error(_("Failed to parse event from message %s/%s: %r") % (folder, num, e))
                continue

            if event and event.uid:
                conflict = check_event_conflict(event, itip_event)
                if conflict:
                    log.info(_("Existing event %r conflicts with invitation %r") % (event.uid, itip_event['uid']))
                    break

        if conflict:
            break

    end = time.time()
    log.debug(_("start: %r, end: %r, total: %r, messages: %d") % (start, end, (end-start), num_messages), level=9)

    # remember the result of this check for further iterations
    itip_event['_conflicts'] = conflict

    return not conflict


def set_write_lock(key, wait=True):
    """
        Set a write-lock for the given key and wait if such a lock already exists
    """
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)
    if not os.path.isdir(os.path.join(mybasepath, 'locks')):
        os.makedirs(os.path.join(mybasepath, 'locks'))

    file = os.path.join(mybasepath, 'locks', key + '.lock')
    locked = os.path.getmtime(file) if os.path.isfile(file) else 0
    expired = time.time() - 300

    # wait if file lock is in place
    while locked and locked > expired:
        if not wait:
            return False

        log.debug(_("%r is locked, waiting...") % (key), level=9)
        time.sleep(0.5)
        locked = os.path.getmtime(file) if os.path.isfile(file) else 0

    # touch the file
    if os.path.isfile(file):
        os.utime(file, None)
    else:
        open(file, 'w').close()

    # register active lock
    write_locks.append(key)

    return True


def remove_write_lock(key, update=True):
    """
        Remove the lock file for the given key
    """
    global write_locks

    if key is not None:
        file = os.path.join(mybasepath, 'locks', key + '.lock')
        if os.path.isfile(file):
            os.remove(file)
            if update:
                write_locks = [k for k in write_locks if not k == key]


def get_lock_key(user, uid):
    return hashlib.md5("%s/%s" % (user['mail'], uid)).hexdigest()


def update_object(object, user_rec):
    """
        Update the given object in IMAP (i.e. delete + append)
    """
    success = False

    if hasattr(object, '_imap_folder'):
        delete_object(object)
        object.set_lastmodified()  # update last-modified timestamp
        success = store_object(object, user_rec, object._imap_folder)

        # remove write lock for this event
        if hasattr(object, '_lock_key') and object._lock_key is not None:
            remove_write_lock(object._lock_key)

    return success


def store_object(object, user_rec, targetfolder=None):
    """
        Append the given object to the user's default calendar/tasklist
    """
    
    # find default calendar folder to save object to
    if targetfolder is None:
        targetfolder = list_user_folders(user_rec, object.type)[0]
        if user_rec.has_key('_default_folder'):
            targetfolder = user_rec['_default_folder']
        # use *.confidential folder for invitations classified as confidential
        if object.get_classification() == kolabformat.ClassConfidential and user_rec.has_key('_confidential_folder'):
            targetfolder = user_rec['_confidential_folder']

    if not targetfolder:
        log.error(_("Failed to save %s: no target folder found for user %r") % (object.type, user_rec['mail']))
        return Fasle

    log.debug(_("Save %s %r to user folder %r") % (object.type, object.uid, targetfolder), level=8)

    try:
        imap.imap.m.select(imap.folder_utf7(targetfolder))
        result = imap.imap.m.append(
            imap.folder_utf7(targetfolder),
            None,
            None,
            object.to_message(creator="Kolab Server <wallace@localhost>").as_string()
        )
        return result

    except Exception, e:
        log.error(_("Failed to save %s to user folder at %r: %r") % (
            object.type, targetfolder, e
        ))

    return False


def delete_object(existing):
    """
        Removes the IMAP object with the given UID from a user's folder
    """
    targetfolder = existing._imap_folder
    imap.imap.m.select(imap.folder_utf7(targetfolder))

    typ, data = imap.imap.m.search(None, '(HEADER SUBJECT "%s")' % existing.uid)

    log.debug(_("Delete %s %r in %r: %r") % (
        existing.type, existing.uid, targetfolder, data
    ), level=8)

    for num in data[0].split():
        imap.imap.m.store(num, '+FLAGS', '\\Deleted')

    imap.imap.m.expunge()


def send_update_notification(object, receiving_user, old=None, reply=True):
    """
        Send a (consolidated) notification about the current participant status to organizer
    """
    global auth

    import smtplib
    from email.MIMEText import MIMEText
    from email.Utils import formatdate

    # encode unicode strings with quoted-printable
    from email import charset
    charset.add_charset('utf-8', charset.SHORTEST, charset.QP)

    organizer = object.get_organizer()
    orgemail = organizer.email()
    orgname = organizer.name()

    if reply:
        log.debug(_("Compose participation status summary for %s %r to user %r") % (
            object.type, object.uid, receiving_user['mail']
        ), level=8)

        auto_replies_expected = 0
        auto_replies_received = 0
        partstats = { 'ACCEPTED':[], 'TENTATIVE':[], 'DECLINED':[], 'DELEGATED':[], 'IN-PROCESS':[], 'COMPLETED':[], 'PENDING':[] }
        for attendee in object.get_attendees():
            parstat = attendee.get_participant_status(True)
            if partstats.has_key(parstat):
                partstats[parstat].append(attendee.get_displayname())
            else:
                partstats['PENDING'].append(attendee.get_displayname())

            # look-up kolabinvitationpolicy for this attendee
            if attendee.get_cutype() == kolabformat.CutypeResource:
                resource_dns = auth.find_resource(attendee.get_email())
                if isinstance(resource_dns, list):
                    attendee_dn = resource_dns[0] if len(resource_dns) > 0 else None
                else:
                    attendee_dn = resource_dns
            else:
                attendee_dn = user_dn_from_email_address(attendee.get_email())

            if attendee_dn:
                attendee_rec = auth.get_entry_attributes(None, attendee_dn, ['kolabinvitationpolicy'])
                if is_auto_reply(attendee_rec, orgemail, object.type):
                    auto_replies_expected += 1
                    if not parstat == 'NEEDS-ACTION':
                        auto_replies_received += 1

        # skip notification until we got replies from all automatically responding attendees
        if auto_replies_received < auto_replies_expected:
            log.debug(_("Waiting for more automated replies (got %d of %d); skipping notification") % (
                auto_replies_received, auto_replies_expected
            ), level=8)
            return

        roundup = ''
        for status,attendees in partstats.iteritems():
            if len(attendees) > 0:
                roundup += "\n" + participant_status_label(status) + ":\n" + "\n".join(attendees) + "\n"
    else:
        roundup = "\n" + _("Changes submitted by %s have been automatically applied.") % (orgname if orgname else orgemail)

        # list properties changed from previous version
        if old:
            diff = xmlutils.compute_diff(old.to_dict(), object.to_dict())
            if len(diff) > 1:
                roundup += "\n"
                for change in diff:
                    if not change['property'] in ['created','lastmodified-date','sequence']:
                        new_value = xmlutils.property_to_string(change['property'], change['new']) if change['new'] else _("(removed)")
                        if new_value:
                            roundup += "\n- %s: %s" % (xmlutils.property_label(change['property']), new_value)

    # compose different notification texts for events/tasks
    if object.type == 'task':
        message_text = """
            The assignment for '%(summary)s' has been updated in your tasklist.
            %(roundup)s
        """ % {
            'summary': object.get_summary(),
            'roundup': roundup
        }
    else:
        message_text = """
            The event '%(summary)s' at %(start)s has been updated in your calendar.
            %(roundup)s
        """ % {
            'summary': object.get_summary(),
            'start': xmlutils.property_to_string('start', object.get_start()),
            'roundup': roundup
        }

    message_text += "\n" + _("*** This is an automated message. Please do not reply. ***")

    # compose mime message
    msg = MIMEText(utils.stripped_message(message_text), _charset='utf-8')

    msg['To'] = receiving_user['mail']
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = utils.str2unicode(_('"%s" has been updated') % (object.get_summary()))
    msg['From'] = utils.str2unicode('"%s" <%s>' % (orgname, orgemail) if orgname else orgemail)

    smtp = smtplib.SMTP("localhost", 10027)

    if conf.debuglevel > 8:
        smtp.set_debuglevel(True)

    try:
        smtp.sendmail(orgemail, receiving_user['mail'], msg.as_string())
    except Exception, e:
        log.error(_("SMTP sendmail error: %r") % (e))

    smtp.quit()


def send_cancel_notification(object, receiving_user):
    """
        Send a notification about event/task cancellation
    """
    import smtplib
    from email.MIMEText import MIMEText
    from email.Utils import formatdate

    # encode unicode strings with quoted-printable
    from email import charset
    charset.add_charset('utf-8', charset.SHORTEST, charset.QP)

    log.debug(_("Send cancellation notification for %s %r to user %r") % (
        object.type, object.uid, receiving_user['mail']
    ), level=8)

    organizer = object.get_organizer()
    orgemail = organizer.email()
    orgname = organizer.name()

    # compose different notification texts for events/tasks
    if object.type == 'task':
        message_text = """
            The assignment for '%(summary)s' has been cancelled by %(organizer)s.
            The copy in your tasklist as been marked as cancelled accordingly.
        """ % {
            'summary': object.get_summary(),
            'organizer': orgname if orgname else orgemail
        }
    else:
        message_text = """
            The event '%(summary)s' at %(start)s has been cancelled by %(organizer)s.
            The copy in your calendar as been marked as cancelled accordingly.
        """ % {
            'summary': object.get_summary(),
            'start': xmlutils.property_to_string('start', object.get_start()),
            'organizer': orgname if orgname else orgemail
        }

    message_text += "\n" + _("*** This is an automated message. Please do not reply. ***")

    # compose mime message
    msg = MIMEText(utils.stripped_message(message_text), _charset='utf-8')

    msg['To'] = receiving_user['mail']
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = utils.str2unicode(_('"%s" has been cancelled') % (object.get_summary()))
    msg['From'] = utils.str2unicode('"%s" <%s>' % (orgname, orgemail) if orgname else orgemail)

    smtp = smtplib.SMTP("localhost", 10027)

    if conf.debuglevel > 8:
        smtp.set_debuglevel(True)

    try:
        smtp.sendmail(orgemail, receiving_user['mail'], msg.as_string())
    except Exception, e:
        log.error(_("SMTP sendmail error: %r") % (e))

    smtp.quit()


def is_auto_reply(user, sender_email, type):
    accept_available = False
    accept_conflicts = False
    for policy in get_matching_invitation_policies(user, sender_email, object_type_conditons.get(type, COND_TYPE_EVENT)):
        if policy & (ACT_ACCEPT | ACT_REJECT | ACT_DELEGATE):
            if check_policy_condition(policy, True):
                accept_available = True
            if check_policy_condition(policy, False):
                accept_conflicts = True

        # we have both cases covered by a policy
        if accept_available and accept_conflicts:
            return True

        # manual action reached
        if policy & (ACT_MANUAL | ACT_SAVE_TO_FOLDER):
            return False

    return False


def check_policy_condition(policy, available):
    condition_fulfilled = True
    if policy & (COND_IF_AVAILABLE | COND_IF_CONFLICT):
        condition_fulfilled = available
    if policy & COND_IF_CONFLICT:
        condition_fulfilled = not condition_fulfilled
    return condition_fulfilled


def propagate_changes_to_attendees_accounts(object):
    """
        Find and update copies of this object in all attendee's personal folders
    """
    for attendee in object.get_attendees():
        attendee_user_dn = user_dn_from_email_address(attendee.get_email())
        if attendee_user_dn:
            attendee_user = auth.get_entry_attributes(None, attendee_user_dn, ['*'])
            attendee_object = find_existing_object(object.uid, object.type, attendee_user, True)  # does IMAP authenticate
            if attendee_object:
                try:
                    attendee_entry = attendee_object.get_attendee_by_email(attendee_user['mail'])
                except:
                    attendee_entry = None

                # copy all attendees from master object (covers additions and removals)
                new_attendees = kolabformat.vectorattendee();
                for a in object.get_attendees():
                    # keep my own entry intact
                    if attendee_entry is not None and attendee_entry.get_email() == a.get_email():
                        new_attendees.append(attendee_entry)
                    else:
                        new_attendees.append(a)

                attendee_object.event.setAttendees(new_attendees)

                success = update_object(attendee_object, attendee_user)
                log.debug(_("Updated %s's copy of %r: %r") % (attendee_user['mail'], object.uid, success), level=8)

            else:
                log.debug(_("Attendee %s's copy of %r not found") % (attendee_user['mail'], object.uid), level=8)

        else:
            log.debug(_("Attendee %r not found in LDAP") % (attendee.get_email()), level=8)


def invitation_response_text(type):
    footer = "\n\n" + _("*** This is an automated message. Please do not reply. ***")

    if type == 'task':
        return _("%(name)s has %(status)s your assignment for %(summary)s.") + footer
    else:
        return _("%(name)s has %(status)s your invitation for %(summary)s.") + footer
