import unittest

class TestImports(unittest.TestCase):
    def test_pykolab(self):
        import pykolab

    def test_pykolab_xml(self):
        import pykolab.xml

    def test_pykolab_xml_attendee(self):
        from pykolab.xml import Attendee

    def test_pykolab_xml_contact(self):
        from pykolab.xml import Contact

    def test_pykolab_xml_contactReference(self):
        from pykolab.xml import ContactReference

    def test_pykolab_xml_event(self):
        from pykolab.xml import Event

if __name__ == '__main__':
    unittest.main()
