
import json
import httplib
import sys

sys.path.append('../..')

from pykolab import utils

API_HOSTNAME = "admin.klab.cc"
API_PORT = "80"
API_SCHEME = "http"
API_BASE = "/~vanmeeuwen/kolab-wap/public_html/api"

session_id = None

conn = None

def authenticate(username=None, password=None):
    global session_id

    if username == None:
        username = utils.ask_question("Login", "cn=Directory Manager")

    if password == None:
        password = utils.ask_question("Password", "5auTYwxBK1uGTpy", password=True)

    params = json.dumps(
            {
                    'username': username,
                    'password': password
                }
        )

    response = request('POST', "system.authenticate", params)

    if response.has_key('session_token'):
        session_id = response['session_token']

def connect():
    global conn

    if conn == None:
        conn = httplib.HTTPConnection(API_HOSTNAME, API_PORT)
        conn.connect()

    return conn

def domains_capabilities():
    return request('GET', 'domains.capabilities')

def domains_list():
    return request('GET', 'domains.list')

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

    if len(user_types.keys()) > 1:
        for key in user_types.keys():
            if not key == "status":
                print "%s) %s" % (key,user_types[key]['name'])

        user_type_id = utils.ask_question("Please select the user type")

    elif len(user_types.keys()) > 0:
        print "Automatically selected the only user type available"
        user_type_id = user_types.keys()[0]

    else:
        print "No user types available"
        sys.exit(1)

    if user_types.has_key(user_type_id):
        user_type_info = user_types[user_type_id]['attributes']
    else:
        print "No such user type"
        sys.exit(1)

    params = {
            'user_type_id': user_type_id
        }

    for attribute in user_type_info['form_fields'].keys():
        params[attribute] = utils.ask_question(attribute)

    for attribute in user_type_info['auto_form_fields'].keys():
        exec("retval = form_value_generate_%s(params)" % (attribute))
        params[attribute] = retval[attribute]

    return params

def group_add(params=None):
    if params == None:
        params = get_group_input()

    params = json.dumps(params)

    return request('POST', 'group.add', params)

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

def request(method, api_uri, params=None, headers={}):
    global session_id

    if not session_id == None:
        headers["X-Session-Token"] = session_id

    conn = connect()
    conn.request(method.upper(), "%s/%s" % (API_BASE,api_uri), params, headers)
    response = conn.getresponse()
    data = response.read()

    #print method, api_uri, params
    #print data

    try:
        response_data = json.loads(data)
    except ValueError, e:
        # Some data is not JSON
        print "Response data is not JSON"
        sys.exit(1)

    #print response_data

    if response_data['status'] == "OK":
        del response_data['status']
        return response_data['result']
    else:
        return response_data['result']

def system_capabilities():
    return request('GET', 'system.capabilities')

def system_get_domain():
    return request('GET', 'system.get_domain')

def system_select_domain(domain=None):
    if domain == None:
        domain = utils.ask_question("Domain name")
    return request('GET', 'system.select_domain?domain=%s' % (domain))

def user_add(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'user.add', params)

def user_delete(params=None):
    if params == None:
        params = {
                'user': utils.ask_question("Username for user to delete", "user")
            }

    params = json.dumps(params)

    return request('POST', 'user.delete', params)

def user_edit(params=None):
    if params == None:
        params = {
                'user': utils.ask_question("Username for user to edit", "user")
            }

    params = json.dumps(params)

    user = request('GET', 'user.info', params)

    return user

def user_form_value_generate_cn(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'user_form_value.generate_cn', params)

def user_form_value_generate_displayname(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'user_form_value.generate_displayname', params)

def user_form_value_generate_mail(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'user_form_value.generate_mail', params)

def user_form_value_generate_password(*args, **kw):
    return request('GET', 'user_form_value.generate_password')

def user_form_value_generate_uid(params=None):
    if params == None:
        params = get_user_input()

    params = json.dumps(params)

    return request('POST', 'user_form_value.generate_uid', params)

def user_form_value_generate_userpassword(*args, **kw):
    result = user_form_value_generate_password()
    return { 'userpassword': result['password'] }

def user_info():
    user = utils.ask_question("User email address")
    user = request('GET', 'user.info?user=%s' % (user))
    return user

def user_types_list():
    return request('GET', 'user_types.list')

def users_list():
    return request('GET', 'users.list')

