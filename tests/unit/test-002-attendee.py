import datetime
import unittest
import kolabformat

from pykolab.xml import Attendee
from pykolab.xml import participant_status_label

class TestEventXML(unittest.TestCase):
    attendee = Attendee("jane@doe.org")

    def assertIsInstance(self, _value, _type):
        if hasattr(unittest.TestCase, 'assertIsInstance'):
            return unittest.TestCase.assertIsInstance(self, _value, _type)
        else:
            if (type(_value)) == _type:
                return True
            else:
                raise AssertionError, "%s != %s" % (type(_value), _type)

    def test_001_minimal(self):
        self.assertIsInstance(self.attendee.__str__(), str)

    def test_002_empty_name(self):
        self.assertEqual(self.attendee.get_name(), "")

    def test_003_set_name(self):
        name = "Doe, Jane"
        self.attendee.set_name(name)
        self.assertEqual(self.attendee.get_name(), name)

    def test_004_default_participant_status(self):
        self.assertEqual(self.attendee.get_participant_status(), 0)

    def test_005_participant_status_map_length(self):
        self.assertEqual(len(self.attendee.participant_status_map.keys()), 7)

    def test_006_participant_status_map_forward_lookup(self):
        # Forward lookups
        self.assertEqual(self.attendee.participant_status_map["NEEDS-ACTION"], 0)
        self.assertEqual(self.attendee.participant_status_map["ACCEPTED"], 1)
        self.assertEqual(self.attendee.participant_status_map["DECLINED"], 2)
        self.assertEqual(self.attendee.participant_status_map["TENTATIVE"], 3)
        self.assertEqual(self.attendee.participant_status_map["DELEGATED"], 4)
        self.assertEqual(self.attendee.participant_status_map["IN-PROCESS"], 5)
        self.assertEqual(self.attendee.participant_status_map["COMPLETED"], 6)

    def test_007_participant_status_map_reverse_lookup(self):
        # Reverse lookups
        self.assertEqual([k for k,v in self.attendee.participant_status_map.iteritems() if v == 0][0], "NEEDS-ACTION")
        self.assertEqual([k for k,v in self.attendee.participant_status_map.iteritems() if v == 1][0], "ACCEPTED")
        self.assertEqual([k for k,v in self.attendee.participant_status_map.iteritems() if v == 2][0], "DECLINED")
        self.assertEqual([k for k,v in self.attendee.participant_status_map.iteritems() if v == 3][0], "TENTATIVE")
        self.assertEqual([k for k,v in self.attendee.participant_status_map.iteritems() if v == 4][0], "DELEGATED")
        self.assertEqual([k for k,v in self.attendee.participant_status_map.iteritems() if v == 5][0], "IN-PROCESS")
        self.assertEqual([k for k,v in self.attendee.participant_status_map.iteritems() if v == 6][0], "COMPLETED")

    def test_008_default_rsvp(self):
        self.assertEqual(self.attendee.get_rsvp(), 0)

    def test_009_rsvp_map_length(self):
        self.assertEqual(len(self.attendee.rsvp_map.keys()), 2)

    def test_010_rsvp_map_forward_lookup_boolean(self):
        self.assertEqual(self.attendee.rsvp_map["TRUE"], True)
        self.assertEqual(self.attendee.rsvp_map["FALSE"], False)

    def test_011_rsvp_map_forward_lookup_integer(self):
        self.assertEqual(self.attendee.rsvp_map["TRUE"], 1)
        self.assertEqual(self.attendee.rsvp_map["FALSE"], 0)

    def test_012_rsvp_map_reverse_lookup_boolean(self):
        self.assertEqual([k for k,v in self.attendee.rsvp_map.iteritems() if v == True][0], "TRUE")
        self.assertEqual([k for k,v in self.attendee.rsvp_map.iteritems() if v == False][0], "FALSE")

    def test_013_rsvp_map_reverse_lookup_integer(self):
        self.assertEqual([k for k,v in self.attendee.rsvp_map.iteritems() if v == 1][0], "TRUE")
        self.assertEqual([k for k,v in self.attendee.rsvp_map.iteritems() if v == 0][0], "FALSE")

    def test_014_default_role(self):
        self.assertEqual(self.attendee.get_role(), 0)

    def test_015_role_map_length(self):
        self.assertEqual(len(self.attendee.role_map.keys()), 4)

    def test_016_role_map_forward_lookup(self):
        self.assertEqual(self.attendee.role_map["REQ-PARTICIPANT"], 0)
        self.assertEqual(self.attendee.role_map["CHAIR"], 1)
        self.assertEqual(self.attendee.role_map["OPT-PARTICIPANT"], 2)
        self.assertEqual(self.attendee.role_map["NON-PARTICIPANT"], 3)

    def test_017_role_map_reverse_lookup(self):
        self.assertEqual([k for k,v in self.attendee.role_map.iteritems() if v == 0][0], "REQ-PARTICIPANT")
        self.assertEqual([k for k,v in self.attendee.role_map.iteritems() if v == 1][0], "CHAIR")
        self.assertEqual([k for k,v in self.attendee.role_map.iteritems() if v == 2][0], "OPT-PARTICIPANT")
        self.assertEqual([k for k,v in self.attendee.role_map.iteritems() if v == 3][0], "NON-PARTICIPANT")

    def test_015_cutype_map_length(self):
        self.assertEqual(len(self.attendee.cutype_map.keys()), 3)

    def test_016_cutype_map_forward_lookup(self):
        self.assertEqual(self.attendee.cutype_map["GROUP"], 1)
        self.assertEqual(self.attendee.cutype_map["INDIVIDUAL"], 2)
        self.assertEqual(self.attendee.cutype_map["RESOURCE"], 3)

    def test_017_cutype_map_reverse_lookup(self):
        self.assertEqual([k for k,v in self.attendee.cutype_map.iteritems() if v == 1][0], "GROUP")
        self.assertEqual([k for k,v in self.attendee.cutype_map.iteritems() if v == 2][0], "INDIVIDUAL")
        self.assertEqual([k for k,v in self.attendee.cutype_map.iteritems() if v == 3][0], "RESOURCE")

    def test_018_partstat_label(self):
        self.assertEqual(participant_status_label('NEEDS-ACTION'), "Needs Action")
        self.assertEqual(participant_status_label(kolabformat.PartTentative), "Tentatively Accepted")
        self.assertEqual(participant_status_label('UNKNOWN'), "UNKNOWN")

    def test_020_to_dict(self):
        name = "Doe, Jane"
        role = 'OPT-PARTICIPANT'
        cutype = 'RESOURCE'
        partstat = 'ACCEPTED'
        self.attendee.set_name(name)
        self.attendee.set_rsvp(True)
        self.attendee.set_role(role)
        self.attendee.set_cutype(cutype)
        self.attendee.set_participant_status(partstat)

        data = self.attendee.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['role'], role)
        self.assertEqual(data['cutype'], cutype)
        self.assertEqual(data['partstat'], partstat)
        self.assertEqual(data['name'], name)
        self.assertEqual(data['email'], 'jane@doe.org')
        self.assertTrue(data['rsvp'])

if __name__ == '__main__':
    unittest.main()
