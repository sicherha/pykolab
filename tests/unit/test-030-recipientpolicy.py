# -*- coding: utf-8 -*-

import unittest

from pykolab.plugins.recipientpolicy import KolabRecipientpolicy

policy = KolabRecipientpolicy()


class TestRecipientPolicy(unittest.TestCase):
    def test_001_primary_mail(self):
        """
            The spaces in attributes used for mail generation.
        """

        entry = {
            'surname': ' sn ',
            'givenname': ' gn ',
        }

        mail = policy.set_primary_mail(
            primary_mail='%(givenname)s.%(surname)s@%(domain)s',
            primary_domain='example.org',
            entry=entry
        )

        self.assertEqual('gn.sn@example.org', mail)

if __name__ == '__main__':
    unittest.main()
