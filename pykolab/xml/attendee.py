import kolabformat

from pykolab.translate import _

from contact_reference import ContactReference

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
            # Not yet implemented
            #"COMPLETED": ,
            #"IN-PROCESS": ,
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

    def get_cutype(self):
        return self.cutype()

    def get_delegated_from(self):
        return self.delegatedFrom()

    def get_delegated_to(self):
        return self.delegatedTo()

    def get_email(self):
        return self.contactreference.get_email()

    def get_name(self):
        return self.contactreference.get_name()

    def get_participant_status(self):
        return self.partStat()

    def get_role(self):
        return self.role()

    def get_rsvp(self):
        return self.rsvp()

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
