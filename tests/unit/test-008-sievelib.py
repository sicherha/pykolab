import sys
import unittest

sieve_scripts = [

# You're average vacation script.
"""
require [ "vacation" ];

if anyof (true) {
    vacation :days 1 :subject "Out of Office" "I'm out of the office";
}
""",

# A non-any/allof if (control) header (test) structure
"""
require ["fileinto"];

if header :contains "X-Spam-Flag" "YES" {
    fileinto "Spam";
    stop;
}
""",

# The same, all on the same line
"""
require ["fileinto"];

if header :contains "X-Spam-Flag" "YES" { fileinto "Spam"; stop; }
""",

# A little more of a complex list of tests
"""
require ["fileinto"];

if allof (header :contains "X-Mailer" "OTRS", header :contains "X-Powered-By" "OTRS", header :contains "Organization" "Example, Inc.") { fileinto "OTRS"; stop; }
""",

    ]


class TestSievelib(unittest.TestCase):

    def test_001_import_sievelib(self):
        from sievelib.parser import Parser

    def test_002_parse_tests(self):
        from sievelib.parser import Parser
        sieve_parser = Parser(debug=True)

        i = 0
        for sieve_str in sieve_scripts:
            i += 1
            result = sieve_parser.parse(sieve_str)
            if not result:
                print "Sieve line: %r" % (sieve_parser.lexer.text.split('\n')[(sieve_parser.lexer.text[:sieve_parser.lexer.pos].count('\n'))])
                raise Exception("Failed parsing Sieve script #%d: %s" % (i, sieve_parser.error))
