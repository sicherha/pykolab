# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

commands = {}
command_groups = {}

def __init__():
    # We only want the base path
    commands_base_path = os.path.dirname(__file__)

    for commands_path, dirnames, filenames in os.walk(commands_base_path):
        if not commands_path == commands_base_path:
            continue

        for filename in filenames:
            if filename.startswith('cmd_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                cmd_name = module_name.replace('cmd_', '')
                #print "exec(\"from %s import __init__ as %s_register\"" % (module_name,cmd_name)
                try:
                    exec("from %s import __init__ as %s_register" % (module_name,cmd_name))
                except ImportError, errmsg:
                    pass

                exec("%s_register()" % (cmd_name))

        for dirname in dirnames:
            register_group(commands_path, dirname)

    register('help', list_commands)

    register('delete_user', not_yet_implemented, description="Not yet implemented")

    register('list_groups', not_yet_implemented, description="Not yet implemented")
    register('add_group', not_yet_implemented, description="Not yet implemented")
    register('delete_group', not_yet_implemented, description="Not yet implemented")

def list_commands(*args, **kw):
    """
        List commands
    """

    __commands = {}

    for command in commands.keys():
        if isinstance(command, tuple):
            command_group, command = command
            __commands[command_group] = {
                    command: commands[(command_group,command)]
                }
        else:
            __commands[command] = commands[command]

    _commands = __commands.keys()
    _commands.sort()

    for _command in _commands:
        if __commands[_command].has_key('group'):
            continue

        if __commands[_command].has_key('function'):
            # This is a top-level command
            if not __commands[_command]['description'] == None:
                print "%-25s - %s" % (_command.replace('_','-'),__commands[_command]['description'])
            else:
                print "%-25s" % (_command.replace('_','-'))

    for _command in _commands:
        if not __commands[_command].has_key('function'):
            # This is a nested command
            print "\n" + _("Command Group: %s") % (_command) + "\n"
            ___commands = __commands[_command].keys()
            ___commands.sort()
            for __command in ___commands:
                if not __commands[_command][__command]['description'] == None:
                    print "%-4s%-21s - %s" % ('',__command.replace('_','-'),__commands[_command][__command]['description'])
                else:
                    print "%-4s%-21s" % ('',__command.replace('_','-'))

def execute(cmd_name, *args, **kw):
    if cmd_name == "":
        execute("help")
        sys.exit(0)

    if not commands.has_key(cmd_name):
        log.error(_("No such command."))
        sys.exit(1)

    if not commands[cmd_name].has_key('function') and \
        not commands[cmd_name].has_key('group'):
        log.error(_("No such command."))
        sys.exit(1)

    if commands[cmd_name].has_key('group'):
        group = commands[cmd_name]['group']
        command_name = commands[cmd_name]['cmd_name']
        try:
            exec("from %s.cmd_%s import cli_options as %s_%s_cli_options" % (group,command_name,group,command_name))
            exec("%s_%s_cli_options()" % (group,command_name))
        except ImportError, e:
            pass

    else:
        command_name = commands[cmd_name]['cmd_name']
        try:
            exec("from cmd_%s import cli_options as %s_cli_options" % (command_name,command_name))
            exec("%s_cli_options()" % (command_name))
        except ImportError, errmsg:
            pass

    conf.finalize_conf()
    commands[cmd_name]['function'](conf.cli_args, kw)

def register_group(dirname, module):
    commands_base_path = os.path.join(os.path.dirname(__file__), module)

    commands[module] = {}

    for commands_path, dirnames, filenames in os.walk(commands_base_path):
        if not commands_path == commands_base_path:
            continue

        for filename in filenames:
            if filename.startswith('cmd_') and filename.endswith('.py'):
                module_name = filename.replace('.py','')
                cmd_name = module_name.replace('cmd_', '')
                #print "exec(\"from %s.%s import __init__ as %s_%s_register\"" % (module,module_name,module,cmd_name)
                exec("from %s.%s import __init__ as %s_%s_register" % (module,module_name,module,cmd_name))
                exec("%s_%s_register()" % (module,cmd_name))

def register(cmd_name, func, group=None, description=None, aliases=[]):
    if not group == None:
        command = "%s_%s" % (group,cmd_name)
    else:
        command = cmd_name

    if isinstance(aliases, basestring):
        aliases = [aliases]

    if commands.has_key(command):
        log.fatal(_("Command '%s' already registered") % (command))
        sys.exit(1)

    if callable(func):
        if group == None:
            commands[cmd_name] = {
                    'cmd_name': cmd_name,
                    'function': func,
                    'description': description
                }
        else:
            commands[group][cmd_name] = {
                    'cmd_name': cmd_name,
                    'function': func,
                    'description': description
                }

            commands[command] = commands[group][cmd_name]
            commands[command]['group'] = group
            commands[command]['cmd_name'] = cmd_name

        for alias in aliases:
            commands[alias] = {
                    'cmd_name': cmd_name,
                    'function': func,
                    'description': _("Alias for %s") % (cmd_name.replace('_','-'))
                }

##
## Commands not yet implemented
##

def not_yet_implemented(*args, **kw):
    print _("Not yet implemented")
    sys.exit(1)
