import kolabformat

from contact_reference import ContactReference

class Attendee(kolabformat.Attendee):
    partstat_map = {
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

    def __init__(self, email, name=None, rsvp=False, role=None, participant_status=None):
        self.email = email

        contactreference = ContactReference(email)

        if not name == None:
            contactreference.set_name(name)

        kolabformat.Attendee.__init__(self, contactreference)

        if isinstance(rsvp, bool):
            self.setRSVP(rsvp)
        else:
            if self.rsvp_map.has_key(rsvp):
                self.setRSVP(self.rsvp_map[rsvp])

        if not role == None:
            self.set_role(role)

        if not participant_status == None:
            self.set_participant_status(participant_status)

    def set_participant_status(self, participant_status):
        if self.participant_status_map.has_key(participant_status):
            self.setPartStat(self.participant_status_map[participant_status])

    def set_role(self, role):
        if self.role_map.has_key(role):
            self.setRole(self.role_map[role])

    def __str__(self):
        return self.email
