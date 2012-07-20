import pykolab

from pykolab import wap_client

conf = pykolab.getConf()

def user_add(givenname, sn, preferredlanguage='en_US'):
    if givenname == None:
        raise Exception

    if givenname == '':
        raise Exception

    if sn == None:
        raise Exception

    if sn == '':
        raise Exception

    user_details = {
            'givenname': givenname,
            'sn': sn,
            'preferredlanguage': preferredlanguage,
            'ou': 'ou=People,dc=example,dc=org',
            'userpassword': 'Welcome2KolabSystems'
        }

    login = conf.get('ldap', 'bind_dn')
    password = conf.get('ldap', 'bind_pw')
    domain = conf.get('kolab', 'primary_domain')

    user_type_id = 0

    result = wap_client.authenticate(login, password, domain)

    user_types = wap_client.user_types_list()

    for key in user_types['list'].keys():
        if user_types['list'][key]['key'] == 'kolab':
            user_type_id = key

    user_type_info = user_types['list'][user_type_id]['attributes']

    params = {
            'user_type_id': user_type_id,
        }

    for attribute in user_type_info['form_fields'].keys():
        attr_details = user_type_info['form_fields'][attribute]

        if isinstance(attr_details, dict):
            if not attr_details.has_key('optional') or attr_details['optional'] == False:
                params[attribute] = user_details[attribute]
        elif isinstance(attr_details, list):
            params[attribute] = user_details[attribute]

    fvg_params = params
    fvg_params['object_type'] = 'user'
    fvg_params['type_id'] = user_type_id
    fvg_params['attributes'] = [attr for attr in user_type_info['auto_form_fields'].keys() if not attr in params.keys()]

    exec("retval = wap_client.form_value_generate(%r)" % (params))

    for attribute in user_type_info['auto_form_fields'].keys():
        params[attribute] = retval[attribute]

    result = wap_client.user_add(params)

