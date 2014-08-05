# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
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
import icalendar
import os
import pytz
import random
import tempfile
import time
from urlparse import urlparse
import urllib
import uuid
import re

from email import message_from_string
from email.parser import Parser
from email.utils import formataddr
from email.utils import getaddresses

import modules

import pykolab
import kolabformat

from pykolab.auth import Auth
from pykolab.conf import Conf
from pykolab.imap import IMAP
from pykolab.xml import to_dt
from pykolab.xml import event_from_message
from pykolab.xml import participant_status_label
from pykolab.itip import events_from_message
from pykolab.itip import check_event_conflict
from pykolab.translate import _

# define some contstants used in the code below
COND_NOTIFY = 256
ACT_MANUAL  = 1
ACT_ACCEPT  = 2
ACT_ACCEPT_AND_NOTIFY = ACT_ACCEPT + COND_NOTIFY

policy_name_map = {
    'ACT_MANUAL':            ACT_MANUAL,
    'ACT_ACCEPT':            ACT_ACCEPT,
    'ACT_ACCEPT_AND_NOTIFY': ACT_ACCEPT_AND_NOTIFY
}

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/resources/'

auth = None
imap = None

def __init__():
    modules.register('resources', execute, description=description())

def accept(filepath):
    new_filepath = os.path.join(
            mybasepath,
            'ACCEPT',
            os.path.basename(filepath)
        )

    cleanup()
    os.rename(filepath, new_filepath)
    filepath = new_filepath
    exec('modules.cb_action_ACCEPT(%r, %r)' % ('resources',filepath))

def description():
    return """Resource management module."""

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

    # (re)set language to default
    pykolab.translate.setUserLanguage(conf.get('kolab','default_locale'))

    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT', 'REJECT', 'HOLD', 'DEFER' ]:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    log.debug(_("Resource Management called for %r, %r") % (args, kw), level=9)

    auth = Auth()
    imap = IMAP()

    # TODO: Test for correct call.
    filepath = args[0]

    if kw.has_key('stage'):
        log.debug(
                _("Issuing callback after processing to stage %s") % (
                        kw['stage']
                    ),
                level=8
            )

        log.debug(_("Testing cb_action_%s()") % (kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' % (kw['stage'])):
            log.debug(
                    _("Attempting to execute cb_action_%s()") % (kw['stage']),
                    level=8
                )

            exec(
                    'modules.cb_action_%s(%r, %r)' % (
                            kw['stage'],
                            'resources',
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
    any_resources = False
    possibly_any_resources = True
    reference_uid = None

    # An iTip message may contain multiple events. Later on, test if the message
    # is an iTip message by checking the length of this list.
    try:
        itip_events = events_from_message(message, ['REQUEST', 'REPLY', 'CANCEL'])
    except Exception, e:
        log.error(_("Failed to parse iTip events from message: %r" % (e)))
        itip_events = []

    if not len(itip_events) > 0:
        log.info(
                _("Message is not an iTip message or does not contain any " + \
                    "(valid) iTip.")
            )

    else:
        any_itips = True

        log.debug(
                _("iTip events attached to this message contain the " + \
                    "following information: %r") % (itip_events),
                level=9
            )

    if any_itips:
        # See if any iTip actually allocates a resource.
        if len([x['resources'] for x in itip_events if x.has_key('resources')]) == 0:
            if len([x['attendees'] for x in itip_events if x.has_key('attendees')]) == 0:
                possibly_any_resources = False
        else:
            possibly_any_resources = False

    if possibly_any_resources:
        auth.connect()

        for recipient in recipients:
            # extract reference UID from recipients like resource+UID@domain.org
            if re.match('.+\+[A-Za-z0-9%/_-]+@', recipient):
                (prefix, host) = recipient.split('@')
                (local, reference_uid) = prefix.split('+')
                recipient = local + '@' + host

            if not len(resource_record_from_email_address(recipient)) == 0:
                resource_recipient = recipient
                any_resources = True

    if any_resources:
        if not any_itips:
            log.debug(_("Not an iTip message, but sent to resource nonetheless. Reject message"), level=5)
            reject(filepath)
            return False
        else:
            # Continue. Resources and iTips. We like.
            pass
    else:
        if not any_itips:
            log.debug(_("No itips, no resources, pass along %r") % (filepath), level=5)
            return filepath
        else:
            log.debug(_("iTips, but no resources, pass along %r") % (filepath), level=5)
            return filepath

    # A simple list of merely resource entry IDs that hold any relevance to the
    # iTip events
    resource_dns = resource_records_from_itip_events(itip_events, resource_recipient)

    # check if resource attendees match the envelope recipient
    if len(resource_dns) == 0:
        log.info(_("No resource attendees matching envelope recipient %s, Reject message") % (resource_recipient))
        log.debug("%r" % (itip_events), level=8)
        reject(filepath)
        return False


    # Get the resource details, which includes details on the IMAP folder
    # This may append resource collection members to recource_dns
    resources = get_resource_records(resource_dns)

    log.debug(_("Resources: %r; %r") % (resource_dns, resources), level=8)

    imap.connect()

    done = False
    receiving_resource = resources[resource_dns[0]]

    for itip_event in itip_events:
        if itip_event['method'] == 'REPLY':
            done = True

            # find initial reservation referenced by the reply
            if reference_uid:
                event = find_existing_event(reference_uid, receiving_resource)
                if event:
                    try:
                        sender_attendee = itip_event['xml'].get_attendee_by_email(sender_email)
                        owner_reply = sender_attendee.get_participant_status()
                        log.debug(_("Sender Attendee: %r => %r") % (sender_attendee, owner_reply), level=9)
                    except Exception, e:
                        log.error("Could not find envelope sender attendee: %r" % (e))
                        continue

                    # forward owner response comment
                    comment = itip_event['xml'].get_comment()
                    if comment:
                        event.set_comment(str(comment))

                    itip_event_ = dict(xml=event, uid=event.get_uid())

                    if owner_reply == kolabformat.PartAccepted:
                        accept_reservation_request(itip_event_, receiving_resource, confirmed=True)
                    elif owner_reply == kolabformat.PartDeclined:
                        decline_reservation_request(itip_event_, receiving_resource)
                        # TODO: set partstat=DECLINED and status=CANCELLED instead of deleting?
                        delete_resource_event(reference_uid, receiving_resource)
                    else:
                        log.info("Invalid response (%r) recieved from resource owner for event %r" % (
                            sender_attendee.get_participant_status(True), reference_uid
                        ))
                else:
                    log.info(_("Event referenced by this REPLY (%r) not found in resource calendar") % (reference_uid))

            # exit for-loop
            break

        # else:

        try:
            receiving_attendee = itip_event['xml'].get_attendee_by_email(receiving_resource['mail'])
            log.debug(_("Receiving Resource: %r; %r") % (receiving_resource, receiving_attendee), level=9)
        except Exception, e:
            log.error("Could not find envelope attendee: %r" % (e))
            continue

        # ignore updates and cancellations to resource collections who already delegated the event
        if receiving_attendee.get_delegated_to().size() > 0 or receiving_attendee.get_role() == kolabformat.NonParticipant:
            done = True
            log.debug(_("Recipient %r is non-participant, ignoring message") % (receiving_resource['mail']), level=8)

        # process CANCEL messages
        if not done and itip_event['method'] == "CANCEL":
            for resource in resource_dns:
                if resources[resource]['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                    delete_resource_event(itip_event['uid'], resources[resource])

            done = True

    if done:
        os.unlink(filepath)
        cleanup()
        return


    # do the magic for the receiving attendee
    (available_resource, itip_event) = check_availability(itip_events, resource_dns, resources, receiving_attendee)

    # accept reservation
    if available_resource is not None:
        if available_resource['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
            # replace existing copy of this event
            if len(available_resource['existing_events']) > 0:
                for uid in available_resource['existing_events']:
                    delete_resource_event(uid, available_resource)

            log.debug(_("Accept invitation for individual resource %r / %r") % (available_resource['dn'], available_resource['mail']), level=8)

            # check if reservation was delegated
            original_resource = None
            if available_resource['mail'] != receiving_resource['mail'] and receiving_attendee.get_participant_status() == kolabformat.PartDelegated:
                original_resource = receiving_resource

            accept_reservation_request(itip_event, available_resource, original_resource)

        else:
            # This must have been a resource collection originally.
            # We have inserted the reference to the original resource
            # record in 'memberof'.
            if available_resource.has_key('memberof'):
                original_resource = resources[available_resource['memberof']]

                if original_resource['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                    #
                    # Delegate:
                    # - delegator: the original resource collection
                    # - delegatee: the target resource
                    #
                    itip_event['xml'].delegate(original_resource['mail'], available_resource['mail'], available_resource['cn'])

                    # set delegator to NON-PARTICIPANT and RSVP=FALSE
                    delegator = itip_event['xml'].get_attendee_by_email(original_resource['mail'])
                    delegator.set_role(kolabformat.NonParticipant)
                    delegator.set_rsvp(False)

                    log.debug(_("Delegate invitation for resource collection %r to %r") % (original_resource['mail'], available_resource['mail']), level=8)
                    accept_reservation_request(itip_event, available_resource, original_resource)

    # decline reservation
    else:
        resource = resources[resource_dns[0]]  # this is the receiving resource record
        decline_reservation_request(itip_event, resource)

    cleanup()

    os.unlink(filepath)


def check_availability(itip_events, resource_dns, resources, receiving_attendee=None):
    """
        For each resource, determine if any of the events in question are in conflict.
    """

    # Store the (first) conflicting event(s) alongside the resource information.
    start = time.time()
    num_messages = 0
    available_resource = None

    for resource in resources.keys():
        # skip this for resource collections
        if not resources[resource].has_key('kolabtargetfolder'):
            continue

        # sets the 'conflicting' flag and adds a list of conflicting events found
        try:
            num_messages += read_resource_calendar(resources[resource], itip_events)
        except Exception, e:
            log.error(_("Failed to read resource calendar for %r: %r") % (resource, e))

    end = time.time()

    log.debug(_("start: %r, end: %r, total: %r, messages: %d") % (start, end, (end-start), num_messages), level=9)


    # For each resource (collections are first!)
    # check conflicts and either accept or decline the reservation request
    for resource in resource_dns:
        log.debug(_("Polling for resource %r") % (resource), level=9)

        if not resources.has_key(resource):
            log.debug(_("Resource %r has been popped from the list") % (resource), level=9)
            continue

        if not resources[resource].has_key('conflicting_events'):
            log.debug(_("Resource is a collection"), level=9)

            # check if there are non-conflicting collection members
            conflicting_members = [x for x in resources[resource]['uniquemember'] if resources[x]['conflict']]

            # found at least one non-conflicting member, remove the conflicting ones and continue
            if len(conflicting_members) < len(resources[resource]['uniquemember']):
                for member in conflicting_members:
                    resources[resource]['uniquemember'] = [x for x in resources[resource]['uniquemember'] if x != member]
                    del resources[member]

                log.debug(_("Removed conflicting resources from %r: (%r) => %r") % (
                    resource, conflicting_members, resources[resource]['uniquemember']
                ), level=9)

            else:
                # TODO: shuffle existing bookings of collection members in order
                # to make one availale for the requested time
                pass

            continue

        if len(resources[resource]['conflicting_events']) > 0:
            log.debug(_("Conflicting events: %r for resource %r") % (resources[resource]['conflicting_events'], resource), level=9)

            # This is the event being conflicted with!
            for itip_event in itip_events:
                # Now we have the event that was conflicting
                if resources[resource]['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                    # this resource initially was delegated from a collection ?
                    if receiving_attendee and receiving_attendee.get_email() == resources[resource]['mail'] \
                            and len(receiving_attendee.get_delegated_from()) > 0:
                        for delegator in receiving_attendee.get_delegated_from():
                            collection_data = get_resource_collection(delegator.email())
                            if collection_data is not None:
                                # check if another collection member is available
                                (available_resource, dummy) = check_availability(itip_events, collection_data[0], collection_data[1])
                                break

                        if available_resource is not None:
                            log.debug(_("Delegate to another resource collection member: %r to %r") % \
                                (resources[resource]['mail'], available_resource['mail']), level=8)

                            # set this new resource as delegate for the receiving_attendee
                            itip_event['xml'].delegate(resources[resource]['mail'], available_resource['mail'], available_resource['cn'])

                            # set delegator to NON-PARTICIPANT and RSVP=FALSE
                            receiving_attendee.set_role(kolabformat.NonParticipant)
                            receiving_attendee.set_rsvp(False)
                            receiving_attendee.setDelegatedFrom([])

                            # remove existing_events as we now delegated back to the collection
                            if len(resources[resource]['existing_events']) > 0:
                                for uid in resources[resource]['existing_events']:
                                    delete_resource_event(uid, resources[resource])

                    done = True

                if done:
                    break

        else:
            # No conflicts, go accept
            for itip_event in itip_events:
                # directly invited resource
                if resources[resource]['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                    available_resource = resources[resource]
                    done = True

                else:
                    # This must have been a resource collection originally.
                    # We have inserted the reference to the original resource
                    # record in 'memberof'.
                    if resources[resource].has_key('memberof'):
                        original_resource = resources[resources[resource]['memberof']]

                        # Randomly select a target resource from the resource collection.
                        available_resource = resources[original_resource['uniquemember'][random.randint(0,(len(original_resource['uniquemember'])-1))]]
                        done = True

        if done:
            break

    # end for resource in resource_dns:

    return (available_resource, itip_event)


def read_resource_calendar(resource_rec, itip_events):
    """
        Read all booked events from the given resource's calendar
        and check for conflicts with the given list if itip events
    """
    global imap

    resource_rec['conflict'] = False
    resource_rec['conflicting_events'] = []
    resource_rec['existing_events'] = []

    mailbox = resource_rec['kolabtargetfolder']

    log.debug(
        _("Checking events in resource folder %r") % (mailbox),
        level=9
    )

    # might raise an exception, let that bubble
    imap.imap.m.select(imap.folder_quote(mailbox))
    typ, data = imap.imap.m.search(None, 'ALL')

    num_messages = len(data[0].split())

    for num in data[0].split():
        # For efficiency, makes the routine non-deterministic
        if resource_rec['conflict']:
            continue

        log.debug(
            _("Fetching message UID %r from folder %r") % (num, mailbox),
            level=9
        )

        typ, data = imap.imap.m.fetch(num, '(RFC822)')

        event_message = message_from_string(data[0][1])

        try:
            event = event_from_message(message_from_string(data[0][1]))
        except Exception, e:
            log.error(_("Failed to parse event from message %s/%s: %r") % (mailbox, num, e))
            continue

        if event:
            for itip in itip_events:
                conflict = check_event_conflict(event, itip)

                if event.get_uid() == itip['uid']:
                    resource_rec['existing_events'].append(itip['uid'])

                if conflict:
                    log.info(
                        _("Event %r conflicts with event %r") % (
                            itip['xml'].get_uid(),
                            event.get_uid()
                        )
                    )

                    resource_rec['conflicting_events'].append(event.get_uid())
                    resource_rec['conflict'] = True

    return num_messages


def find_existing_event(uid, resource_rec):
    """
        Search the resources's calendar folder for the given event (by UID)
    """
    global imap

    event = None
    mailbox = resource_rec['kolabtargetfolder']

    log.debug(_("Searching %r for event %r") % (mailbox, uid), level=9)

    try:
        imap.imap.m.select(imap.folder_quote(mailbox))
        typ, data = imap.imap.m.search(None, '(UNDELETED HEADER SUBJECT "%s")' % (uid))
    except Exception, e:
        log.error(_("Failed to access resource calendar:: %r") % (e))
        return event

    for num in reversed(data[0].split()):
        typ, data = imap.imap.m.fetch(num, '(RFC822)')

        try:
            event = event_from_message(message_from_string(data[0][1]))
        except Exception, e:
            log.error(_("Failed to parse event from message %s/%s: %r") % (mailbox, num, e))
            continue

        if event and event.uid == uid:
            return event

    return event


def accept_reservation_request(itip_event, resource, delegator=None, confirmed=False):
    """
        Accepts the given iTip event by booking it into the resource's
        calendar. Then set the attendee status of the given resource to
        ACCEPTED and sends an iTip reply message to the organizer.
    """
    owner = get_resource_owner(resource)
    confirmation_required = False

    if not confirmed:
        invitationpolicy = get_resource_invitationpolicy(resource)
        log.debug(_("Apply invitation policies %r") % (invitationpolicy), level=9)

        if invitationpolicy is not None:
            for policy in invitationpolicy:
                if policy & ACT_MANUAL and owner['mail']:
                    confirmation_required = True
                    break

    partstat = 'TENTATIVE' if confirmation_required else 'ACCEPTED'

    itip_event['xml'].set_attendee_participant_status(
        itip_event['xml'].get_attendee_by_email(resource['mail']),
        partstat
    )

    # remove old copy of the reservation
    if confirmed:
        delete_resource_event(itip_event['uid'], resource)

    saved = save_resource_event(itip_event, resource)

    log.debug(
        _("Adding event to %r: %r") % (resource['kolabtargetfolder'], saved),
        level=8
    )

    if saved:
        send_response(delegator['mail'] if delegator else resource['mail'], itip_event, owner)

    if owner and confirmation_required:
        send_owner_confirmation(resource, owner, itip_event)
    elif owner:
        send_owner_notification(resource, owner, itip_event, saved)


def decline_reservation_request(itip_event, resource):
    """
        Set the attendee status of the given resource to
        DECLINED and send an according iTip reply to the organizer.
    """

    itip_event['xml'].set_attendee_participant_status(
        itip_event['xml'].get_attendee_by_email(resource['mail']),
        "DECLINED"
    )

    owner = get_resource_owner(resource)
    send_response(resource['mail'], itip_event, get_resource_owner(resource))

    if owner:
        send_owner_notification(resource, owner, itip_event, True)


def save_resource_event(itip_event, resource):
    """
        Append the given event object to the resource's calendar
    """
    try:
        # Administrator login name comes from configuration.
        targetfolder = imap.folder_quote(resource['kolabtargetfolder'])
        imap.imap.m.setacl(targetfolder, conf.get(conf.get('kolab', 'imap_backend'), 'admin_login'), "lrswipkxtecda")
        result = imap.imap.m.append(
            targetfolder,
            None,
            None,
            itip_event['xml'].to_message().as_string()
        )
        return result

    except Exception, e:
        log.error(_("Failed to save event to resource calendar at %r: %r") % (
            resource['kolabtargetfolder'], e
        ))

    return False


def delete_resource_event(uid, resource):
    """
        Removes the IMAP object with the given UID from a resource's calendar folder
    """
    targetfolder = imap.folder_quote(resource['kolabtargetfolder'])
    imap.imap.m.setacl(targetfolder, conf.get(conf.get('kolab', 'imap_backend'), 'admin_login'), "lrswipkxtecda")
    imap.imap.m.select(targetfolder)

    typ, data = imap.imap.m.search(None, '(HEADER SUBJECT "%s")' % uid)

    log.debug(_("Delete resource calendar object %r in %r: %r") % (
        uid, resource['kolabtargetfolder'], data
    ), level=9)

    for num in data[0].split():
        imap.imap.m.store(num, '+FLAGS', '\\Deleted')

    imap.imap.m.expunge()


def reject(filepath):
    new_filepath = os.path.join(
            mybasepath,
            'REJECT',
            os.path.basename(filepath)
        )

    os.rename(filepath, new_filepath)
    filepath = new_filepath
    exec('modules.cb_action_REJECT(%r, %r)' % ('resources',filepath))


def resource_record_from_email_address(email_address):
    """
        Resolves the given email address to a resource entity
    """
    global auth

    if not auth:
        auth = Auth()
        auth.connect()

    resource_records = []

    local_domains = auth.list_domains()

    if not local_domains == None:
        local_domains = list(set(local_domains.keys()))

    if not email_address.split('@')[1] in local_domains:
        return []

    log.debug(
        _("Checking if email address %r belongs to a resource (collection)") % (email_address),
        level=8
    )

    resource_records = auth.find_resource(email_address)

    if isinstance(resource_records, list):
        if len(resource_records) > 0:
            log.debug(_("Resource record(s): %r") % (resource_records), level=8)
        else:
            log.debug(_("No resource (collection) records found for %r") % (email_address), level=9)

    elif isinstance(resource_records, basestring):
        resource_records = [ resource_records ]
        log.debug(_("Resource record: %r") % (resource_records), level=8)

    auth.disconnect()

    return resource_records


def resource_records_from_itip_events(itip_events, recipient_email=None):
    """
        Given a list of itip_events, determine which resources have been
        invited as attendees and/or resources.
    """
    global auth

    if not auth:
        auth = Auth()
        auth.connect()

    resource_records = []

    log.debug(_("Raw itip_events: %r") % (itip_events), level=9)
    attendees_raw = []
    for list_attendees_raw in [x for x in [y['attendees'] for y in itip_events if y.has_key('attendees') and isinstance(y['attendees'], list)]]:
        attendees_raw.extend(list_attendees_raw)

    for list_attendees_raw in [y['attendees'] for y in itip_events if y.has_key('attendees') and isinstance(y['attendees'], basestring)]:
        attendees_raw.append(list_attendees_raw)

    log.debug(_("Raw set of attendees: %r") % (attendees_raw), level=9)

    # TODO: Resources are actually not implemented in the format. We reset this
    # list later.
    resources_raw = []
    for list_resources_raw in [x for x in [y['resources'] for y in itip_events if y.has_key('resources')]]:
        resources_raw.extend(list_resources_raw)

    log.debug(_("Raw set of resources: %r") % (resources_raw), level=9)

    # consider organizer (in REPLY messages), too
    organizers_raw = [re.sub('\+[A-Za-z0-9%/_-]+@', '@', str(y['organizer'])) for y in itip_events if y.has_key('organizer')]

    log.debug(_("Raw set of organizers: %r") % (organizers_raw), level=8)


    # TODO: We expect the format of an attendee line to literally be:
    #
    #   ATTENDEE:RSVP=TRUE;ROLE=REQ-PARTICIPANT;MAILTO:lydia.bossers@kolabsys.com
    #
    # which makes the attendees_raw contain:
    #
    #   RSVP=TRUE;ROLE=REQ-PARTICIPANT;MAILTO:lydia.bossers@kolabsys.com
    #
    attendees = [x.split(':')[-1] for x in attendees_raw + organizers_raw]

    # Limit the attendee resources to the one that is actually invited
    # with the current message. Considering all invited resources would result in
    # duplicate responses from every iTip message sent to a resource.
    if recipient_email is not None:
        attendees = [a for a in attendees if a == recipient_email]

    for attendee in attendees:
        log.debug(_("Checking if attendee %r is a resource (collection)") % (attendee), level=8)

        _resource_records = auth.find_resource(attendee)

        if isinstance(_resource_records, list):
            if len(_resource_records) > 0:
                resource_records.extend(_resource_records)
                log.debug(_("Resource record(s): %r") % (_resource_records), level=8)
            else:
                log.debug(_("No resource (collection) records found for %r") % (attendee), level=9)

        elif isinstance(_resource_records, basestring):
            resource_records.append(_resource_records)
            log.debug(_("Resource record: %r") % (_resource_records), level=8)

        else:
            log.warning(_("Resource reservation made but no resource records found"))

    # Escape the non-implementation of the free-form, undefined RESOURCES
    # list(s) in iTip.
    if len(resource_records) == 0:

        # TODO: We don't know how to handle this yet!
        # We expect the format of an resource line to literally be:
        #   RESOURCES:MAILTO:resource-car@kolabsys.com
        resources_raw = []

        resources = [x.split(':')[-1] for x in resources_raw]

        # Limit the attendee resources to the one that is actually invited
        # with the current message.
        if recipient_email is not None:
            resources = [a for a in resources if a == recipient_email]

        for resource in resources:
            log.debug(_("Checking if resource %r is a resource (collection)") % (resource), level=8)

            _resource_records = auth.find_resource(resource)
            if isinstance(_resource_records, list):
                if len(_resource_records) > 0:
                    resource_records.extend(_resource_records)
                    log.debug(_("Resource record(s): %r") % (_resource_records), level=8)

                else:
                    log.debug(_("No resource (collection) records found for %r") % (resource), level=8)

            elif isinstance(_resource_records, basestring):
                resource_records.append(_resource_records)
                log.debug(_("Resource record: %r") % (_resource_records), level=8)
            else:
                log.warning(_("Resource reservation made but no resource records found"))


    log.debug(_("The following resources are being referred to in the " + \
                "iTip: %r") % (resource_records), level=8)

    return resource_records


def get_resource_records(resource_dns):
    """
        Get the resource details, which includes details on the IMAP folder
    """
    global auth

    resources = {}
    for resource_dn in list(set(resource_dns)):
        # Get the attributes for the record
        # See if it is a resource collection
        #   If it is, expand to individual resources
        #   If it is not, ...
        resource_attrs = auth.get_entry_attributes(None, resource_dn, ['*'])
        resource_attrs['dn'] = resource_dn
        parse_kolabinvitationpolicy(resource_attrs)

        if not 'kolabsharedfolder' in [x.lower() for x in resource_attrs['objectclass']]:
            if resource_attrs.has_key('uniquemember'):
                resources[resource_dn] = resource_attrs
                for uniquemember in resource_attrs['uniquemember']:
                    member_attrs = auth.get_entry_attributes(
                            None,
                            uniquemember,
                            ['*']
                        )

                    if 'kolabsharedfolder' in [x.lower() for x in member_attrs['objectclass']]:
                        member_attrs['dn'] = uniquemember
                        parse_kolabinvitationpolicy(member_attrs, resource_attrs)

                        resources[uniquemember] = member_attrs
                        resources[uniquemember]['memberof'] = resource_dn
                        if not member_attrs.has_key('owner') and resources[resource_dn].has_key('owner'):
                            resources[uniquemember]['owner'] = resources[resource_dn]['owner']
                        resource_dns.append(uniquemember)
        else:
            resources[resource_dn] = resource_attrs

    return resources


def parse_kolabinvitationpolicy(attrs, parent=None):
    if attrs.has_key('kolabinvitationpolicy'):
        if not isinstance(attrs['kolabinvitationpolicy'], list):
            attrs['kolabinvitationpolicy'] = [attrs['kolabinvitationpolicy']]
        attrs['kolabinvitationpolicy'] = [policy_name_map[p] for p in attrs['kolabinvitationpolicy'] if policy_name_map.has_key(p)]

    elif isinstance(parent, dict) and parent.has_key('kolabinvitationpolicy'):
        attrs['kolabinvitationpolicy'] = parent['kolabinvitationpolicy']


def get_resource_collection(email_address):
    """
        
    """
    resource_dns = resource_record_from_email_address(email_address)
    if len(resource_dns) == 1:
        resource_attrs = auth.get_entry_attributes(None, resource_dns[0], ['objectclass'])
        if not 'kolabsharedfolder' in [x.lower() for x in resource_attrs['objectclass']]:
            resources = get_resource_records(resource_dns)
            return (resource_dns, resources)

    return None


def get_resource_owner(resource):
    """
        Get this resource's owner record
    """
    global auth

    if not auth:
        auth = Auth()
        auth.connect()

    owners = []

    if resource.has_key('owner'):
        if not isinstance(resource['owner'], list):
            owners = [ resource['owner'] ]
        else:
            owners = resource['owner']

    else:
        # get owner attribute from collection
        collections = auth.search_entry_by_attribute('uniquemember', resource['dn'])
        if not isinstance(collections, list):
            collections = [ collections ]

        for dn,collection in collections:
            if collection.has_key('owner') and isinstance(collection['owner'], list):
                owners += collection['owner']
            elif collection.has_key('owner'):
                owners.append(collection['owner'])

    for dn in owners:
        owner = auth.get_entry_attributes(None, dn, ['cn','mail','telephoneNumber'])
        if owner is not None:
            return owner

    return None


def get_resource_invitationpolicy(resource):
    """
        Get this resource's kolabinvitationpolicy configuration
    """
    global auth

    if not resource.has_key('kolabinvitationpolicy') or resource['kolabinvitationpolicy'] is None:
        if not auth:
            auth = Auth()
            auth.connect()

        # get kolabinvitationpolicy attribute from collection
        collections = auth.search_entry_by_attribute('uniquemember', resource['dn'])
        if not isinstance(collections, list):
            collections = [ (collections['dn'],collections) ]

        log.debug("Check collections %r for kolabinvitationpolicy attributes" % (collections), level=9)

        for dn,collection in collections:
            # ldap.search_entry_by_attribute() doesn't return the attributes lower-cased
            if collection.has_key('kolabInvitationPolicy'):
                collection['kolabinvitationpolicy'] = collection['kolabInvitationPolicy']

            if collection.has_key('kolabinvitationpolicy'):
                parse_kolabinvitationpolicy(collection)
                resource['kolabinvitationpolicy'] = collection['kolabinvitationpolicy']
                break

    return resource['kolabinvitationpolicy'] if resource.has_key('kolabinvitationpolicy') else None


def send_response(from_address, itip_events, owner=None):
    """
        Send the given iCal events as a valid iTip response to the organizer.
        In case the invited resource coolection was delegated to a concrete
        resource, this will send an additional DELEGATED response message.
    """

    if isinstance(itip_events, dict):
        itip_events = [ itip_events ]

    for itip_event in itip_events:
        attendee = itip_event['xml'].get_attendee_by_email(from_address)
        participant_status = itip_event['xml'].get_ical_attendee_participant_status(attendee)

        # TODO: look-up event organizer in LDAP and change localization to its preferredlanguage

        message_text = reservation_response_text(participant_status, owner)
        subject_template = _("Reservation Request for %(summary)s was %(status)s")

        if participant_status == "DELEGATED":
            # Extra actions to take
            delegator = itip_event['xml'].get_attendee_by_email(from_address)
            delegatee = [a for a in itip_event['xml'].get_attendees() if from_address in [b.email() for b in a.get_delegated_from()]][0]
            delegatee_status = itip_event['xml'].get_ical_attendee_participant_status(delegatee)

            pykolab.itip.send_reply(delegatee.get_email(), itip_event, reservation_response_text(delegatee_status, owner),
                subject=subject_template)

            # restore list of attendees after to_message_itip()
            itip_event['xml']._attendees = [ delegator, delegatee ]
            itip_event['xml'].event.setAttendees(itip_event['xml']._attendees)

            message_text = _("""
                *** This is an automated response, please do not reply! ***

                Your reservation was delegated to "%s" which is available for the requested time.
            """) % (delegatee.get_name())

        pykolab.itip.send_reply(from_address, itip_event, message_text,
            subject=subject_template)


def reservation_response_text(status, owner):
    message_text = _("""
        *** This is an automated response, please do not reply! ***
        
        We hereby inform you that your reservation was %s.
    """) % (participant_status_label(status))

    if owner:
        message_text += _("""
            If you have questions about this reservation, please contact
            %s <%s> %s
        """) % (owner['cn'], owner['mail'], owner['telephoneNumber'] if owner.has_key('telephoneNumber') else '')
    
    return message_text


def send_owner_notification(resource, owner, itip_event, success=True):
    """
        Send a reservation notification to the resource owner
    """
    import smtplib
    from pykolab import utils
    from email.MIMEText import MIMEText
    from email.Utils import formatdate

    notify = False
    status = itip_event['xml'].get_attendee_by_email(resource['mail']).get_participant_status(True)

    invitationpolicy = get_resource_invitationpolicy(resource)

    if invitationpolicy is not None:
        for policy in invitationpolicy:
            # TODO: distingish ACCEPTED / DECLINED status notifications?
            if policy & COND_NOTIFY and owner['mail']:
                notify = True
                break

    if notify or not success:
        log.debug(
            _("Sending booking notification for event %r to %r from %r") % (
                itip_event['uid'], owner['mail'], resource['cn']
            ),
            level=8
        )

        # change gettext language to the preferredlanguage setting of the resource owner
        if owner.has_key('preferredlanguage'):
            pykolab.translate.setUserLanguage(owner['preferredlanguage'])

        message_text = owner_notification_text(resource, owner, itip_event['xml'], success)

        msg = MIMEText(utils.stripped_message(message_text))

        msg['To'] = owner['mail']
        msg['From'] = resource['mail']
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = _('Booking for %s has been %s') % (resource['cn'], participant_status_label(status) if success else _('failed'))

        smtp = smtplib.SMTP("localhost", 10027)

        if conf.debuglevel > 8:
            smtp.set_debuglevel(True)

        try:
            smtp.sendmail(resource['mail'], owner['mail'], msg.as_string())
        except Exception, e:
            log.error(_("SMTP sendmail error: %r") % (e))

        smtp.quit()

def owner_notification_text(resource, owner, event, success):
    organizer = event.get_organizer()
    status = event.get_attendee_by_email(resource['mail']).get_participant_status(True)

    if success:
        message_text = _("""
            The resource booking for %(resource)s by %(orgname)s <%(orgemail)s> has been %(status)s for %(date)s.

            *** This is an automated message, sent to you as the resource owner. ***
        """)
    else:
        message_text = _("""
            A reservation request for %(resource)s could not be processed automatically.
            Please contact %(orgname)s <%(orgemail)s> who requested this resource for %(date)s. Subject: %(summary)s.

            *** This is an automated message, sent to you as the resource owner. ***
        """)

    return message_text % {
        'resource': resource['cn'],
        'summary': event.get_summary(),
        'date': event.get_date_text(),
        'status': participant_status_label(status),
        'orgname': organizer.name(),
        'orgemail': organizer.email()
    }


def send_owner_confirmation(resource, owner, itip_event):
    """
        Send a reservation request to the resource owner for manual confirmation (ACCEPT or DECLINE)

        This clones the given invtation with a new UID and setting the resource as organizer in order to
        receive the reply from the owner.
    """

    uid = itip_event['uid']
    event = itip_event['xml']
    organizer = event.get_organizer()
    event_attendees = [a.get_displayname() for a in event.get_attendees() if not a.get_cutype() == kolabformat.CutypeResource]

    # generate new UID and set the resource as organizer
    (mail, domain) = resource['mail'].split('@')
    event.set_uid(str(uuid.uuid4()))
    event.set_organizer(mail + '+' + urllib.quote(uid) + '@' + domain, resource['cn'])
    itip_event['uid'] = event.get_uid()

    # add resource owner as (the sole) attendee
    event._attendees = []
    event.add_attendee(owner['mail'], owner['cn'], rsvp=True, role=kolabformat.Required, participant_status=kolabformat.PartNeedsAction)

    # flag this iTip message as confirmation type
    event.add_custom_property('X-Kolab-InvitationType', 'CONFIRMATION')

    log.debug(
        _("Clone invitation for owner confirmation: %r from %r") % (
            itip_event['uid'], event.get_organizer().email()
        ),
        level=8
    )

    message_text = _("""
        A reservation request for %(resource)s requires your approval!
        Please either accept or decline this inivitation without saving it to your calendar.

        The reservation request was sent from %(orgname)s <%(orgemail)s>.

        Subject: %(summary)s.
        Date: %(date)s
        Participants: %(attendees)s

        *** This is an automated message, please don't reply by email. ***
    """)% {
        'resource': resource['cn'],
        'orgname': organizer.name(),
        'orgemail': organizer.email(),
        'summary': event.get_summary(),
        'date': event.get_date_text(),
        'attendees': ",\n+ ".join(event_attendees)
    }

    pykolab.itip.send_request(owner['mail'], itip_event, message_text,
        subject=_('Booking request for %s requires confirmation') % (resource['cn']),
        direct=True)


