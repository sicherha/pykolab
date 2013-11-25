# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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

import datetime
import icalendar
import os
import pytz
import random
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

from pykolab.auth import Auth
from pykolab.conf import Conf
from pykolab.imap import IMAP
from pykolab.xml import event_from_ical
from pykolab.xml import event_from_string
from pykolab.xml import to_dt
from pykolab.translate import _

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

    os.rename(filepath, new_filepath)
    filepath = new_filepath
    exec('modules.cb_action_ACCEPT(%r, %r)' % ('resources',filepath))

def description():
    return """Resource management module."""

def execute(*args, **kw):
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT', 'REJECT', 'HOLD', 'DEFER' ]:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    log.debug(_("Resource Management called for %r, %r") % (args, kw), level=9)

    auth = Auth()
    auth.connect()

    imap = IMAP()
    imap.connect()

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

            return
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

    # parse message headers
    # @TODO: make sure we can use True as the 2nd argument here
    message = Parser().parse(open(filepath, 'r'), True)

    recipients = [address for displayname,address in getaddresses(message.get_all('X-Kolab-To'))]

    any_itips = False
    any_resources = False
    possibly_any_resources = True

    # An iTip message may contain multiple events. Later on, test if the message
    # is an iTip message by checking the length of this list.
    itip_events = itip_events_from_message(message)

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
        for recipient in recipients:
            if not len(resource_record_from_email_address(recipient)) == 0:
                any_resources = True

    if any_resources:
        if not any_itips:
            log.debug(_("Not an iTip message, but sent to resource nonetheless. Reject message"), level=5)
            reject(filepath)
            return
        else:
            # Continue. Resources and iTips. We like.
            pass
    else:
        if not any_itips:
            log.debug(_("No itips, no resources, pass along"), level=5)
            accept(filepath)
            return
        else:
            log.debug(_("iTips, but no resources, pass along"), level=5)
            accept(filepath)
            return

    # A simple list of merely resource entry IDs that hold any relevance to the
    # iTip events
    resource_records = resource_records_from_itip_events(itip_events)

    # Get the resource details, which includes details on the IMAP folder
    resources = {}
    for resource_record in list(set(resource_records)):
        # Get the attributes for the record
        # See if it is a resource collection
        #   If it is, expand to individual resources
        #   If it is not, ...
        resource_attrs = auth.get_entry_attributes(None, resource_record, ['*'])
        if not 'kolabsharedfolder' in [x.lower() for x in resource_attrs['objectclass']]:
            if resource_attrs.has_key('uniquemember'):
                resources[resource_record] = resource_attrs
                for uniquemember in resource_attrs['uniquemember']:
                    resource_attrs = auth.get_entry_attributes(
                            None,
                            uniquemember,
                            ['*']
                        )

                    if 'kolabsharedfolder' in [x.lower() for x in resource_attrs['objectclass']]:
                        resources[uniquemember] = resource_attrs
                        resources[uniquemember]['memberof'] = resource_record
        else:
            resources[resource_record] = resource_attrs

    log.debug(_("Resources: %r") % (resources), level=8)

    # For each resource, determine if any of the events in question is in
    # conflict.
    #
    # Store the (first) conflicting event(s) alongside the resource information.
    start = time.time()

    for resource in resources.keys():
        if not resources[resource].has_key('kolabtargetfolder'):
            continue

        mailbox = resources[resource]['kolabtargetfolder']

        resources[resource]['conflict'] = False
        resources[resource]['conflicting_events'] = []

        log.debug(
                _("Checking events in resource folder %r") % (mailbox),
                level=8
            )

        try:
            imap.imap.m.select(mailbox)
        except:
            log.error(_("Mailbox for resource %r doesn't exist") % (resource))
            continue

        typ, data = imap.imap.m.search(None, 'ALL')

        num_messages = len(data[0].split())

        for num in data[0].split():
            # For efficiency, makes the routine non-deterministic
            if resources[resource]['conflict']:
                continue

            log.debug(
                    _("Fetching message UID %r from folder %r") % (num, mailbox),
                    level=9
                )

            typ, data = imap.imap.m.fetch(num, '(RFC822)')

            event_message = message_from_string(data[0][1])

            if event_message.is_multipart():
                for part in event_message.walk():
                    if part.get_content_type() == "application/calendar+xml":
                        payload = part.get_payload(decode=True)
                        event = pykolab.xml.event_from_string(payload)

                        for itip in itip_events:
                            _es = to_dt(event.get_start())
                            _is = to_dt(itip['start'].dt)

                            _ee = to_dt(event.get_end())
                            _ie = to_dt(itip['end'].dt)

                            if _es < _is:
                                if _es <= _ie:
                                    if _ee <= _is:
                                        conflict = False
                                    else:
                                        conflict = True
                                else:
                                    conflict = True
                            elif _es == _is:
                                conflict = True
                            else: # _es > _is
                                if _es <= _ie:
                                    conflict = True
                                else:
                                    conflict = False

                            if conflict:
                                log.info(
                                        _("Event %r conflicts with event " + \
                                            "%r") % (
                                                itip['xml'].get_uid(),
                                                event.get_uid()
                                            )
                                    )

                                resources[resource]['conflicting_events'].append(event)
                                resources[resource]['conflict'] = True

    end = time.time()

    log.debug(
            _("start: %r, end: %r, total: %r, messages: %r") % (
                    start, end, (end-start), num_messages
                ),
            level=1
        )

    for resource in resources.keys():
        log.debug(_("Polling for resource %r") % (resource), level=9)

        if not resources.has_key(resource):
            log.debug(
                    _("Resource %r has been popped from the list") % (resource),
                    level=9
                )

            continue

        if not resources[resource].has_key('conflicting_events'):
            log.debug(_("Resource is a collection"), level=9)
            continue

        if len(resources[resource]['conflicting_events']) > 0:
            # This is the event being conflicted with!
            for itip_event in itip_events:
                # Now we have the event that was conflicting
                if resources[resource]['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                    itip_event['xml'].set_attendee_participant_status(
                            [a for a in itip_event['xml'].get_attendees() if a.get_email() == resources[resource]['mail']][0],
                            "DECLINED"
                        )

                    send_response(resources[resource]['mail'], itip_events)
                    # TODO: Accept the message to the other attendees

                else:
                    # This must have been a resource collection originally.
                    # We have inserted the reference to the original resource
                    # record in 'memberof'.
                    if resources[resource].has_key('memberof'):
                        original_resource = resources[resources[resource]['memberof']]

                        _target_resource = resources[original_resource['uniquemember'][random.randint(0,(len(original_resource['uniquemember'])-1))]]

                        # unset all
                        for _r in original_resource['uniquemember']:
                            del resources[_r]

                    if original_resource['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                        itip_event['xml'].set_attendee_participant_status(
                                [a for a in itip_event['xml'].get_attendees() if a.get_email() == original_resource['mail']][0],
                                "DECLINED"
                            )

                        send_response(original_resource['mail'], itip_events)
                        # TODO: Accept the message to the other attendees

        else:
            # No conflicts, go accept
            for itip_event in itip_events:
                if resources[resource]['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                    itip_event['xml'].set_attendee_participant_status(
                            [a for a in itip_event['xml'].get_attendees() if a.get_email() == resources[resource]['mail']][0],
                            "ACCEPTED"
                        )

                    log.debug(
                            _("Adding event to %r") % (
                                    resources[resource]['kolabtargetfolder']
                                ),
                            level=9
                        )

                    imap.imap.m.setacl(resources[resource]['kolabtargetfolder'], "cyrus-admin", "lrswipkxtecda")
                    imap.imap.m.append(
                            resources[resource]['kolabtargetfolder'],
                            None,
                            None,
                            itip_event['xml'].to_message().as_string()
                        )

                    send_response(resources[resource]['mail'], itip_event)

                else:
                    # This must have been a resource collection originally.
                    # We have inserted the reference to the original resource
                    # record in 'memberof'.
                    if resources[resource].has_key('memberof'):
                        original_resource = resources[resources[resource]['memberof']]

                        # Randomly selects a target resource from the resource
                        # collection.
                        _target_resource = resources[original_resource['uniquemember'][random.randint(0,(len(original_resource['uniquemember'])-1))]]

                        # Remove all resources from the collection.
                        for _r in original_resource['uniquemember']:
                            del resources[_r]

                    if original_resource['mail'] in [a.get_email() for a in itip_event['xml'].get_attendees()]:
                        #
                        # Delegate:
                        #
                        # - delegator: the original resource collection
                        # - delegatee: the target resource
                        #

                        itip_event['xml'].delegate(
                                original_resource['mail'],
                                _target_resource['mail']
                            )

                        itip_event['xml'].set_attendee_participant_status(
                                [a for a in itip_event['xml'].get_attendees() if a.get_email() == _target_resource['mail']][0],
                                "ACCEPTED"
                            )

                        log.debug(
                                _("Adding event to %r") % (
                                        _target_resource['kolabtargetfolder']
                                    ),
                                level=9
                            )

                        # TODO: The Cyrus IMAP (or Dovecot) Administrator login
                        # name comes from configuration.
                        imap.imap.m.setacl(_target_resource['kolabtargetfolder'], "cyrus-admin", "lrswipkxtecda")
                        imap.imap.m.append(
                                _target_resource['kolabtargetfolder'],
                                None,
                                None,
                                itip_event['xml'].to_message().as_string()
                            )

                        send_response(original_resource['mail'], itip_event)

    auth.disconnect()
    del auth

    # Disconnect IMAP or we lock the mailbox almost constantly
    imap.disconnect()
    del imap

    os.unlink(filepath)

def itip_events_from_message(message):
    """
        Obtain the iTip payload from email.message <message>
    """
    # Placeholder for any itip_events found in the message.
    itip_events = []

    # iTip methods we are actually interested in. Other methods will be ignored.
    itip_methods = [ "REQUEST", "REPLY", "ADD", "CANCEL" ]

    # TODO: Are all iTip messages multipart? RFC 6047, section 2.4 states "A
    # MIME body part containing content information that conforms to this
    # document MUST have (...)" but does not state whether an iTip message must
    # therefore also be multipart.
    if message.is_multipart():
        # Check each part
        for part in message.walk():

            # The iTip part MUST be Content-Type: text/calendar (RFC 6047,
            # section 2.4)
            if part.get_content_type() == "text/calendar":
                if not part.get_param('method') in itip_methods:
                    log.error(
                            _("Method %r not really interesting for us.") % (
                                    part.get_param('method')
                                )
                        )

                # Get the itip_payload
                itip_payload = part.get_payload(decode=True)

                log.debug(_("Raw iTip payload: %s") % (itip_payload))

                # Python iCalendar prior to 3.0 uses "from_string".
                if hasattr(icalendar.Calendar, 'from_ical'):
                    cal = icalendar.Calendar.from_ical(itip_payload)
                elif hasattr(icalendar.Calendar, 'from_string'):
                    cal = icalendar.Calendar.from_string(itip_payload)

                # If we can't read it, we're out
                else:
                    log.error(_("Could not read iTip from message."))
                    return []

                for c in cal.walk():
                    if c.name == "VEVENT":
                        itip = {}

                        # From the event, take the following properties:
                        #
                        # - start
                        # - end (if any)
                        # - duration (if any)
                        # - organizer
                        # - attendees (if any)
                        # - resources (if any)
                        # - TODO: recurrence rules (if any)
                        #   Where are these stored actually?
                        #

                        if c.has_key('dtstart'):
                            itip['start'] = c['dtstart']
                        else:
                            log.error(_("iTip event without a start"))
                            continue

                        if c.has_key('dtend'):
                            itip['end'] = c['dtend']

                        if c.has_key('duration'):
                            itip['duration'] = c['duration']

                        itip['organizer'] = c['organizer']

                        itip['attendees'] = c['attendee']

                        if c.has_key('resources'):
                            itip['resources'] = c['resources']

                        itip['raw'] = itip_payload
                        itip['xml'] = event_from_ical(c.to_ical())

                        itip_events.append(itip)

                    # end if c.name == "VEVENT"

                # end for c in cal.walk()

            # end if part.get_content_type() == "text/calendar"

        # end for part in message.walk()

    else: # if message.is_multipart()
        log.debug(_("Message is not an iTip message (non-multipart message)"), level=5)

    return itip_events

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
    auth = Auth()
    auth.connect()
    resource_records = []

    log.debug(
            _("Checking if email address %r belongs to a resource (collection)") % (
                    email_address
                ),
            level=8
        )

    resource_records = auth.find_resource(email_address)

    if isinstance(resource_records, list):
        if len(resource_records) == 0:
            log.debug(
                    _("No resource (collection) records found for %r") % (
                            email_address
                        ),
                    level=9
                )

        else:
            log.debug(
                    _("Resource record(s): %r") % (resource_records),
                    level=8
                )

    elif isinstance(resource_records, basestring):
        log.debug(
                _("Resource record: %r") % (resource_records),
                level=8
            )

        resource_records = [ resource_records ]

    auth.disconnect()

    return resource_records

def resource_records_from_itip_events(itip_events):
    """
        Given a list of itip_events, determine which resources have been
        invited as attendees and/or resources.
    """

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

    # TODO: We expect the format of an attendee line to literally be:
    #
    #   ATTENDEE:RSVP=TRUE;ROLE=REQ-PARTICIPANT;MAILTO:lydia.bossers@kolabsys.com
    #
    # which makes the attendees_raw contain:
    #
    #   RSVP=TRUE;ROLE=REQ-PARTICIPANT;MAILTO:lydia.bossers@kolabsys.com
    #
    attendees = [x.split(':')[-1] for x in attendees_raw]

    for attendee in attendees:
        log.debug(
                _("Checking if attendee %r is a resource (collection)") % (
                        attendee
                    ),
                level=8
            )

        _resource_records = auth.find_resource(attendee)

        if isinstance(_resource_records, list):
            if len(_resource_records) == 0:
                log.debug(
                        _("No resource (collection) records found for %r") % (
                                attendee
                            ),
                        level=9
                    )

            else:
                log.debug(
                        _("Resource record(s): %r") % (_resource_records),
                        level=8
                    )

                resource_records.extend(_resource_records)
        elif isinstance(_resource_records, basestring):
            log.debug(
                    _("Resource record: %r") % (_resource_records),
                    level=8
                )

            resource_records.append(_resource_records)
        else:
            log.warning(
                    _("Resource reservation made but no resource records found")
                )

    # TODO: Escape the non-implementation of the free-form, undefined RESOURCES
    # list(s) in iTip. We don't know how to handle this yet!
    resources_raw = []

    # TODO: We expect the format of an resource line to literally be:
    #
    #   RESOURCES:MAILTO:resource-car@kolabsys.com
    #
    # which makes the resources_raw contain:
    #
    #   MAILTO:resource-car@kolabsys.com
    #
    resources = [x.split(':')[-1] for x in resources_raw]
    for resource in resources:
        log.debug(
                _("Checking if resource %r is a resource (collection)") % (
                        resource
                    ),
                level=8
            )

        _resource_records = auth.find_resource(resource)
        if isinstance(_resource_records, list):
            if len(_resource_records) == 0:
                log.debug(
                        _("No resource (collection) records found for %r") % (
                                resource
                            ),
                        level=8
                    )

            else:
                log.debug(
                        _("Resource record(s): %r") % (_resource_records),
                        level=8
                    )

                resource_records.extend(_resource_records)
        elif isinstance(_resource_records, basestring):
            resource_records.append(_resource_records)
            log.debug(_("Resource record: %r") % (_resource_records), level=8)
        else:
            log.warning(
                    _("Resource reservation made but no resource records found")
                )

    log.debug(
            _("The following resources are being referred to in the " + \
                "iTip: %r") % (
                    resource_records
                ),
            level=8
        )

    auth.disconnect()

    return resource_records

def send_response(from_address, itip_events):
    import smtplib
    smtp = smtplib.SMTP("localhost", 10027)

    if conf.debuglevel > 8:
        smtp.set_debuglevel(True)

    if isinstance(itip_events, dict):
        itip_events = [ itip_events ]

    for itip_event in itip_events:
        attendee = [a for a in itip_event['xml'].get_attendees() if a.get_email() == from_address][0]
        participant_status = itip_event['xml'].get_ical_attendee_participant_status(attendee)

        if participant_status == "DELEGATED":
            # Extra actions to take
            delegator = [a for a in itip_event['xml'].get_attendees() if a.get_email() == from_address][0]
            delegatee = [a for a in itip_event['xml'].get_attendees() if from_address in [b.email() for b in a.get_delegated_from()]][0]

            itip_event['xml'].event.setAttendees([ delegator, delegatee ])

            message = itip_event['xml'].to_message_itip(delegatee.get_email(), method="REPLY", participant_status=itip_event['xml'].get_ical_attendee_participant_status(delegatee))
            smtp.sendmail(message['From'], message['To'], message.as_string())

        itip_event['xml'].event.setAttendees([a for a in itip_event['xml'].get_attendees() if a.get_email() == from_address])

        message = itip_event['xml'].to_message_itip(from_address, method="REPLY", participant_status=participant_status)
        smtp.sendmail(message['From'], message['To'], message.as_string())

    smtp.quit()
