# -*- coding: utf-8 -*-
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

import icalendar
import json
import os
import random
import tempfile
import time
from urlparse import urlparse
import urllib

from email import message_from_file
from email import message_from_string
from email.utils import formataddr
from email.utils import getaddresses

import modules

import pykolab

from pykolab.auth import Auth
from pykolab.imap import IMAP
from pykolab.xml import event_from_ical
from pykolab.xml import event_from_string
from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/resources/'

auth = None
imap = None

def __init__():
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    modules.register('resources', execute, description=description())

def description():
    return """Resource management module."""

def execute(*args, **kw):
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

    log.debug(_("Resource Management called for %r, %r") % (args, kw), level=8)

    message = message_from_file(open(filepath, 'r'))

    # An iTip message may contain multiple events. Later on, test if the message
    # is an iTip message by checking the length of this list.
    itip_events = itip_events_from_message(message)

    if not len(itip_events) > 0:
        log.info(
                _("Message is not an iTip message or does not contain any " + \
                    "iTip.")
            )

        exec('modules.cb_action_ACCEPT(%r, %r)' % ('resources',filepath))
        return

    else:
        log.debug(
                _("iTip events attached to this message contain the " + \
                    "following information: %r") % (itip_events),
                level=9
            )

    # See if a resource is actually being allocated
    if len([x['resources'] for x in itip_events if x.has_key('resources')]) == 0:
        if len([x['attendees'] for x in itip_events if x.has_key('attendees')]) == 0:
            exec('modules.cb_action_ACCEPT(%r, %r)' % ('resources',filepath))
            return

    # A simple list of merely resource entry IDs
    resource_records = resource_records_from_itip_events(itip_events)

    resources = {}
    for resource_record in list(set(resource_records)):
        # Get the attributes for the record
        # See if it is a resource collection
        #   If it is, expand to individual resources
        #   If it is not, ...
        resource_attrs = auth.get_entry_attributes(None, resource_record, ['*'])
        if not 'kolabsharedfolder' in [x.lower() for x in resource_attrs['objectclass']]:
            if resource_attrs.has_key('uniquemember'):
                for uniquemember in resource_attrs['uniquemember']:
                    resource_attrs = auth.get_entry_attributes(None, uniquemember, ['*'])
                    if 'kolabsharedfolder' in [x.lower() for x in resource_attrs['objectclass']]:
                        resources[resource_record] = resource_attrs
        else:
            resources[resource_record] = resource_attrs

    for resource in resources.keys():
        if not resources[resource].has_key('kolabtargetfolder'):
            continue

        mailbox = resources[resource]['kolabtargetfolder']

        resources[resource]['conflict'] = False
        resources[resource]['conflicting_events'] = []

        log.debug(_("Checking events in resource folder %r") % (mailbox), level=8)

        try:
            imap.imap.m.select(mailbox)
        except:
            log.error(_("Mailbox for resource %r doesn't exist") % (resource))
            continue

        typ, data = imap.imap.m.search(None, 'ALL')

        for num in data[0].split():
            # For efficiency, non-deterministic
            if resources[resource]['conflict']:
                continue

            log.debug(_("Fetching message UID %r from folder %r") %(num, mailbox), level=9)
            typ, data = imap.imap.m.fetch(num, '(RFC822)')

            event_message = message_from_string(data[0][1])

            if event_message.is_multipart():
                for part in event_message.walk():
                    if part.get_content_type() == "application/calendar+xml":
                        payload = part.get_payload()
                        event = pykolab.xml.event_from_string(payload)

                        for itip in itip_events:
                            log.debug(_("comparing %r to event %r (%r message UID %r)") % (itip, event.get_uid(), mailbox, num), level=9)
                            log.debug(_("  event %r start: %r") % (event.get_uid(),event.get_start()), level=9)
                            log.debug(_("  event %r end: %r") % (event.get_uid(),event.get_end()), level=9)

                            if event.get_start() < itip['start']:
                                if event.get_start() <= itip['end']:
                                    if event.get_end() <= itip['start']:
                                        conflict = False
                                    else:
                                        log.debug(_("Event %r ends later than invitation") % (event.get_uid()), level=9)
                                        conflict = True
                                else:
                                    log.debug(_("Event %r starts before invitation ends") % (event.get_uid()), level=9)
                                    conflict = True
                            elif event.get_start() == itip['start']:
                                log.debug(_("Event %r and invitation start at the same time") % (event.get_uid()), level=9)
                                conflict = True
                            else: # event.get_start() > itip['start']
                                if event.get_start() <= itip['end']:
                                    log.debug(_("Event %r starts before invitation ends") % (event.get_uid()), level=9)
                                    conflict = True
                                else:
                                    conflict = False

                            if conflict:
                                log.debug(_("Conflict with event %r") % (event.get_uid()), level=8)
                                resources[resource]['conflicting_events'].append(event)
                                resources[resource]['conflict'] = True

        log.debug(_("Resource status information: %r") % (resources[resource]), level=8)

def itip_events_from_message(message):
    """
        Obtain the iTip payload from email.message <message>
    """

    itip_events = []

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

                if part.get_param('method') == "REQUEST":
                    # Python iCalendar prior to 3.0 uses "from_string".
                    itip_payload = part.get_payload()
                    if hasattr(icalendar.Calendar, 'from_ical'):
                        cal = icalendar.Calendar.from_ical(itip_payload)
                    elif hasattr(icalendar.Calendar, 'from_string'):
                        cal = icalendar.Calendar.from_string(itip_payload)
                    else:
                        log.error(_("Could not read iTip from message."))
                        exec(
                                'modules.cb_action_ACCEPT(%r, %r)' % (
                                        'resources',
                                        filepath
                                    )
                            )

                        return

                    for c in cal.walk():
                        itip = {}
                        if c.name == "VEVENT":
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
                            itip['start'] = c.decoded('dtstart')
                            if c.has_key('dtend'):
                                itip['end'] = c.decoded('dtend')
                            if c.has_key('duration'):
                                itip['duration'] = c.decoded('duration')
                            itip['organizer'] = c.decoded('organizer')
                            itip['attendees'] = c.decoded('attendee')
                            if c.has_key('resources'):
                                itip['resources'] = c.decoded('resources')
                            itip['raw'] = itip_payload
                            itip['xml'] = event_from_ical(c.__str__())
                            itip_events.append(itip)
                else:
                    log.error(
                            _("Method %r not yet implemented") % (
                                    part.get_param('method')
                                )
                        )

    else:
        log.error(_("Non-multipart iTip messages are not accepted"))

    return itip_events

def resource_records_from_itip_events(itip_events):
    """
        Given a list of itip_events, determine which resources have been
        invited as attendees and/or resources.
    """

    auth = Auth()
    auth.connect()

    resource_records = []

    attendees_raw = []
    for list_attendees_raw in [x for x in [y['attendees'] for y in itip_events if y.has_key('attendees')]]:
        attendees_raw.extend(list_attendees_raw)

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
        log.debug(_("Checking if attendee %r is a resource (collection)") % (attendee), level=8)
        _resource_records = auth.find_resource(attendee)

        if isinstance(_resource_records, list):
            if len(_resource_records) == 0:
                log.debug(_("No resource (collection) records found for %r") % (attendee), level=9)
            else:
                log.debug(_("Resource record(s): %r") % (_resource_records), level=8)
                resource_records.extend(_resource_records)
        elif isinstance(_resource_records, basestring):
            resource_records.append(_resource_records)
            log.debug(_("Resource record: %r") % (_resource_records), level=8)
        else:
            log.warning(_("Resource reservation made but no resource records found"))

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
        log.debug(_("Checking if resource %r is a resource (collection)") % (resource), level=8)
        _resource_records = auth.find_resource(resource)
        if isinstance(_resource_records, list):
            if len(_resource_records) == 0:
                log.debug(_("No resource (collection) records found for %r") % (resource), level=8)
            else:
                log.debug(_("Resource record(s): %r") % (_resource_records), level=8)
                resource_records.extend(_resource_records)
        elif isinstance(_resource_records, basestring):
            resource_records.append(_resource_records)
            log.debug(_("Resource record: %r") % (_resource_records), level=8)
        else:
            log.warning(_("Resource reservation made but no resource records found"))

    log.debug(_("The following resources are being referred to in the iTip: %r") % (resource_records), level=8)

    return resource_records