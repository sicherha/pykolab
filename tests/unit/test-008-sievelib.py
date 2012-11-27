import sys
import unittest

sieve_scripts = [
        """
require [ "vacation" ];

if anyof (true) {
    vacation :days 1 :subject "Out of Office" "I'm out of the office";
}
""",

    ]

class TestSievelib(unittest.TestCase):

    def test_001_import_sievelib(self):
        from sievelib.parser import Parser

    def test_002_parse_vacation(self):
        from sievelib.parser import Parser
        sieve_parser = Parser(debug=True)

        i = 0
        for sieve_str in sieve_scripts:
            i += 1
            result = sieve_parser.parse(sieve_str)
            if not result:
                raise Exception, "Failed parsing Sieve script #%d: %s" % (i, sieve_parser.error)
