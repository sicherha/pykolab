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

from __future__ import print_function

import base64
import getpass
import grp
import os
import pwd
from six import string_types
import struct
import sys

import pykolab
from pykolab import constants
from pykolab.translate import _ as _l

# pylint: disable=invalid-name
log = pykolab.getLogger('pykolab.utils')
conf = pykolab.getConf()

try:
    # pylint: disable=redefined-builtin
    input = raw_input
except NameError:
    pass

try:
    unicode('')
except NameError:
    unicode = str


# pylint: disable=too-many-branches
def ask_question(question, default="", password=False, confirm=False):
    """
        Ask a question on stderr.

        Since the answer to the question may actually be a password, cover that
        case with a getpass.getpass() prompt.

        Accepts a default value, but ignores defaults for password prompts.

        Usage: pykolab.utils.ask_question("What is the server?", default="localhost")
    """
    if default != "" and default is not None and conf.cli_keywords.answer_default:
        if not conf.cli_keywords.quiet:
            print("%s [%s]: " % (question, default))
        return default

    if password:
        if default == "" or default is None:
            answer = getpass.getpass("%s: " % (question))
        else:
            answer = getpass.getpass("%s [%s]: " % (question, default))
    else:
        if default == "" or default is None:
            answer = input("%s: " % (question))
        else:
            answer = input("%s [%s]: " % (question, default))

    # pylint: disable=too-many-nested-blocks
    if not answer == "":
        if confirm:
            answer_confirm = None
            answer_confirmed = False
            while not answer_confirmed:
                if password:
                    answer_confirm = getpass.getpass(_l("Confirm %s: ") % (question))
                else:
                    answer_confirm = input(_l("Confirm %s: ") % (question))

                if not answer_confirm == answer:
                    print(_l("Incorrect confirmation. Please try again."), file=sys.stderr)

                    if password:
                        if default == "" or default is None:
                            answer = getpass.getpass(_l("%s: ") % (question))
                        else:
                            answer = getpass.getpass(_l("%s [%s]: ") % (question, default))
                    else:
                        if default == "" or default is None:
                            answer = input(_l("%s: ") % (question))
                        else:
                            answer = input(_l("%s [%s]: ") % (question, default))

                else:
                    answer_confirmed = True

    if answer == "":
        return default

    return answer


# pylint: disable=too-many-return-statements
def ask_confirmation(question, default="y", all_inclusive_no=True):
    """
        Create a confirmation dialog, including a default option (capitalized),
        and a "yes" or "no" parsing that can either require an explicit, full
        "yes" or "no", or take the default or any YyNn answer.
    """
    default_answer = None

    if default in ["y", "Y"]:
        default_answer = True
        default_no = "n"
        default_yes = "Y"
    elif default in ["n", "N"]:
        default_answer = False
        default_no = "N"
        default_yes = "y"
    else:
        # This is a 'yes' or 'no' question the user
        # needs to provide the full yes or no for.
        default_no = "'no'"
        default_yes = "Please type 'yes'"

    if conf.cli_keywords.answer_yes \
            or (conf.cli_keywords.answer_default and default_answer is not None):

        if not conf.cli_keywords.quiet:
            print("%s [%s/%s]: " % (question, default_yes, default_no))
        if conf.cli_keywords.answer_yes:
            return True
        if conf.cli_keywords.answer_default:
            return default_answer

    answer = False
    while not answer:
        answer = input("%s [%s/%s]: " % (question, default_yes, default_no))
        # Parse answer and set back to False if not appropriate
        if all_inclusive_no:
            if answer == "" and default_answer is not None:
                return default_answer

            if answer in ["y", "Y", "yes"]:
                return True

            if answer in ["n", "N", "no"]:
                return False

            answer = False
            print(_l("Please answer 'yes' or 'no'."), file=sys.stderr)

        if answer not in ["y", "Y", "yes"]:
            return False

        return True


# pylint: disable=dangerous-default-value
def ask_menu(question, options={}, default=''):
    if default != '' and conf.cli_keywords.answer_default:
        if not conf.cli_keywords.quiet:
            print(question + " [" + default + "]:")
        return default

    if default != '':
        print(question + " [" + default + "]:")
    else:
        print(question)

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

        if default == '' or default not in options.keys():
            for key in keys:
                if options[key] == key:
                    print(" - " + key)
                else:
                    print(" - " + str_format % key + ": " + options[key])

            answer = input(_l("Choice") + ": ")

        else:
            answer = input(_l("Choice (type '?' for options)") + ": ")

        if answer == '?':
            for key in keys:
                if options[key] == key:
                    print(" - " + key)
                else:
                    print(" - " + str_format % key + ": " + options[key])

            continue

        if answer == '' and default in options.keys():
            answer = default

        if answer in [str(x) for x in options.keys()]:
            answer_correct = True

    return answer


def decode(key, enc):
    if key is None:
        return enc

    dec = []
    enc = base64.urlsafe_b64decode(enc)
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)


def encode(key, clear):
    if key is None:
        return clear

    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))


def ensure_directory(_dir, _user='root', _group='root'):
    if not os.path.isdir(_dir):
        os.makedirs(_dir)

    try:
        try:
            (ruid, _, _) = os.getresuid()
            (rgid, _, _) = os.getresgid()
        except AttributeError:
            ruid = os.getuid()
            rgid = os.getgid()

        if ruid == 0:
            # Means we can setreuid() / setregid() / setgroups()
            if rgid == 0:
                # Get group entry details
                try:
                    (_, _, group_gid, _) = grp.getgrnam(_group)

                except KeyError:
                    print(_l("Group %s does not exist") % (_group), file=sys.stderr)
                    sys.exit(1)

                # Set real and effective group if not the same as current.
                if not group_gid == rgid:
                    os.chown(_dir, -1, group_gid)

            if ruid == 0:
                # Means we haven't switched yet.
                try:
                    (_, _, user_uid, _, _, _, _) = pwd.getpwnam(_user)

                except KeyError:
                    print(_l("User %s does not exist") % (_user), file=sys.stderr)

                    sys.exit(1)

                # Set real and effective user if not the same as current.
                if not user_uid == ruid:
                    os.chown(_dir, user_uid, -1)

    except Exception:
        print(_l("Could not change the permissions on %s") % (_dir), file=sys.stderr)


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
    if hasattr(conf, 'cli_keywords') and hasattr(conf.cli_keywords, 'quiet'):
        if conf.cli_keywords.quiet:
            return ""

    column_width = 80

    # First, replace all occurences of "\n"
    message = message.replace("    ", "")
    message = message.replace("\n", " ")

    lines = []
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


def stripped_message(message):
    return "\n" + message.strip() + "\n"


def str2unicode(s, encoding='utf-8'):
    if isinstance(s, unicode):
        return s
    try:
        return unicode(s, encoding)
    except Exception:
        pass
    return s


def normalize(_object):
    if isinstance(_object, list):
        result = []
    elif isinstance(_object, dict):
        result = {}
    else:
        return _object

    if isinstance(_object, list):
        for item in _object:
            result.append(item.lower())
        result = list(set(result))
        return result

    if isinstance(_object, dict):
        def _strip(value):
            try:
                return value.strip()
            except Exception:
                return value

        for key in _object:
            if isinstance(_object[key], list):
                if _object[key] is None:
                    continue

                # Dont run strip anything from attributes which
                # hold byte strings
                if key.lower() in constants.BINARY_ATTRS:
                    val = _object[key]
                else:
                    val = map(_strip, _object[key])

                if len(val) == 1:
                    result[key.lower()] = ''.join(val)
                else:
                    result[key.lower()] = val

            else:
                if _object[key] is None:
                    continue

                result[key.lower()] = _strip(_object[key])

        if 'objectsid' in result and not result['objectsid'][0] == "S":
            result['objectsid'] = sid_to_string(result['objectsid'])

        if 'sn' in result:
            result['surname'] = result['sn'].replace(' ', '')

        if 'mail' in result:
            if isinstance(result['mail'], list):
                result['mail'] = result['mail'][0]

            if result['mail']:
                if len(result['mail'].split('@')) > 1:
                    result['domain'] = result['mail'].split('@')[1]

        if 'domain' not in result and 'standard_domain' in result:
            result['domain'] = result['standard_domain']

        if 'objectclass' not in result:
            result['objectclass'] = []

        if result['objectclass'] is None:
            result['objectclass'] = []

        if not isinstance(result['objectclass'], list):
            result['objectclass'] = [result['objectclass']]

        result['objectclass'] = [x.lower() for x in result['objectclass']]

        return result


def parse_input(_input, splitchars=[' ']):
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

        except Exception:
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
            _attrs = [_attr]

        if _scope == '':
            _scope = 'sub'

        if _filter == '':
            _filter = "(objectclass=*)"

        return (_protocol, _server, _port, _base_dn, _attrs, _scope, _filter)

    except Exception:
        return None


def pop_empty_from_list(_input_list):
    _output_list = []

    for item in _input_list:
        if not item == '':
            _output_list.append(item)


def sid_to_string(sid):
    srl = ord(sid[0])
    number_sub_id = ord(sid[1])
    iav = struct.unpack('!Q', '\x00\x00' + sid[2:8])[0]

    sub_ids = []

    for i in range(number_sub_id):
        sub_ids.append(struct.unpack('<I', sid[8 + 4 * i:12 + 4 * i])[0])

    result = 'S-%d-%d-%s' % (
        srl,
        iav,
        '-'.join([str(s) for s in sub_ids]),
    )

    return result


def standard_root_dn(domain):
    return 'dc=%s' % (',dc='.join(domain.split('.')))


def translate(mystring, locale_name='en_US'):
    import locale
    import subprocess

    log.debug(_l("Transliterating string %r with locale %r") % (mystring, locale_name), level=8)

    if len(locale.normalize(locale_name).split('.')) > 1:
        (locale_name, locale_charset) = locale.normalize(locale_name).split('.')
    else:
        locale_charset = 'utf-8'

    try:
        log.debug(_l("Attempting to set locale"), level=8)
        locale.setlocale(locale.LC_ALL, (locale_name, locale_charset))
        log.debug(_l("Success setting locale"), level=8)
    except Exception:
        log.debug(_l("Failure to set locale"), level=8)

    command = ['/usr/bin/iconv', '-f', 'UTF-8', '-t', 'ASCII//TRANSLIT', '-s']

    log.debug(_l("Executing '%s | %s'") % (r"%s" % (mystring), ' '.join(command)), level=8)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={'LANG': locale.normalize(locale_name)}
    )

    try:
        print(r"%s" % (mystring), file=process.stdin)
    except UnicodeEncodeError:
        pass

    result = process.communicate()[0].strip()

    if '?' in result or (result == '' and not mystring == ''):
        log.warning(_l("Could not translate %s using locale %s") % (mystring, locale_name))
        from pykolab import translit
        result = translit.transliterate(mystring, locale_name)

    return result


def true_or_false(val):
    if val is None:
        return False

    if isinstance(val, bool):
        return val

    if isinstance(val, string_types):
        val = val.lower()

        if val in ["true", "yes", "y", "1"]:
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

    return (_service, _other_services)
