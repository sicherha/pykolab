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
from pykolab.xml import event_from_message
from pykolab.itip import events_from_message
from pykolab.itip import check_event_conflict
from pykolab.itip import send_reply
from pykolab.translate import _

# define some contstants used in the code below
COND_IF_AVAILABLE  = 32
COND_IF_CONFLICT   = 64
COND_TENTATIVE     = 128
COND_NOTIFY        = 256
ACT_MANUAL         = 1
ACT_ACCEPT         = 2
ACT_DELEGATE       = 4
ACT_REJECT         = 8
ACT_UPDATE         = 16
ACT_TENTATIVE                = ACT_ACCEPT + COND_TENTATIVE
ACT_ACCEPT_IF_NO_CONFLICT    = ACT_ACCEPT + COND_IF_AVAILABLE
ACT_TENTATIVE_IF_NO_CONFLICT = ACT_ACCEPT + COND_TENTATIVE + COND_IF_AVAILABLE
ACT_DELEGATE_IF_CONFLICT     = ACT_DELEGATE + COND_IF_CONFLICT
ACT_REJECT_IF_CONFLICT       = ACT_REJECT + COND_IF_CONFLICT
ACT_UPDATE_AND_NOTIFY        = ACT_UPDATE + COND_NOTIFY
ACT_SAVE_TO_CALENDAR         = 512

FOLDER_TYPE_ANNOTATION = '/vendor/kolab/folder-type'

MESSAGE_PROCESSED = 1
MESSAGE_FORWARD   = 2

policy_name_map = {
    'ACT_MANUAL':                   ACT_MANUAL,
    'ACT_ACCEPT':                   ACT_ACCEPT,
    'ACT_ACCEPT_IF_NO_CONFLICT':    ACT_ACCEPT_IF_NO_CONFLICT,
    'ACT_TENTATIVE':                ACT_TENTATIVE,
    'ACT_TENTATIVE_IF_NO_CONFLICT': ACT_TENTATIVE_IF_NO_CONFLICT,
    'ACT_DELEGATE':                 ACT_DELEGATE,
    'ACT_DELEGATE_IF_CONFLICT':     ACT_DELEGATE_IF_CONFLICT,
    'ACT_REJECT':                   ACT_REJECT,
    'ACT_REJECT_IF_CONFLICT':       ACT_REJECT_IF_CONFLICT,
    'ACT_UPDATE':                   ACT_UPDATE,
    'ACT_UPDATE_AND_NOTIFY':        ACT_UPDATE_AND_NOTIFY,
    'ACT_SAVE_TO_CALENDAR':         ACT_SAVE_TO_CALENDAR
}

policy_value_map = dict([(v, k) for (k, v) in policy_name_map.iteritems()])

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/invitationpolicy/'

auth = None
imap = None

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
    global auth, imap

    log.debug("cleanup(): %r, %r" % (auth, imap), level=9)

    auth.disconnect()
    del auth

    # Disconnect IMAP or we lock the mailbox almost constantly
    imap.disconnect()
    del imap

def execute(*args, **kw):
    global auth, imap

    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT', 'REJECT', 'HOLD', 'DEFER' ]:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    log.debug(_("Invitation policy called for %r, %r") % (args, kw), level=9)

    auth = Auth()
    imap = IMAP()

    # TODO: Test for correct call.
    filepath = args[0]

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

    recipients = [address for displayname,address in getaddresses(message.get_all('X-Kolab-To'))]
    sender_email = [address for displayname,address in getaddresses(message.get_all('X-Kolab-From'))][0]

    any_itips = False
    recipient_email = None
    recipient_user_dn = None

    # An iTip message may contain multiple events. Later on, test if the message
    # is an iTip message by checking the length of this list.
    try:
        itip_events = events_from_message(message, ['REQUEST', 'REPLY', 'CANCEL'])
    except Exception, e:
        log.error(_("Failed to parse iTip events from message: %r" % (e)))
        itip_events = []

    if not len(itip_events) > 0:
        log.info(_("Message is not an iTip message or does not contain any (valid) iTip events."))

    else:
        any_itips = True
        log.debug(_("iTip events attached to this message contain the following information: %r") % (itip_events), level=9)

    # See if any iTip actually allocates a user.
    if any_itips and len([x['uid'] for x in itip_events if x.has_key('attendees') or x.has_key('organizer')]) > 0:
        auth.connect()

        for recipient in recipients:
            recipient_user_dn = user_dn_from_email_address(recipient)
            if recipient_user_dn is not None:
                recipient_email = recipient
                break

    if not any_itips:
        log.debug(_("No itips, no users, pass along %r") % (filepath), level=5)
        return filepath
    elif recipient_email is None:
        log.debug(_("iTips, but no users, pass along %r") % (filepath), level=5)
        return filepath

    # we're looking at the first itip event object
    itip_event = itip_events[0];

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
    sender_domain = str(sender_email).split('@')[-1]
    policies = get_matching_invitation_policies(receiving_user, sender_domain)

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
            log.debug(_("Apply invitation policy %r for domain %r") % (policy_value_map[policy], sender_domain), level=8)
            done = processor_func(itip_event, policy, recipient_email, sender_email, receiving_user)

            # matching policy found
            if done is not None:
                break

    else:
        log.debug(_("Ignoring '%s' iTip method") % (itip_event['method']), level=8)

    # message has been processed by the module, remove it
    if done == MESSAGE_PROCESSED:
        log.debug(_("iTip message %r consumed by the invitationpolicy module") % (message.get('Message-ID')), level=5)
        os.unlink(filepath)
        filepath = None

    cleanup()
    return filepath


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
    nonpart = receiving_attendee.get_role() == kolabformat.NonParticipant
    partstat = receiving_attendee.get_participant_status()
    save_event = not nonpart or not partstat == kolabformat.PartNeedsAction
    rsvp = receiving_attendee.get_rsvp()
    scheduling_required = rsvp or partstat == kolabformat.PartNeedsAction
    condition_fulfilled = True

    # find existing event in user's calendar
    existing = find_existing_event(itip_event, receiving_user)

    # compare sequence number to determine a (re-)scheduling request
    if existing is not None:
        log.debug(_("Existing event: %r") % (existing), level=9)
        scheduling_required = itip_event['sequence'] > 0 and itip_event['sequence'] >= existing.get_sequence()
        save_event = True

    # if scheduling: check availability
    if scheduling_required:
        if policy & (COND_IF_AVAILABLE | COND_IF_CONFLICT):
            condition_fulfilled = check_availability(itip_event, receiving_user)
        if policy & COND_IF_CONFLICT:
            condition_fulfilled = not condition_fulfilled

        log.debug(_("Precondition for event %r fulfilled: %r") % (itip_event['uid'], condition_fulfilled), level=5)

    # if RSVP, send an iTip REPLY
    if rsvp or scheduling_required:
        respond_with = None
        if policy & ACT_ACCEPT and condition_fulfilled:
            respond_with = 'TENTATIVE' if policy & COND_TENTATIVE else 'ACCEPTED'

        elif policy & ACT_REJECT and condition_fulfilled:
            respond_with = 'DECLINED'
            # TODO: only save declined invitation when a certain config option is set?

        elif policy & ACT_DELEGATE and condition_fulfilled:
            # TODO: delegate (but to whom?)
            return None

        # send iTip reply
        if respond_with is not None:
            # set attendee's CN from LDAP record if yet missing
            if not receiving_attendee.get_name() and receiving_user.has_key('cn'):
                receiving_attendee.set_name(receiving_user['cn'])

            receiving_attendee.set_participant_status(respond_with)
            send_reply(recipient_email, itip_event, invitation_response_text(),
                subject=_('"%(summary)s" has been %(status)s'))

        elif policy & ACT_SAVE_TO_CALENDAR:
            # copy the invitation into the user's calendar with unchanged PARTSTAT
            save_event = True

        else:
            # policy doesn't match, pass on to next one
            return None

    else:
        log.debug(_("No RSVP for recipient %r requested") % (receiving_user['mail']), level=8)
        # TODO: only update if policy & ACT_UPDATE ?

    if save_event:
        targetfolder = None

        if existing:
            # delete old version from IMAP
            targetfolder = existing._imap_folder
            delete_event(existing)

        if not nonpart or existing:
            # save new copy from iTip
            if store_event(itip_event['xml'], receiving_user, targetfolder):
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
        existing = find_existing_event(itip_event, receiving_user)

        if existing:
            log.debug(_("Auto-updating event %r on iTip REPLY") % (existing.uid), level=8)

            # TODO: compare sequence number to avoid outdated replies?
            try:
                existing.set_attendee_participant_status(sender_email, sender_attendee.get_participant_status())
            except Exception, e:
                log.error("Could not find corresponding attende in organizer's event: %r" % (e))

                # TODO: accept new participant if ACT_ACCEPT ?
                return MESSAGE_FORWARD

            # update the organizer's copy of the event
            if update_event(existing, receiving_user):
                if policy & COND_NOTIFY:
                    send_reply_notification(existing, receiving_user)

                # TODO: update all other attendee's copies if conf.get('wallace','invitationpolicy_autoupdate_other_attendees_on_reply'):
                return MESSAGE_PROCESSED

        else:
            log.error(_("The event referred by this reply was not found in the user's calendars. Forwarding to Inbox."))
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
        # find existing event in user's calendar
        existing = find_existing_event(itip_event, receiving_user)

        if existing:
            existing.set_status('CANCELLED')
            existing.set_transparency(True)
            if update_event(existing, receiving_user):
                # TODO: send cancellation notification if policy & ACT_UPDATE_AND_NOTIFY: ?
                return MESSAGE_PROCESSED

        else:
            log.error(_("The event referred by this reply was not found in the user's calendars. Forwarding to Inbox."))
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

    local_domains = auth.list_domains()

    if not local_domains == None:
        local_domains = list(set(local_domains.keys()))

    if not email_address.split('@')[1] in local_domains:
        return None

    log.debug(_("Checking if email address %r belongs to a local user") % (email_address), level=8)

    user_dn = auth.find_user_dn(email_address, True)

    if isinstance(user_dn, basestring):
        log.debug(_("User DN: %r") % (user_dn), level=8)
    else:
        log.debug(_("No user record(s) found for %r") % (email_address), level=9)

    auth.disconnect()

    return user_dn


def get_matching_invitation_policies(receiving_user, sender_domain):
    # get user's kolabInvitationPolicy settings
    policies = receiving_user['kolabinvitationpolicy'] if receiving_user.has_key('kolabinvitationpolicy') else []
    if policies and not isinstance(policies, list):
        policies = [policies]

    if len(policies) == 0:
        policies = conf.get_list('wallace', 'kolab_invitation_policy')

    # match policies agains the given sender_domain
    matches = []
    for p in policies:
        if ':' in p:
            (value, domain) = p.split(':')
        else:
            value = p
            domain = ''

        if domain == '' or domain == '*' or sender_domain.endswith(domain):
            value = value.upper()
            if policy_name_map.has_key(value):
                matches.append(policy_name_map[value])

    # add manual as default action
    if len(matches) == 0:
        matches.append(ACT_MANUAL)

    return matches


def imap_proxy_auth(user_rec):
    """
        
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


def list_user_calendars(user_rec):
    """
        Get a list of the given user's private calendar folders
    """
    global imap

    # return cached list
    if user_rec.has_key('_calendar_folders'):
        return user_rec['_calendar_folders'];

    calendars = []

    if not imap_proxy_auth(user_rec):
        return calendars

    folders = imap.list_folders('*')
    log.debug(_("List calendar folders for user %r: %r") % (user_rec['mail'], folders), level=8)

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
            metadata[folder].has_key('/shared' + FOLDER_TYPE_ANNOTATION) and metadata[folder]['/shared' + FOLDER_TYPE_ANNOTATION].startswith('event') \
            or metadata[folder].has_key('/private' + FOLDER_TYPE_ANNOTATION) and metadata[folder]['/private' + FOLDER_TYPE_ANNOTATION].startswith('event')):
            calendars.append(folder)

            # store default calendar folder in user record
            if metadata[folder].has_key('/private' + FOLDER_TYPE_ANNOTATION) and metadata[folder]['/private' + FOLDER_TYPE_ANNOTATION].endswith('.default'):
                user_rec['_default_calendar'] = folder

    # cache with user record
    user_rec['_calendar_folders'] = calendars

    return calendars


def find_existing_event(itip_event, user_rec):
    """
        Search user's calendar folders for the given event (by UID)
    """
    global imap

    event = None
    for folder in list_user_calendars(user_rec):
        log.debug(_("Searching folder %r for event %r") % (folder, itip_event['uid']), level=8)
        imap.imap.m.select(imap.folder_utf7(folder))

        typ, data = imap.imap.m.search(None, '(UNDELETED HEADER SUBJECT "%s")' % (itip_event['uid']))
        for num in reversed(data[0].split()):
            typ, data = imap.imap.m.fetch(num, '(RFC822)')

            try:
                event = event_from_message(message_from_string(data[0][1]))
                setattr(event, '_imap_folder', folder)
            except Exception, e:
                log.error(_("Failed to parse event from message %s/%s: %r") % (folder, num, e))
                continue

            if event and event.uid == itip_event['uid']:
                return event

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

    for folder in list_user_calendars(receiving_user):
        log.debug(_("Listing events from folder %r") % (folder), level=8)
        imap.imap.m.select(imap.folder_utf7(folder))

        typ, data = imap.imap.m.search(None, '(UNDELETED HEADER X-Kolab-Type "application/x-vnd.kolab.event")')
        num_messages += len(data[0].split())

        for num in reversed(data[0].split()):
            event = None
            typ, data = imap.imap.m.fetch(num, '(RFC822)')

            try:
                event = event_from_message(message_from_string(data[0][1]))
                setattr(event, '_imap_folder', folder)
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


def update_event(event, user_rec):
    """
        Update the given event in IMAP (i.e. delete + append)
    """
    if hasattr(event, '_imap_folder'):
        delete_event(event)
        return store_event(event, user_rec, event._imap_folder)

    return False


def store_event(event, user_rec, targetfolder=None):
    """
        Append the given event object to the user's default calendar
    """

    # find default calendar folder to save event to
    if targetfolder is None:
        targetfolder = list_user_calendars(user_rec)[0]
        if user_rec.has_key('_default_calendar'):
            targetfolder = user_rec['_default_calendar']

    if not targetfolder:
        log.error(_("Failed to save event: no calendar folder found for user %r") % (user_rec['mail']))
        return Fasle

    log.debug(_("Save event %r to user calendar %r") % (event.uid, targetfolder), level=8)

    try:
        imap.imap.m.select(imap.folder_utf7(targetfolder))
        result = imap.imap.m.append(
            imap.folder_utf7(targetfolder),
            None,
            None,
            event.to_message().as_string()
        )
        return result

    except Exception, e:
        log.error(_("Failed to save event to user calendar at %r: %r") % (
            targetfolder, e
        ))

    return False


def delete_event(existing):
    """
        Removes the IMAP object with the given UID from a user's calendar folder
    """
    targetfolder = existing._imap_folder
    imap.imap.m.select(imap.folder_utf7(targetfolder))

    typ, data = imap.imap.m.search(None, '(HEADER SUBJECT "%s")' % existing.uid)

    log.debug(_("Delete event %r in %r: %r") % (
        existing.uid, targetfolder, data
    ), level=8)

    for num in data[0].split():
        imap.imap.m.store(num, '+FLAGS', '\\Deleted')

    imap.imap.m.expunge()


def send_reply_notification(event, receiving_user):
    """
        Send a (consolidated) notification about the current participant status to organizer
    """
    import smtplib
    from email.MIMEText import MIMEText
    from email.Utils import formatdate

    log.debug(_("Compose participation status summary for event %r to user %r") % (
        event.uid, receiving_user['mail']
    ), level=8)

    partstats = { 'ACCEPTED':[], 'TENTATIVE':[], 'DECLINED':[], 'DELEGATED':[], 'PENDING':[] }
    for attendee in event.get_attendees():
        parstat = attendee.get_participant_status(True)
        if partstats.has_key(parstat):
            partstats[parstat].append(attendee.get_displayname())
        else:
            partstats['PENDING'].append(attendee.get_displayname())

    # TODO: for every attendee, look-up its kolabinvitationpolicy and skip notification
    # until we got replies from all automatically responding attendees

    roundup = ''
    for status,attendees in partstats.iteritems():
        if len(attendees) > 0:
            roundup += "\n" + _(status) + ":\n" + "\n".join(attendees) + "\n"

    message_text = """
        The event '%(summary)s' at %(start)s has been updated in your calendar.
        %(roundup)s
    """ % {
        'summary': event.get_summary(),
        'start': event.get_start().strftime('%Y-%m-%d %H:%M %Z'),
        'roundup': roundup
    }

    # compose mime message
    msg = MIMEText(utils.stripped_message(message_text))

    msg['To'] = receiving_user['mail']
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = _('"%s" has been updated') % (event.get_summary())

    organizer = event.get_organizer()
    orgemail = organizer.email()
    orgname = organizer.name()

    msg['From'] = '"%s" <%s>' % (orgname, orgemail) if orgname else orgemail

    smtp = smtplib.SMTP("localhost", 10027)

    if conf.debuglevel > 8:
        smtp.set_debuglevel(True)

    smtp.sendmail(orgemail, receiving_user['mail'], msg.as_string())
    smtp.quit()


def invitation_response_text():
    return _("""
        %(name)s has %(status)s your invitation for %(summary)s.

        *** This is an automated response sent by the Kolab Invitation system ***
    """)
