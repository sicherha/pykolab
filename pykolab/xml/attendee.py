import kolabformat

from pykolab.translate import _
from pykolab.translate import N_

from contact_reference import ContactReference

participant_status_labels = {
        "NEEDS-ACTION": N_("Needs Action"),
        "ACCEPTED": N_("Accepted"),
        "DECLINED": N_("Declined"),
        "TENTATIVE": N_("Tentatively Accepted"),
        "DELEGATED": N_("Delegated"),
        "IN-PROCESS": N_("Started"),
        "COMPLETED": N_("Completed"),
        # support integer values, too
        kolabformat.PartNeedsAction: N_("Needs Action"),
        kolabformat.PartAccepted: N_("Accepted"),
        kolabformat.PartDeclined: N_("Declined"),
        kolabformat.PartTentative: N_("Tentatively Accepted"),
        kolabformat.PartDelegated: N_("Delegated"),
        kolabformat.PartInProcess: N_("Started"),
        kolabformat.PartCompleted: N_("Completed"),
    }

def participant_status_label(status):
    return _(participant_status_labels[status]) if participant_status_labels.has_key(status) else _(status)


class Attendee(kolabformat.Attendee):
    cutype_map = {
            "INDIVIDUAL": kolabformat.CutypeIndividual,
            "RESOURCE": kolabformat.CutypeResource,
            "GROUP": kolabformat.CutypeGroup,
        }

    participant_status_map = {
            "NEEDS-ACTION": kolabformat.PartNeedsAction,
            "ACCEPTED": kolabformat.PartAccepted,
            "DECLINED": kolabformat.PartDeclined,
            "TENTATIVE": kolabformat.PartTentative,
            "DELEGATED": kolabformat.PartDelegated,
            "IN-PROCESS": kolabformat.PartInProcess,
            "COMPLETED": kolabformat.PartCompleted,
        }

    # See RFC 2445, 5445
    role_map = {
            "CHAIR": kolabformat.Chair,
            "REQ-PARTICIPANT": kolabformat.Required,
            "OPT-PARTICIPANT": kolabformat.Optional,
            "NON-PARTICIPANT": kolabformat.NonParticipant,
        }

    rsvp_map = {
            "TRUE": True,
            "FALSE": False,
        }

    properties_map = {
            'role': 'get_role',
            'rsvp':  'rsvp',
            'partstat':  'get_participant_status',
            'cutype':   'get_cutype',
            'delegated-to': 'get_delegated_to',
            'delegated-from': 'get_delegated_from',
        }

    def __init__(
            self,
            email,
            name=None,
            rsvp=False,
            role=None,
            participant_status=None,
            cutype=None,
            ical_params=None
        ):

        self.email = email

        self.contactreference = ContactReference(email)

        if not name == None:
            self.contactreference.set_name(name)

        kolabformat.Attendee.__init__(self, self.contactreference)

        if isinstance(rsvp, bool):
            self.setRSVP(rsvp)
        else:
            if self.rsvp_map.has_key(rsvp):
                self.setRSVP(self.rsvp_map[rsvp])

        if not role == None:
            self.set_role(role)

        if not cutype == None:
            self.set_cutype(cutype)

        if ical_params and ical_params.has_key('DELEGATED-FROM'):
            self.delegate_from(Attendee(str(ical_params['DELEGATED-FROM']), role=self.get_role(), cutype=self.get_cutype()))

        if ical_params and ical_params.has_key('DELEGATED-TO'):
            self.delegate_to(Attendee(str(ical_params['DELEGATED-TO'])))

        if not participant_status == None:
            self.set_participant_status(participant_status)

    def copy_from(self, obj):
        if isinstance(obj, kolabformat.Attendee):
            self.contactreference = ContactReference(obj.contact())
            self.email = self.contactreference.get_email()
            self.setContact(self.contactreference)

            # manually copy all properities, copy constructor doesn't work :-(
            self.setRSVP(obj.rsvp())
            self.setRole(obj.role())
            self.setCutype(obj.cutype())
            self.setPartStat(obj.partStat())
            self.setDelegatedTo(obj.delegatedTo())
            self.setDelegatedFrom(obj.delegatedFrom())

    def delegate_from(self, delegators):
        crefs = []

        if not isinstance(delegators, list):
            delegators = [delegators]

        for delegator in delegators:
            if not isinstance(delegator, Attendee):
                raise ValueError, _("Not a valid attendee")
            else:
                self.set_role(delegator.get_role())
                self.set_cutype(delegator.get_cutype())
                crefs.append(delegator.contactreference)

        if len(crefs) == 0:
            raise ValueError, _("No valid delegator references found")
        else:
            crefs += self.get_delegated_from()

        self.setDelegatedFrom(list(set(crefs)))

    def delegate_to(self, delegatees):
        self.set_participant_status("DELEGATED")

        crefs = []
        if not isinstance(delegatees, list):
            delegatees = [delegatees]

        for delegatee in delegatees:
            if not isinstance(delegatee, Attendee):
                raise ValueError, _("Not a valid attendee")
            else:
                crefs.append(delegatee.contactreference)

        if len(crefs) == 0:
            raise ValueError, _("No valid delegatee references found")
        else:
            crefs += self.get_delegated_to()

        self.setDelegatedTo(list(set(crefs)))

    def get_cutype(self, translated=False):
        cutype = self.cutype()
        if translated:
            return self._translate_value(cutype, self.cutype_map)
        return cutype

    def get_delegated_from(self, translated=False):
        delegators = []
        for cr in self.delegatedFrom():
            delegators.append(cr.email() if translated else ContactReference(cr))
        return delegators

    def get_delegated_to(self, translated=False):
        delegatees = []
        for cr in self.delegatedTo():
            delegatees.append(cr.email() if translated else ContactReference(cr))
        return delegatees

    def get_email(self):
        return self.contactreference.get_email()

    def get_name(self):
        return self.contactreference.get_name()

    def get_displayname(self):
        name = self.contactreference.get_name()
        email = self.contactreference.get_email()
        return "%s <%s>" % (name, email) if not name == "" else email

    def get_participant_status(self, translated=False):
        partstat = self.partStat()
        if translated:
            return self._translate_value(partstat, self.participant_status_map)
        return partstat

    def get_role(self, translated=False):
        role = self.role()
        if translated:
            return self._translate_value(role, self.role_map)
        return role

    def get_rsvp(self):
        return self.rsvp()

    def _translate_value(self, val, map):
        name_map = dict([(v, k) for (k, v) in map.iteritems()])
        return name_map[val] if name_map.has_key(val) else 'UNKNOWN'

    def set_cutype(self, cutype):
        if cutype in self.cutype_map.keys():
            self.setCutype(self.cutype_map[cutype])
        elif cutype in self.cutype_map.values():
            self.setCutype(cutype)
        else:
            raise InvalidAttendeeCutypeError, _("Invalid cutype %r") % (cutype)

    def set_name(self, name):
        self.contactreference.set_name(name)
        self.setContact(self.contactreference)

    def set_participant_status(self, participant_status):
        if participant_status in self.participant_status_map.keys():
            self.setPartStat(self.participant_status_map[participant_status])
        elif participant_status in self.participant_status_map.values():
            self.setPartStat(participant_status)
        else:
            raise InvalidAttendeeParticipantStatusError, _("Invalid participant status %r") % (participant_status)

    def set_role(self, role):
        if role in self.role_map.keys():
            self.setRole(self.role_map[role])
        elif role in self.role_map.values():
            self.setRole(role)
        else:
            raise InvalidAttendeeRoleError, _("Invalid role %r") % (role)

    def set_rsvp(self, rsvp):
        self.setRSVP(rsvp)

    def to_dict(self):
        data = self.contactreference.to_dict()
        data.pop('type', None)

        for p, getter in self.properties_map.iteritems():
            val = None
            args = {}
            if hasattr(self, getter):
                if getter.startswith('get_'):
                    args = dict(translated=True)
                val = getattr(self, getter)(**args)
            if val is not None:
                data[p] = val

        return data

    def __str__(self):
        return self.email

class AttendeeIntegrityError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class InvalidAttendeeCutypeError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class InvalidAttendeeParticipantStatusError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class InvalidAttendeeRoleError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
