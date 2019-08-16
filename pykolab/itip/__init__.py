import re
import traceback

import icalendar
import kolabformat

import pykolab
from pykolab.translate import _
from pykolab.xml import to_dt
from pykolab.xml import event_from_ical
from pykolab.xml import todo_from_ical
from pykolab.xml import participant_status_label

from tzlocal import windows_tz

# pylint: disable=invalid-name
log = pykolab.getLogger('pykolab.wallace')


def events_from_message(message, methods=None):
    return objects_from_message(message, ["VEVENT"], methods)


def todos_from_message(message, methods=None):
    return objects_from_message(message, ["VTODO"], methods)


# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def objects_from_message(message, objnames, methods=None):  # noqa: C901
    """
        Obtain the iTip payload from email.message <message>
    """
    # Placeholder for any itip_objects found in the message.
    itip_objects = []
    seen_uids = []

    # iTip methods we are actually interested in. Other methods will be ignored.
    if methods is None:
        methods = ["REQUEST", "CANCEL"]

    # Are all iTip messages multipart? No! RFC 6047, section 2.4 states "A
    # MIME body part containing content information that conforms to this
    # document MUST have (...)" but does not state whether an iTip message must
    # therefore also be multipart.

    # Check each part
    # pylint: disable=too-many-nested-blocks
    for part in message.walk():

        # The iTip part MUST be Content-Type: text/calendar (RFC 6047, section 2.4)
        # But in real word, other mime-types are used as well
        if part.get_content_type() in ["text/calendar", "text/x-vcalendar", "application/ics"]:
            if str(part.get_param('method')).upper() not in methods:
                log.info("Method %r not really interesting for us." % (part.get_param('method')))
                continue

            # Get the itip_payload
            itip_payload = part.get_payload(decode=True)

            log.debug(
                "Raw iTip payload (%r): %r" % (part.get_param('charset'), itip_payload),
                level=8
            )

            # Convert unsupported timezones, etc.
            itip_payload = _convert_itip_payload(itip_payload)

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
                if c.name in objnames:
                    itip = {}

                    if c['uid'] in seen_uids:
                        log.debug(_("Duplicate iTip object: %s") % (c['uid']), level=8)
                        continue

                    # From the event, take the following properties:
                    #
                    # - method
                    # - uid
                    # - sequence
                    # - start
                    # - end (if any)
                    # - duration (if any)
                    # - organizer
                    # - attendees (if any)
                    # - resources (if any)
                    #

                    itip['type'] = 'task' if c.name == 'VTODO' else 'event'
                    itip['uid'] = str(c['uid'])
                    itip['method'] = str(cal['method']).upper()
                    itip['sequence'] = int(c['sequence']) if 'sequence' in c else 0

                    itip['recurrence-id'] = None
                    if 'recurrence-id' in c:
                        if hasattr(c['recurrence-id'], 'dt'):
                            itip['recurrence-id'] = c['recurrence-id'].dt

                    if 'dtstart' in c:
                        itip['start'] = c['dtstart'].dt
                    elif itip['type'] == 'event':
                        log.error(_("iTip event without a start"))
                        continue

                    if 'dtend' in c:
                        itip['end'] = c['dtend'].dt

                    if 'duration' in c:
                        itip['duration'] = c['duration'].dt
                        itip['end'] = itip['start'] + c['duration'].dt

                    # Outlook can send itip replies with no organizer property
                    if 'organizer' in c:
                        itip['organizer'] = c['organizer']

                    if 'attendee' in c:
                        itip['attendees'] = c['attendee']

                    if 'attendees' in itip and not isinstance(itip['attendees'], list):
                        itip['attendees'] = [c['attendee']]

                    if 'resources' in c:
                        itip['resources'] = c['resources']

                    itip['raw'] = itip_payload

                    try:
                        # distinguish event and todo here
                        if itip['type'] == 'task':
                            itip['xml'] = todo_from_ical(c, itip_payload)
                        else:
                            itip['xml'] = event_from_ical(c, itip_payload)

                    # pylint: disable=broad-except
                    except Exception as e:
                        log.error(
                            "event|todo_from_ical() exception: %r; iCal: %s" % (e, itip_payload)
                        )

                        continue

                    itip_objects.append(itip)

                    seen_uids.append(c['uid'])

                # end if c.name in objnames

            # end for c in cal.walk()

        # end if part.get_content_type() == "text/calendar"

    # end for part in message.walk()

    if not len(itip_objects) and not message.is_multipart():
        log.debug(_("Message is not an iTip message (non-multipart message)"), level=5)

    return itip_objects


def check_event_conflict(kolab_event, itip_event):
    """
        Determine whether the given kolab event conflicts with the given itip event
    """
    conflict = False

    # don't consider conflict with myself
    if kolab_event.uid == itip_event['uid']:
        return conflict

    # don't consider conflict if event has TRANSP:TRANSPARENT
    if _is_transparent(kolab_event):
        return conflict

    if _is_transparent(itip_event['xml']):
        return conflict

    _es = to_dt(kolab_event.get_start())
    # use iCal style end date: next day for all-day events
    _ee = to_dt(kolab_event.get_ical_dtend())

    _is = to_dt(itip_event['start'])
    _ie = to_dt(itip_event['end'])

    # Escape looping through anything if neither of the events is recurring.
    if not itip_event['xml'].is_recurring() and not kolab_event.is_recurring():
        return check_date_conflict(_es, _ee, _is, _ie)

    loop = 0

    done = False

    # naive loops to check for collisions in (recurring) events
    # TODO: compare recurrence rules directly (e.g. matching time slot or weekday or monthday)
    while not conflict and not done:
        loop += 1

        # Scroll forward the kolab event recurrence until we're in the prime
        # spot. We choose to start with the Kolab event because that is likely
        # the older one.
        if _ee < _is:
            while _ee < _is and _es is not None and kolab_event.is_recurring():
                log.debug(
                    "Attempt to move forward kolab event recurrence from {} closer to {}".format(
                        _ee,
                        _is
                    ),
                    level=8
                )

                __es = to_dt(kolab_event.get_next_occurence(_es))

                if __es is not None and not __es == _es:
                    _es = __es
                    _ee = to_dt(kolab_event.get_occurence_end_date(_es))
                else:
                    done = True
                    break

        # Scroll forward the itip event recurrence until we're in the
        # prime spot, this time with the iTip event.
        elif _ie < _es:
            while _ie < _es and _is is not None and itip_event['xml'].is_recurring():
                log.debug(
                    "Attempt to move forward itip event recurrence from {} closer to {}".format(
                        _ie,
                        _es
                    ),
                    level=8
                )

                __is = to_dt(itip_event['xml'].get_next_occurence(_is))

                if __is is not None and not _is == __is:
                    _is = __is
                    _ie = to_dt(itip_event['xml'].get_occurence_end_date(_is))
                else:
                    done = True
                    break

        # Now that we have some events somewhere in the same neighborhood...
        conflict = check_date_conflict(_es, _ee, _is, _ie)
        log.debug(
            "* Comparing itip at %s/%s with kolab at %s/%s: conflict - %r (occurence - %d)" % (
                _is, _ie, _es, _ee, conflict, loop
            ),
            level=8
        )

        if not conflict:
            if kolab_event.is_recurring() and itip_event['xml'].is_recurring():
                if not kolab_event.has_exceptions() and not itip_event['xml'].has_exceptions():
                    log.debug("No conflict, both recurring, but neither with exceptions", level=8)
                    done = True
                    break

            _is = to_dt(itip_event['xml'].get_next_occurence(_is))

            if _is is not None:
                _ie = to_dt(itip_event['xml'].get_occurence_end_date(_is))
            else:
                done = True

    return conflict


def _is_transparent(event):
    return event.get_transparency() or event.get_status() == kolabformat.StatusCancelled


def _convert_itip_payload(itip):
    matchlist = re.findall("^((DTSTART|DTEND|DUE|EXDATE|COMPLETED)[:;][^\n]+)$", itip, re.MULTILINE)

    for match in matchlist:
        match = match[0]
        search = re.search(";TZID=([^:;]+)", match)

        if search:
            tzorig = tzdest = search.group(1).replace('"', '')

            # timezone in Olson-database format, nothing to convert
            if re.match("[a-zA-Z]+/[a-zA-Z0-9_+-]+", tzorig):
                continue

            # convert timezone from windows format to Olson
            if tzorig in windows_tz.win_tz:
                tzdest = windows_tz.win_tz[tzorig]

                # @TODO: Should be prefer server time if it has the same offset?

            # replace old with new timezone name
            if tzorig != tzdest:
                replace = match.replace(search.group(0), ";TZID=" + tzdest)
                itip = itip.replace("\n" + match, "\n" + replace)

    return itip


def check_date_conflict(_es, _ee, _is, _ie):
    """
        Check the given event start/end dates for conflicts
    """
    conflict = False

    # TODO: add margin for all-day dates (+13h; -12h)

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
    else:  # _es > _is
        if _es < _ie:
            conflict = True
        else:
            conflict = False

    return conflict


def send_reply(from_address, itip_events, response_text, subject=None):
    """
        Send the given iCal events as a valid iTip REPLY to the organizer.
    """
    import smtplib

    conf = pykolab.getConf()
    smtp = None

    if isinstance(itip_events, dict):
        itip_events = [itip_events]

    for itip_event in itip_events:
        attendee = itip_event['xml'].get_attendee_by_email(from_address)
        participant_status = itip_event['xml'].get_ical_attendee_participant_status(attendee)

        log.debug(
            "Send iTip reply {} for {} {}".format(
                participant_status,
                itip_event['xml'].type,
                itip_event['xml'].uid
            ),
            level=8
        )

        event_summary = itip_event['xml'].get_summary()
        message_text = response_text % {
            'summary': event_summary,
            'status': participant_status_label(participant_status),
            'name': attendee.get_name()
        }

        if subject is not None:
            subject = subject % {
                'summary': event_summary,
                'status': participant_status_label(participant_status),
                'name': attendee.get_name()
            }

        try:
            message = itip_event['xml'].to_message_itip(
                from_address,
                method="REPLY",
                participant_status=participant_status,
                message_text=message_text,
                subject=subject
            )

        # pylint: disable=broad-except
        except Exception as e:
            log.error("Failed to compose iTip reply message: %r: %s" % (e, traceback.format_exc()))
            return

        smtp = smtplib.SMTP("localhost", 10026)  # replies go through wallace again

        if conf.debuglevel > 8:
            smtp.set_debuglevel(True)

        try:
            smtp.sendmail(message['From'], message['To'], message.as_string())

        # pylint: disable=broad-except
        except Exception as e:
            log.error(_("SMTP sendmail error: %r") % (e))

    if smtp:
        smtp.quit()


def send_request(to_address, itip_events, request_text, subject=None, direct=False):
    """
        Send an iTip REQUEST message from the given iCal events
    """
    import smtplib

    conf = pykolab.getConf()
    smtp = None

    if isinstance(itip_events, dict):
        itip_events = [itip_events]

    for itip_event in itip_events:
        event_summary = itip_event['xml'].get_summary()
        message_text = request_text % {'summary': event_summary}

        if subject is not None:
            subject = subject % {'summary': event_summary}

        try:
            message = itip_event['xml'].to_message_itip(
                None,
                method="REQUEST",
                message_text=message_text,
                subject=subject
            )

        # pylint: disable=broad-except
        except Exception as e:
            log.error(_("Failed to compose iTip request message: %r") % (e))
            return

        port = 10027 if direct else 10026
        smtp = smtplib.SMTP("localhost", port)

        if conf.debuglevel > 8:
            smtp.set_debuglevel(True)

        try:
            smtp.sendmail(message['From'], to_address, message.as_string())

        # pylint: disable=broad-except
        except Exception as e:
            log.error(_("SMTP sendmail error: %r") % (e))

    if smtp:
        smtp.quit()
