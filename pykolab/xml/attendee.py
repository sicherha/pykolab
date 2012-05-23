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

    role_map = {
            "REQ-PARTICIPANT": kolabformat.Required,
            "CHAIR": kolabformat.Chair,
            "OPTIONAL": kolabformat.Optional,
            "NONPARTICIPANT": kolabformat.NonParticipant,
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
            cutype=None
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

        if not participant_status == None:
            self.set_participant_status(participant_status)

        if not cutype == None:
            self.set_cutype(cutype)

    def get_email(self):
        return self.contactreference.get_email()

    def get_name(self):
        return self.contactreference.get_name()

    def get_participant_status(self):
        return self.partStat()

    def set_cutype(self, cutype):
        if cutype in self.cutype_map.keys():
            self.setCutype(self.cutype_map[cutype])
        elif cutype in self.cutype_map.values():
            self.setCutype(cutype)
        else:
            raise InvalidAttendeeCutypeError, _("Invalid cutype %r") % (cutype)

    def set_name(self, name):
        self.contactreference.set_name(name)

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
