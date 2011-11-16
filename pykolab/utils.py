# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
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

import getpass
import os
import sys

from pykolab import constants
from pykolab.translate import _

def ask_question(question, default="", password=False):
    """
        Ask a question on stderr.

        Since the answer to the question may actually be a password, cover that
        case with a getpass.getpass() prompt.

        Accepts a default value, but ignores defaults for password prompts.

        Usage: pykolab.utils.ask_question("What is the server?", default="localhost")
    """
    if password:
        answer = getpass.getpass("%s: " %(question))
    else:
        if default == "":
            answer = raw_input("%s: " %(question))
        else:
            answer = raw_input("%s [%s]: " %(question, default))

    if answer == "":
        return default
    else:
        return answer

def ask_confirmation(question, default="y", all_inclusive_no=True):
    """
        Create a confirmation dialog, including a default option (capitalized),
        and a "yes" or "no" parsing that can either require an explicit, full
        "yes" or "no", or take the default or any YyNn answer.
    """

    if default in [ "y", "Y" ]:
        default_answer = True
        default_no = "n"
        default_yes = "Y"
    elif default in [ "n", "N" ]:
        default_answer = True
        default_no = "N"
        default_yes = "y"
    else:
        # This is a 'yes' or 'no' question the user
        # needs to provide the full yes or no for.
        default_no = "'no'"
        default_yes = "Please type 'yes'"

    answer = False
    while answer == False:
        answer = raw_input("%s [%s/%s]: " %(question,default_yes,default_no))
        # Parse answer and set back to False if not appropriate
        if all_inclusive_no:
            if not answer in [ "y", "Y", "yes" ]:
                return False
            else:
                return True
        else:
            if answer in [ "y", "Y", "yes" ]:
                return True
            elif answer in [ "n", "N", "no" ]:
                return False
            elif answer == "" and not default_answer == None:
                return default_answer
            else:
                answer = False
                print >> sys.stderr, _("Please answer 'yes' or 'no'.")

def normalize(_object):
    if type(_object) == list:
        result = []
    elif type(_object) == dict:
        result = {}
    else:
        return _object

    if type(_object) == list:
        for item in _object:
            result.append(item.lower())
        result = list(set(result))
        return result

    elif type(_object) == dict:
        for key in _object.keys():
            if type(_object[key]) == list:
                if _object[key] == None:
                    continue
                if len(_object[key]) == 1:
                    result[key.lower()] = ''.join(_object[key])
                else:
                    result[key.lower()] = _object[key]
            else:
                if _object[key] == None:
                    continue
                # What the heck?
                result[key.lower()] = _object[key]

        if result.has_key('sn'):
            result['surname'] = result['sn'].replace(' ', '')

        if result.has_key('mail'):
            if len(result['mail']) > 0:
                if len(result['mail'].split('@')) > 1:
                    result['domain'] = result['mail'].split('@')[1]

        if not result.has_key('domain') and result.has_key('standard_domain'):
            result['domain'] = result['standard_domain']

        return result

def parse_input(_input, splitchars= [ ' ' ]):
    """
        Split the input string using the split characters defined
        in splitchars, and remove the empty list items, then unique the
        list items.

        Takes a string as input, and a list of characters the string should be
        split with (list of delimiter characters).
    """

    _parse_list = _input.split(splitchars.pop())
    _output_list = []

    for splitchar in splitchars:
        __parse_list = []
        for item in _parse_list:
            __parse_list.extend(item.split(splitchar))
        _parse_list = __parse_list

    for item in _parse_list:
        if not item == '':
            if _output_list.count(item) < 1:
                _output_list.append(item)

    return _output_list

def parse_ldap_uri(uri):
    """
        Parse an LDAP URI and return it's components.

        Returns a tuple containing;

         - protocol (ldap, ldaps),
         - server (address or None),
         - base_dn,
         - attrs (list of attributes length 1, or empty),
         - scope,
         - filter

        or None on failure
    """

    try:
        _protocol = uri.split(':')[0]
        _ldap_uri, _attr, _scope, _filter = uri.split('?')
        _server = _ldap_uri.split('//')[1].split('/')[0]
        _base_dn = _ldap_uri.split('//')[1].split('/')[1]

        if _server == '':
            _server = None
        if _attr == '':
            _attrs = []
        else:
            _attrs = [ _attr ]

        if _scope == '':
            _scope = 'sub'

        if _filter == '':
            _filter = "(objectclass=*)"

        return (_protocol, _server, _base_dn, _attr, _scope, _filter)

    except:
        return None

def pop_empty_from_list(_input_list):
    _output_list = []

    for item in _input_list:
        if not item == '':
            _output_list.append(item)

def standard_root_dn(domain):
    return 'dc=%s' %(',dc='.join(domain.split('.')))

def is_service(services):
    """
        Checks each item in list services to see if it has a RC script in
        pykolab.constants.RC_DIR to see if it's a service, and returns
        the name of the service for the first service it can find. However,
        it also checks whether the other services exist and issues a warning if
        more then one service exists.

        Usage: utils.is_service(['dirsrv', 'ldap'])
    """
    _service = None
    _other_services = []

    for service in services:
        if os.path.isfile(os.path.join(constants.RC_DIR, service)):
            if _service == '':
                _service = service
            else:
                _other_services.append(service)

    return (_service,_other_services)
