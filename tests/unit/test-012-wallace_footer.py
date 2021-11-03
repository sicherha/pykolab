# -*- coding: utf-8 -*-

import os
import pykolab
import unittest

from wallace import module_footer as Footer

conf = pykolab.getConf()

if not hasattr(conf, 'defaults'):
    conf.finalize_conf()


class TestWallaceFooter(unittest.TestCase):

    def test_001_append_footer_plain(self):
        # bottom
        content = Footer.append_footer('test', 'footer')
        self.assertEqual('test\n\n-- \nfooter', content)

        # top
        content = Footer.append_footer('test', 'footer', 'top')
        self.assertEqual('footer\n\ntest', content)

    def test_001_append_footer_html(self):
        foot = "\n<!-- footer appended by Wallace -->\nfooter\n<!-- footer end -->\n"

        # bottom
        content = Footer.append_footer('<p>test</p>', 'footer', None, True)
        self.assertEqual('<html><body><p>test</p>' + foot + '</body></html>', content)

        content = Footer.append_footer('<body><p>test</p></body>', 'footer', None, True)
        self.assertEqual('<body><p>test</p>' + foot + '</body>', content)

        content = Footer.append_footer('<BODY><p>test</p></BODY>', 'footer', None, True)
        self.assertEqual('<BODY><p>test</p>' + foot + '</BODY>', content)

        # top
        content = Footer.append_footer('<p>test</p>', 'footer', 'top', True)
        self.assertEqual('<html><body>' + foot + '<p>test</p></body></html>', content)

        content = Footer.append_footer('<body color=red"><p>test</p>', 'footer', 'top', True)
        self.assertEqual('<body color=red">' + foot + '<p>test</p>', content)

        content = Footer.append_footer('<BODY\ncolor=red"><p>test</p>', 'footer', 'top', True)
        self.assertEqual('<BODY\ncolor=red">' + foot + '<p>test</p>', content)
