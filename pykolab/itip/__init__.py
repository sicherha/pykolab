import icalendar
import pykolab

from pykolab.xml import to_dt
from pykolab.xml import event_from_ical
from pykolab.xml import participant_status_label
from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')


def events_from_message(message, methods=None):
    return objects_from_message(message, "VEVENT", methods)

def todos_from_message(message, methods=None):
    return objects_from_message(message, "VTODO", methods)


def objects_from_message(message, objname, methods=None):
    """
        Obtain the iTip payload from email.message <message>
    """
    # Placeholder for any itip_objects found in the message.
    itip_objects = []
    seen_uids = []

    # iTip methods we are actually interested in. Other methods will be ignored.
    if methods is None:
        methods = [ "REQUEST", "CANCEL" ]

    # Are all iTip messages multipart? No! RFC 6047, section 2.4 states "A
    # MIME body part containing content information that conforms to this
    # document MUST have (...)" but does not state whether an iTip message must
    # therefore also be multipart.

    # Check each part
    for part in message.walk():

        # The iTip part MUST be Content-Type: text/calendar (RFC 6047, section 2.4)
        # But in real word, other mime-types are used as well
        if part.get_content_type() in [ "text/calendar", "text/x-vcalendar", "application/ics" ]:
            if not str(part.get_param('method')).upper() in methods:
                log.info(_("Method %r not really interesting for us.") % (part.get_param('method')))
                continue

            # Get the itip_payload
            itip_payload = part.get_payload(decode=True)

            log.debug(_("Raw iTip payload: %s") % (itip_payload), level=9)

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
                if c.name == objname:
                    itip = {}

                    if c['uid'] in seen_uids:
                        log.debug(_("Duplicate iTip object: %s") % (c['uid']), level=9)
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

                    itip['uid'] = str(c['uid'])
                    itip['method'] = str(cal['method']).upper()
                    itip['sequence'] = int(c['sequence']) if c.has_key('sequence') else 0

                    if c.has_key('dtstart'):
                        itip['start'] = c['dtstart'].dt
                    else:
                        log.error(_("iTip event without a start"))
                        continue

                    if c.has_key('dtend'):
                        itip['end'] = c['dtend'].dt

                    if c.has_key('duration'):
                        itip['duration'] = c['duration'].dt
                        itip['end'] = itip['start'] + c['duration'].dt

                    itip['organizer'] = c['organizer']

                    itip['attendees'] = c['attendee']

                    if itip.has_key('attendees') and not isinstance(itip['attendees'], list):
                        itip['attendees'] = [c['attendee']]

                    if c.has_key('resources'):
                        itip['resources'] = c['resources']

                    itip['raw'] = itip_payload

                    try:
                        # TODO: distinguish event and todo here
                        itip['xml'] = event_from_ical(c.to_ical())
                    except Exception, e:
                        log.error("event_from_ical() exception: %r" % (e))
                        continue

                    itip_objects.append(itip)

                    seen_uids.append(c['uid'])

                # end if c.name == "VEVENT"

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

    _es = to_dt(kolab_event.get_start())
    _ee = to_dt(kolab_event.get_ical_dtend())  # use iCal style end date: next day for all-day events

    # naive loops to check for collisions in (recurring) events
    # TODO: compare recurrence rules directly (e.g. matching time slot or weekday or monthday)
    while not conflict and _es is not None:
        _is = to_dt(itip_event['start'])
        _ie = to_dt(itip_event['end'])

        while not conflict and _is is not None:
            # log.debug("* Comparing event dates at %s/%s with %s/%s" % (_es, _ee, _is, _ie), level=9)
            conflict = check_date_conflict(_es, _ee, _is, _ie)
            _is = to_dt(itip_event['xml'].get_next_occurence(_is)) if kolab_event.is_recurring() else None
            _ie = to_dt(itip_event['xml'].get_occurence_end_date(_is))

        _es = to_dt(kolab_event.get_next_occurence(_es)) if kolab_event.is_recurring() else None
        _ee = to_dt(kolab_event.get_occurence_end_date(_es))

    return conflict


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
    else: # _es > _is
        if _es <= _ie:
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

    if isinstance(itip_events, dict):
        itip_events = [ itip_events ]

    for itip_event in itip_events:
        attendee = itip_event['xml'].get_attendee_by_email(from_address)
        participant_status = itip_event['xml'].get_ical_attendee_participant_status(attendee)

        event_summary = itip_event['xml'].get_summary()
        message_text = response_text % { 'summary':event_summary, 'status':participant_status_label(participant_status), 'name':attendee.get_name() }

        if subject is not None:
            subject = subject % { 'summary':event_summary, 'status':participant_status_label(participant_status), 'name':attendee.get_name() }

        try:
            message = itip_event['xml'].to_message_itip(from_address,
                method="REPLY",
                participant_status=participant_status,
                message_text=message_text,
                subject=subject
            )
        except Exception, e:
            log.error(_("Failed to compose iTip reply message: %r") % (e))
            return

        smtp = smtplib.SMTP("localhost", 10026)  # replies go through wallace again

        if conf.debuglevel > 8:
            smtp.set_debuglevel(True)

        try:
            smtp.sendmail(message['From'], message['To'], message.as_string())
        except Exception, e:
            log.error(_("SMTP sendmail error: %r") % (e))

    smtp.quit()
