
import json
import httplib
import urllib
import sys
from urlparse import urlparse

import pykolab

from pykolab import utils
from pykolab.translate import _

log = pykolab.getLogger('pykolab.wap_client')
conf = pykolab.getConf()

if not hasattr(conf, 'defaults'):
    conf.finalize_conf()

API_HOSTNAME = "localhost"
API_SCHEME = "http"
API_PORT = 80
API_BASE = "/kolab-webadmin/api/"

kolab_wap_url = conf.get('kolab_wap', 'api_url')

if not kolab_wap_url == None:
    result = urlparse(kolab_wap_url)
else:
    result = None

if hasattr(result, 'hostname'):
    API_HOSTNAME = result.hostname

if hasattr(result, 'port'):
    API_PORT = result.port

if hasattr(result, 'path'):
    API_BASE = result.path

session_id = None

conn = None

from connect import connect

def authenticate(username=None, password=None, domain=None):
    global session_id

    if username == None:
        username = conf.get('ldap', 'bind_dn')
    if password == None:
        password = conf.get('ldap', 'bind_pw')

    if domain == None:
        domain = conf.get('kolab', 'primary_domain')

    post = json.dumps(
            {
                    'username': username,
                    'password': password,
                    'domain': domain
                }
        )

    response = request('POST', "system.authenticate", post=post)

    if response.has_key('session_token'):
        session_id = response['session_token']

def connect():
    global conn

    if conn == None:
        conn = httplib.HTTPConnection(API_HOSTNAME, API_PORT)
        conn.connect()

    return conn

def domain_add(domain, aliases=[]):
    dna = conf.get('ldap', 'domain_name_attribute')

    post = json.dumps({
            dna: [ domain ] + aliases
        })

    return request('POST', 'domain.add', post=post)

def domain_delete(domain):
    domain_id, domain_attrs = domain_find(domain).popitem()

    post = json.dumps({
            'id': domain_id
        })

    return request('POST', 'domain.delete', post=post)

def domain_find(domain):
    dna = conf.get('ldap', 'domain_name_attribute')

    get = { dna: domain }

    return request('GET', 'domain.find', get=get)

def domain_info(domain):
    domain_id, domain_attrs = domain_find(domain)

    get = { 'id': domain_id }

    return request('GET', 'domain.info', get=get)

def domains_capabilities():
    return request('GET', 'domains.capabilities')

def domains_list():
    return request('GET', 'domains.list')

def form_value_generate(params):
    post = json.dumps(params)

    return request('POST', 'form_value.generate', post=post)

def get_group_input():
    group_types = group_types_list()

    if len(group_types.keys()) > 1:
        for key in group_types.keys():
            if not key == "status":
                print "%s) %s" % (key,group_types[key]['name'])

        group_type_id = utils.ask_question("Please select the group type")

    elif len(group_types.keys()) > 0:
        print "Automatically selected the only group type available"
        group_type_id = group_types.keys()[0]

    else:
        print "No group types available"
        sys.exit(1)

    if group_types.has_key(group_type_id):
        group_type_info = group_types[group_type_id]['attributes']
    else:
        print "No such group type"
        sys.exit(1)

    params = {
            'group_type_id': group_type_id
        }

    for attribute in group_type_info['form_fields'].keys():
        params[attribute] = utils.ask_question(attribute)

    for attribute in group_type_info['auto_form_fields'].keys():
        exec("retval = group_form_value_generate_%s(params)" % (attribute))
        params[attribute] = retval[attribute]

    return params

def get_user_input():
    user_types = user_types_list()

    if user_types['count'] > 1:
        print ""
        for key in user_types['list'].keys():
            if not key == "status":
                print "%s) %s" % (key,user_types['list'][key]['name'])

        print ""
        user_type_id = utils.ask_question("Please select the user type")

    elif user_types['count'] > 0:
        print "Automatically selected the only user type available"
        user_type_id = user_types['list'].keys()[0]

    else:
        print "No user types available"
        sys.exit(1)

    if user_types['list'].has_key(user_type_id):
        user_type_info = user_types['list'][user_type_id]['attributes']
    else:
        print "No such user type"
        sys.exit(1)

    params = {
            'object_type': 'user',
            'type_id': user_type_id
        }

    must_attrs = []
    may_attrs = []

    for attribute in user_type_info['form_fields'].keys():
        if isinstance(user_type_info['form_fields'][attribute], dict):
            if user_type_info['form_fields'][attribute].has_key('optional') and user_type_info['form_fields'][attribute]['optional']:
                may_attrs.append(attribute)
            else:
                must_attrs.append(attribute)
        else:
            must_attrs.append(attribute)

    for attribute in must_attrs:
        if isinstance(user_type_info['form_fields'][attribute], dict) and \
                user_type_info['form_fields'][attribute].has_key('type'):

            if user_type_info['form_fields'][attribute]['type'] == 'select':
                if not user_type_info['form_fields'][attribute].has_key('values'):
                    attribute_values = form_value_select_options('user', user_type_id, attribute)

                    default = ''
                    if attribute_values[attribute].has_key('default'):
                        default = attribute_values[attribute]['default']

                    params[attribute] = utils.ask_menu(
                            "Choose the %s value" % (attribute),
                            attribute_values[attribute]['list'],
                            default=default
                        )

                else:
                    default = ''
                    if user_type_info['form_fields'][attribute].has_key('default'):
                        default = user_type_info['form_fields'][attribute]['default']

                    params[attribute] = utils.ask_menu(
                            "Choose the %s value" % (attribute),
                            user_type_info['form_fields'][attribute]['values'],
                            default=default
                        )

            else:
                params[attribute] = utils.ask_question(attribute)

        else:
            params[attribute] = utils.ask_question(attribute)

    for attribute in user_type_info['fields'].keys():
        params[attribute] = user_type_info['fields'][attribute]

    exec("retval = user_form_value_generate(params)")
    print retval

    return params

def group_add(params=None):
    if params == None:
        params = get_group_input()

    post = json.dumps(params)

    return request('POST', 'group.add', post=post)

def group_delete(params=None):
    if params == None:
        params = {
                'id': utils.ask_question("Name of group to delete", "group")
            }

    post = json.dumps(params)

    return request('POST', 'group.delete', post=post)

def group_form_value_generate_mail(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'group_form_value.generate_mail', params)

def group_info():
    group = utils.ask_question("Group email address")
    group = request('GET', 'group.info?group=%s' % (group))
    return group

def group_members_list(group=None):
    if group == None:
        group = utils.ask_question("Group email address")
    group = request('GET', 'group.members_list?group=%s' % (group))
    return group

def group_types_list():
    return request('GET', 'group_types.list')

def groups_list():
    return request('GET', 'groups.list')

def request(method, api_uri, get=None, post=None, headers={}):
    response_data = request_raw(method, api_uri, get, post, headers)

    if response_data['status'] == "OK":
        del response_data['status']
        return response_data['result']
    else:
        return response_data['result']

def request_raw(method, api_uri, get=None, post=None, headers={}):
    global session_id

    if not session_id == None:
        headers["X-Session-Token"] = session_id

    conn = connect()

    if conf.debuglevel > 8:
        conn.set_debuglevel(9)

    if not get == None:
        _get = "?%s" % (urllib.urlencode(get))
    else:
        _get = ""

    log.debug(_("Requesting %r with params %r") % ("%s/%s" % (API_BASE,api_uri), (get, post)), level=8)

    conn.request(method.upper(), "%s/%s%s" % (API_BASE, api_uri, _get), post, headers)

    response = conn.getresponse()

    data = response.read()

    log.debug(_("Got response: %r") % (data), level=8)
    try:
        response_data = json.loads(data)
    except ValueError, e:
        # Some data is not JSON
        log.error(_("Response data is not JSON"))

    return response_data

def role_capabilities():
    return request('GET', 'role.capabilities')

def system_capabilities():
    return request('GET', 'system.capabilities')

def system_get_domain():
    return request('GET', 'system.get_domain')

def system_select_domain(domain=None):
    if domain == None:
        domain = utils.ask_question("Domain name")

    get = { 'domain': domain }

    return request('GET', 'system.select_domain', get=get)

def user_add(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'user.add', post=params)

def user_delete(params=None):
    if params == None:
        params = {
                'user': utils.ask_question("Username for user to delete", "user")
            }

    post = json.dumps(params)

    return request('POST', 'user.delete', post=post)

def user_edit(user = None, attributes={}):
    if user == None:
        get = {
                'user': utils.ask_question("Username for user to edit", "user")
            }
    else:
        get = {
                'user': user
            }

    user_info = request('GET', 'user.info', get=get)

    for attribute in attributes.keys():
        user_info[attribute] = attributes[attribute]

    post = json.dumps(user_info)

    user_edit = request('POST', 'user.edit', get=get, post=post)

    return user_edit

def user_form_value_generate(params=None):
    if params == None:
        params = get_user_input()

    post = json.dumps(params)

    return request('POST', 'form_value.generate', post=post)

def form_value_generate_password(*args, **kw):
    return request('GET', 'form_value.generate_password')

def form_value_list_options(object_type, object_type_id, attribute):
    post = json.dumps(
            {
                    'object_type': object_type,
                    'type_id': object_type_id,
                    'attribute': attribute
                }
        )

    return request('POST', 'form_value.list_options', post=post)

def form_value_select_options(object_type, object_type_id, attribute):
    post = json.dumps(
            {
                    'object_type': object_type,
                    'type_id': object_type_id,
                    'attributes': [ attribute ]
                }
        )

    return request('POST', 'form_value.select_options', post=post)

def role_find_by_attribute(params=None):
    if params == None:
        role_name = utils.ask_question("Role name")
    else:
        role_name = params['cn']

    get = { 'cn': role_name }
    role = request('GET', 'role.find_by_attribute', get=get)

    return role

def role_add(params=None):
    if params == None:
        role_name = utils.ask_question("Role name")
        params = {
                'cn': role_name
            }

    params = json.dumps(params)

    return request('POST', 'role.add', params)

def role_delete(params=None):
    if params == None:
        role_name = utils.ask_question("Role name")
        role = role_find_by_attribute({'cn': role_name})
        params = {
                'role': role.keys()[0]
            }

    if not params.has_key('role'):
        role = role_find_by_attribute(params)
        params = {
                'role': role.keys()[0]
            }

    post = json.dumps(params)

    return request('POST', 'role.delete', post=post)

def role_info(role_name):
    role = role_find_by_attribute({'cn': role_name})

    get = { 'role': role['id'] }

    role = request('GET', 'role.info', get=get)

    return role

def roles_list():
    return request('GET', 'roles.list')

def user_form_value_generate_uid(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'form_value.generate_uid', params)

def user_form_value_generate_userpassword(*args, **kw):
    result = form_value_generate_password()
    return { 'userpassword': result['password'] }

def user_info(user=None):
    if user == None:
        user = utils.ask_question("User email address")
    _params = { 'user': user }
    user = request('GET', 'user.info', get=_params)
    return user

def user_types_list():
    return request('GET', 'user_types.list')

def users_list():
    return request('GET', 'users.list')

