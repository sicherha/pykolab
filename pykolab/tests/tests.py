# -*- coding: utf-8 -*-
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 or, at your option, any later version
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

import os
import sys

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.tests')
conf = pykolab.getConf()

tests = {}
test_groups = {}

def __init__():
    # We only want the base path
    tests_base_path = os.path.dirname(__file__)

    for tests_path, dirnames, filenames in os.walk(tests_base_path):
        if not tests_path == tests_base_path:
            continue

        for filename in filenames:
            #print filename
            if filename.startswith('test_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                test_name = module_name.replace('test_', '')
                #print "exec(\"from %s import __init__ as %s_register\"" %(module_name,test_name)
                exec("from %s import __init__ as %s_register" %(module_name,test_name))
                exec("%s_register()" %(test_name))

        for dirname in dirnames:
            register_group(tests_path, dirname)

    register('help', list_tests, description=_("List tests"))

def list_tests(*args, **kw):
    """
        List tests
    """

    __tests = {}

    for test in tests.keys():
        if isinstance(test, tuple):
            test_group, test = test
            __tests[test_group] = {
                    test: tests[(test_group,test)]
                }
        else:
            __tests[test] = tests[test]

    _tests = __tests.keys()
    _tests.sort()

    for _test in _tests:
        if not __tests[_test].has_key('group'):
            if __tests[_test].has_key('function'):
                # This is a top-level test
                if not __tests[_test]['description'] == None:
                    print "%-25s - %s" %(_test.replace('_','-'),__tests[_test]['description'])
                else:
                    print "%-25s" %(_test.replace('_','-'))

    for _test in _tests:
        if not __tests[_test].has_key('function'):
            # This is a nested test
            print "\n" + _("Test Suite: %s") %(_test) + "\n"
            ___tests = __tests[_test].keys()
            ___tests.sort()
            for __test in ___tests:
                if not __tests[_test][__test]['description'] == None:
                    print "%-4s%-21s - %s" %('',__test.replace('_','-'),__tests[_test][__test]['description'])
                else:
                    print "%-4s%-21s" %('',__test.replace('_','-'))

def execute(test_name, *args, **kw):
    print "tests:", tests
    print "test_name:", test_name

    if not tests.has_key(test_name):
        log.error(_("No such test."))
        sys.exit(1)

    if not tests[test_name].has_key('function') and \
        not tests[test_name].has_key('group'):
        log.error(_("No such test."))
        sys.exit(1)

    if tests[test_name].has_key('group'):
        group = tests[test_name]['group']
        _test_name = tests[test_name]['test_name']
        try:
            exec("from %s.test_%s import cli_options as %s_%s_cli_options" %(group,_test_name,group,test_name))
            exec("%s_%s_cli_options()" %(group,test_name))
        except ImportError, e:
            pass

    else:
        try:
            exec("from test_%s import cli_options as %s_cli_options" %(test_name,test_name))
            exec("%s_cli_options()" %(test_name))
        except ImportError, e:
            pass

    conf.finalize_conf()

    tests[test_name]['function'](conf.cli_args, kw)

def register_group(dirname, module):
    tests_base_path = os.path.join(os.path.dirname(__file__), module)

    tests[module] = {}

    for tests_path, dirnames, filenames in os.walk(tests_base_path):
        if not tests_path == tests_base_path:
            continue

        for filename in filenames:
            if filename.startswith('test_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                test_name = module_name.replace('test_', '')
                #print "exec(\"from %s.%s import __init__ as %s_%s_register\"" %(module,module_name,module,test_name)
                exec("from %s.%s import __init__ as %s_%s_register" %(module,module_name,module,test_name))
                exec("%s_%s_register()" %(module,test_name))

def register(test_name, func, group=None, description=None, aliases=[]):
    if not group == None:
        test = "%s_%s" %(group,test_name)
    else:
        test = test_name

    #print "registering", test

    if isinstance(aliases, basestring):
        aliases = [aliases]

    if tests.has_key(test):
        log.fatal(_("Test '%s' already registered") %(test))
        sys.exit(1)

    if tests.has_key(test):
        log.fatal(_("Test '%s' already registered") %(test))
        sys.exit(1)

    if callable(func):
        if group == None:
            tests[test_name] = {
                    'function': func,
                    'description': description
                }
        else:
            tests[group][test_name] = {
                    'function': func,
                    'description': description
                }

            tests[test] = tests[group][test_name]
            tests[test]['group'] = group
            tests[test]['test_name'] = test_name

        for alias in aliases:
            tests[alias] = {
                    'function': func,
                    'description': _("Alias for %s") %(test_name)
                }

##
## Tests not yet implemented
##

def not_yet_implemented(*args, **kw):
    print _("Not yet implemented")
    sys.exit(1)