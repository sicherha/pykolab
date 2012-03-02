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

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

modules = {}

def __init__():
    # We only want the base path
    modules_base_path = os.path.dirname(__file__)

    for modules_path, dirnames, filenames in os.walk(modules_base_path):
        if not modules_path == modules_base_path:
            continue

        for filename in filenames:
            if filename.startswith('module_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                name = module_name.replace('module_', '')
                #print "exec(\"from %s import __init__ as %s_register\"" %(module_name,name)
                exec("from %s import __init__ as %s_register" %(module_name,name))
                exec("%s_register()" %(name))

        for dirname in dirnames:
            register_group(modules_path, dirname)

def list_modules(*args, **kw):
    """
        List modules
    """

    __modules = {}

    for module in modules.keys():
        if isinstance(module, tuple):
            module_group, module = module
            __modules[module_group] = {
                    module: modules[(module_group,module)]
                }
        else:
            __modules[module] = modules[module]

    _modules = __modules.keys()
    _modules.sort()

    for _module in _modules:
        if __modules[_module].has_key('function'):
            # This is a top-level module
            if not __modules[_module]['description'] == None:
                print "%-25s - %s" %(_module.replace('_','-'),__modules[_module]['description'])
            else:
                print "%-25s" %(_module.replace('_','-'))

    for _module in _modules:
        if not __modules[_module].has_key('function'):
            # This is a nested module
            print "\n" + _("Module Group: %s") %(_module) + "\n"
            ___modules = __modules[_module].keys()
            ___modules.sort()
            for __module in ___modules:
                if not __modules[_module][__module]['description'] == None:
                    print "%-4s%-21s - %s" %('',__module.replace('_','-'),__modules[_module][__module]['description'])
                else:
                    print "%-4s%-21s" %('',__module.replace('_','-'))

def execute(name, *args, **kw):
    if not modules.has_key(name):
        log.error(_("No such module."))
        sys.exit(1)

    if not modules[name].has_key('function') and \
        not modules[name].has_key('group'):
        log.error(_("No such module."))
        sys.exit(1)

    modules[name]['function'](*args, **kw)

def cb_action_HOLD(module, filepath):
    log.info(_("Holding message in queue for manual review (%s by %s)") %(filepath, module))
    ## Actually just unlink the file for now
    #os.unlink(filepath)

def cb_action_DEFER(module, filepath):
    log.info(_("Deferring message in %s (by module %s)") %(filepath, module))

def cb_action_REJECT(module, filepath):
    log.info(_("Rejecting message in %s (by module %s)") %(filepath, module))
    # Send NDR, unlink file
    os.unlink(filepath)

def cb_action_ACCEPT(module, filepath):
    log.info(_("Accepting message in %s (by module %s)") %(filepath, module))
    # Deliver for final delivery (use re-injection smtpd), unlink file
    os.unlink(filepath)

def register_group(dirname, module):
    modules_base_path = os.path.join(os.path.dirname(__file__), module)

    modules[module] = {}

    for modules_path, dirnames, filenames in os.walk(modules_base_path):
        if not modules_path == modules_base_path:
            continue

        for filename in filenames:
            if filename.startswith('module_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                name = module_name.replace('module_', '')
                #print "exec(\"from %s.%s import __init__ as %s_%s_register\"" %(module,module_name,module,name)
                exec("from %s.%s import __init__ as %s_%s_register" %(module,module_name,module,name))
                exec("%s_%s_register()" %(module,name))

def register(name, func, group=None, description=None, aliases=[]):
    if not group == None:
        module = "%s_%s" %(group,name)
    else:
        module = name

    if isinstance(aliases, basestring):
        aliases = [aliases]

    if modules.has_key(module):
        log.fatal(_("Module '%s' already registered") %(module))
        sys.exit(1)

    if callable(func):
        if group == None:
            modules[name] = {
                    'function': func,
                    'description': description
                }
        else:
            modules[group][name] = {
                    'function': func,
                    'description': description
                }

            modules[module] = modules[group][name]
            modules[module]['group'] = group
            modules[module]['name'] = name

        for alias in aliases:
            modules[alias] = {
                    'function': func,
                    'description': _("Alias for %s") %(name)
                }

