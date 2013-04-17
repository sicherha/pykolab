# -*- coding: utf-8 -*-
#
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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

import pykolab

from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

components = {}
component_groups = {}
executed_components = []

components_included_in_cli = []

finalize_conf_ok = None

def __init__():
    # We only want the base path
    components_base_path = os.path.dirname(__file__)

    for components_path, dirnames, filenames in os.walk(components_base_path):
        if not components_path == components_base_path:
            continue

        for filename in filenames:
            if filename.startswith('setup_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                component_name = module_name.replace('setup_', '')
                #print "exec(\"from %s import __init__ as %s_register\"" % (module_name,component_name)
                exec("from %s import __init__ as %s_register" % (module_name,component_name))
                exec("%s_register()" % (component_name))

        for dirname in dirnames:
            register_group(components_path, dirname)

    register('help', list_components, description=_("Display this help."))

def list_components(*args, **kw):
    """
        List components
    """

    __components = {}

    for component in components.keys():
        if isinstance(component, tuple):
            component_group, component = component
            __components[component_group] = {
                    component: components[(component_group,component)]
                }
        else:
            __components[component] = components[component]

    _components = __components.keys()
    _components.sort()

    for _component in _components:
        if __components[_component].has_key('function'):
            # This is a top-level component
            if not __components[_component]['description'] == None:
                print "%-25s - %s" % (_component.replace('_','-'),__components[_component]['description'])
            else:
                print "%-25s" % (_component.replace('_','-'))

    for _component in _components:
        if not __components[_component].has_key('function'):
            # This is a nested component
            print "\n" + _("Command Group: %s") % (_component) + "\n"
            ___components = __components[_component].keys()
            ___components.sort()
            for __component in ___components:
                if not __components[_component][__component]['description'] == None:
                    print "%-4s%-21s - %s" % ('',__component.replace('_','-'),__components[_component][__component]['description'])
                else:
                    print "%-4s%-21s" % ('',__component.replace('_','-'))

def _list_components(*args, **kw):
    """
        List components and return API compatible, parseable lists and
        dictionaries.
    """

    __components = {}

    for component in components.keys():
        if isinstance(component, tuple):
            component_group, component = component
            __components[component_group] = {
                    component: components[(component_group,component)]
                }
        else:
            __components[component] = components[component]

    _components = __components.keys()
    _components.sort()

    return _components

def cli_options_from_component(component_name, *args, **kw):
    global components_included_in_cli

    if component_name in components_included_in_cli:
        return

    if components[component_name].has_key('group'):
        group = components[component_name]['group']
        component_name = components[component_name]['component_name']
        try:
            exec("from %s.setup_%s import cli_options as %s_%s_cli_options" % (group,component_name,group,component_name))
            exec("%s_%s_cli_options()" % (group,component_name))
        except ImportError, e:
            pass

    else:
        try:
            exec("from setup_%s import cli_options as %s_cli_options" % (component_name,component_name))
            exec("%s_cli_options()" % (component_name))
        except ImportError, e:
            pass

    components_included_in_cli.append(component_name)

def execute(component_name, *args, **kw):
    if component_name == '':

        log.debug(
                _("No component selected, continuing for all components"),
                level=8
            )

        while 1:
            for component in _list_components():
                execute_this = True

                if component in executed_components:
                    execute_this = False

                if component == "help":
                    execute_this = False

                if execute_this:
                    if components[component].has_key('after'):
                        for _component in components[component]['after']:
                            if not _component in executed_components:
                                execute_this = False

                if execute_this:
                    execute(component)
                    executed_components.append(component)

            executed_all = True
            for component in _list_components():
                if not component in executed_components and not component == "help":
                    executed_all = False

            if executed_all:
                break

        return
    else:
        for component in _list_components():
            cli_options_from_component(component)

    if not components.has_key(component_name):
        log.error(_("No such component."))
        sys.exit(1)

    if not components[component_name].has_key('function') and \
        not components[component_name].has_key('group'):
        log.error(_("No such component."))
        sys.exit(1)

    conf.finalize_conf()

    if len(conf.cli_args) >= 1:
        _component_name = conf.cli_args.pop(0)
    else:
        _component_name = component_name

    components[component_name]['function'](conf.cli_args, kw)

def register_group(dirname, module):
    components_base_path = os.path.join(os.path.dirname(__file__), module)

    components[module] = {}

    for components_path, dirnames, filenames in os.walk(components_base_path):
        if not components_path == components_base_path:
            continue

        for filename in filenames:
            if filename.startswith('setup_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                component_name = module_name.replace('setup_', '')
                #print "exec(\"from %s.%s import __init__ as %s_%s_register\"" % (module,module_name,module,component_name)
                exec("from %s.%s import __init__ as %s_%s_register" % (module,module_name,module,component_name))
                exec("%s_%s_register()" % (module,component_name))

def register(component_name, func, group=None, description=None, aliases=[], after=[], before=[]):
    if not group == None:
        component = "%s_%s" % (group,component_name)
    else:
        component = component_name

    if isinstance(aliases, basestring):
        aliases = [aliases]

    if components.has_key(component):
        log.fatal(_("Command '%s' already registered") % (component))
        sys.exit(1)

    if callable(func):
        if group == None:
            components[component_name] = {
                    'function': func,
                    'description': description,
                    'after': after,
                    'before': before,
                }
        else:
            components[group][component_name] = {
                    'function': func,
                    'description': description,
                    'after': after,
                    'before': before,
                }

            components[component] = components[group][component_name]
            components[component]['group'] = group
            components[component]['component_name'] = component_name

        for alias in aliases:
            components[alias] = {
                    'function': func,
                    'description': _("Alias for %s") % (component_name)
                }

##
## Commands not yet implemented
##

def not_yet_implemented(*args, **kw):
    print _("Not yet implemented")
    sys.exit(1)
