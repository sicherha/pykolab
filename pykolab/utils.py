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

import getpass
import grp
import os
import pwd
import sys

import pykolab
from pykolab import constants
from pykolab.translate import _

log = pykolab.getLogger('pykolab.utils')

def ask_question(question, default="", password=False, confirm=False):
    """
        Ask a question on stderr.

        Since the answer to the question may actually be a password, cover that
        case with a getpass.getpass() prompt.

        Accepts a default value, but ignores defaults for password prompts.

        Usage: pykolab.utils.ask_question("What is the server?", default="localhost")
    """
    if password:
        if default == "" or default == None:
            answer = getpass.getpass("%s: " % (question))
        else:
            answer = getpass.getpass("%s [%s]: " % (question, default))
    else:
        if default == "" or default == None:
            answer = raw_input("%s: " % (question))
        else:
            answer = raw_input("%s [%s]: " % (question, default))

    if not answer == "":
        if confirm:
            answer_confirm = None
            answer_confirmed = False
            while not answer_confirmed:
                if password:
                    answer_confirm = getpass.getpass(_("Confirm %s: ") % (question))
                else:
                    answer_confirm = raw_input(_("Confirm %s: ") % (question))

                if not answer_confirm == answer:
                    print >> sys.stderr, _("Incorrect confirmation. " + \
                            "Please try again.")

                    if password:
                        if default == "" or default == None:
                            answer = getpass.getpass(_("%s: ") % (question))
                        else:
                            answer = getpass.getpass(_("%s [%s]: ") % (question, default))
                    else:
                        if default == "" or default == None:
                            answer = raw_input(_("%s: ") % (question))
                        else:
                            answer = raw_input(_("%s [%s]: ") % (question, default))

                else:
                    answer_confirmed = True

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
    default_answer = None

    if default in [ "y", "Y" ]:
        default_answer = True
        default_no = "n"
        default_yes = "Y"
    elif default in [ "n", "N" ]:
        default_answer = False
        default_no = "N"
        default_yes = "y"
    else:
        # This is a 'yes' or 'no' question the user
        # needs to provide the full yes or no for.
        default_no = "'no'"
        default_yes = "Please type 'yes'"

    answer = False
    while answer == False:
        answer = raw_input("%s [%s/%s]: " % (question,default_yes,default_no))
        # Parse answer and set back to False if not appropriate
        if all_inclusive_no:
            if answer == "" and not default_answer == None:
                return default_answer
            elif answer in [ "y", "Y", "yes" ]:
                return True
            elif answer in [ "n", "N", "no" ]:
                return False
            else:
                answer = False
                print >> sys.stderr, _("Please answer 'yes' or 'no'.")
        else:
            if not answer in [ "y", "Y", "yes" ]:
                return False
            else:
                return True

def ask_menu(question, options={}, default=''):
    if not default == '':
        print question + " [" + default + "]:"
    else:
        print question

    answer_correct = False
    max_key_length = 0

    if isinstance(options, list):
        _options = options
        options = {}
        for key in _options:
            options[key] = key
        
    keys = options.keys()
    keys.sort()

    while not answer_correct:
        for key in keys:
            key_length = len("%s" % key)
            if key_length > max_key_length:
                max_key_length = key_length

        str_format = "%%%ds" % max_key_length

        if default == '' or not default in options.keys():
            for key in keys:
                if options[key] == key:
                    print " - " + key
                else:
                    print " - " + eval("str_format % key") + ": " + options[key]

            answer = raw_input(_("Choice") + ": ")

        else:
            answer = raw_input(_("Choice (type '?' for options)") + ": ")

        if answer == '?':
            for key in keys:
                if options[key] == key:
                    print " - " + key
                else:
                    print " - " + eval("str_format % key") + ": " + options[key]

            continue

        if answer == '' and default in options.keys():
            answer = default

        if answer in [str(x) for x in options.keys()]:
            answer_correct = True

    return answer

def ensure_directory(_dir, _user='root', _group='root'):
    if not os.path.isdir(_dir):
        os.makedirs(_dir)

    try:
        try:
            (ruid, euid, suid) = os.getresuid()
            (rgid, egid, sgid) = os.getresgid()
        except AttributeError, errmsg:
            ruid = os.getuid()
            rgid = os.getgid()

        if ruid == 0:
            # Means we can setreuid() / setregid() / setgroups()
            if rgid == 0:
                # Get group entry details
                try:
                    (
                            group_name,
                            group_password,
                            group_gid,
                            group_members
                        ) = grp.getgrnam(_group)

                except KeyError:
                    print >> sys.stderr, _("Group %s does not exist") % (
                            _group
                        )

                    sys.exit(1)

                # Set real and effective group if not the same as current.
                if not group_gid == rgid:
                    os.chown(_dir, -1, group_gid)

            if ruid == 0:
                # Means we haven't switched yet.
                try:
                    (
                            user_name,
                            user_password,
                            user_uid,
                            user_gid,
                            user_gecos,
                            user_homedir,
                            user_shell
                        ) = pwd.getpwnam(_user)

                except KeyError:
                    print >> sys.stderr, _("User %s does not exist") % (_user)

                    sys.exit(1)


                # Set real and effective user if not the same as current.
                if not user_uid == ruid:
                    os.chown(_dir, user_uid, -1)

    except:
        print >> sys.stderr, _("Could not change the permissions on %s") % (_dir)

def generate_password():
    import subprocess

    p1 = subprocess.Popen(['head', '-c', '200', '/dev/urandom'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['tr', '-dc', '_A-Z-a-z-0-9'], stdin=p1.stdout, stdout=subprocess.PIPE)
    p3 = subprocess.Popen(['head', '-c', '15'], stdin=p2.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    p2.stdout.close()
    output = p3.communicate()[0]

    return output

def multiline_message(message):
    _msg = ""

    column_width = 80

    # First, replace all occurences of "\n"
    message = message.replace("    ", "")
    message = message.replace("\n", " ")

    lines = []
    line_length = 0

    line = ""
    for word in message.split():
        if (len(line) + len(word)) > column_width:
            lines.append(line)
            line = word
        else:
            if line == "":
                line = word
            else:
                line += " %s" % (word)

    lines.append(line)

    return "\n%s\n" % ("\n".join(lines))

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

    _protocol = uri.split(':')[0]

    try:
        try:
            _ldap_uri, _attr, _scope, _filter = uri.split('?')
            _server = _ldap_uri.split('//')[1].split('/')[0]
            _base_dn = _ldap_uri.split('//')[1].split('/')[1]

        except:
            _server = uri.split('//')[1].split('/')[0]
            _attr = None
            _scope = None
            _filter = None
            _base_dn = None

        if len(_server.split(':')) > 1:
            _port = _server.split(':')[1]
            _server = _server.split(':')[0]
        else:
            if _protocol == 'ldaps':
                _port = "636"
            else:
                _port = "389"

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

        return (_protocol, _server, _port, _base_dn, _attr, _scope, _filter)

    except:
        return None

def pop_empty_from_list(_input_list):
    _output_list = []

    for item in _input_list:
        if not item == '':
            _output_list.append(item)

def standard_root_dn(domain):
    return 'dc=%s' % (',dc='.join(domain.split('.')))

def translate(mystring, locale_name='en_US'):
    import locale
    import subprocess

    log.debug(_("Transliterating string %r with locale %r") % (mystring, locale_name), level=8)

    if len(locale.normalize(locale_name).split('.')) > 1:
        (locale_name,locale_charset) = locale.normalize(locale_name).split('.')
    else:
        locale_charset = 'utf-8'

    try:
        log.debug(_("Attempting to set locale"), level=8)
        locale.setlocale(locale.LC_ALL, (locale_name,locale_charset))
        log.debug(_("Success setting locale"), level=8)
    except:
        log.debug(_("Failure to set locale"), level=8)
        pass

    command = [ '/usr/bin/iconv',
                '-f', 'UTF-8',
                '-t', 'ASCII//TRANSLIT',
                '-s' ]

    log.debug(_("Executing '%s | %s'") % (r"%s" % (mystring), ' '.join(command)), level=8)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, env={'LANG': locale.normalize(locale_name)})

    try:
        print >> process.stdin, r"%s" % mystring
    except UnicodeEncodeError, errmsg:
        pass

    result = process.communicate()[0].strip()

    if '?' in result or (result == '' and not mystring == ''):
        log.warning(_("Could not translate %s using locale %s") % (mystring, locale_name))
        from pykolab import translit
        result = translit.transliterate(mystring, locale_name)

    return result

def true_or_false(val):
    if val == None:
        return False

    if isinstance(val, bool):
        return val

    if isinstance(val, basestring) or isinstance(val, str):
        val = val.lower()
        if val in [ "true", "yes", "y", "1" ]:
            return True
        else:
            return False

    if isinstance(val, int) or isinstance(val, float):
        if val >= 1:
            return True
        else:
            return False

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
