import pykolab

from pykolab import wap_client

conf = pykolab.getConf()


def user_add(givenname, sn, preferredlanguage='en_US', **kw):
    if givenname is None or givenname == '':
        raise Exception

    if sn is None or sn == '':
        raise Exception

    user_details = {
            'givenname': givenname,
            'sn': sn,
            'preferredlanguage': preferredlanguage,
            'ou': 'ou=People,dc=example,dc=org',
            'userpassword': 'Welcome2KolabSystems'
        }

    user_details.update(kw)

    login = conf.get('ldap', 'bind_dn')
    password = conf.get('ldap', 'bind_pw')
    domain = conf.get('kolab', 'primary_domain')

    user_type_id = 0

    result = wap_client.authenticate(login, password, domain)

    user_types = wap_client.user_types_list()

    for key in user_types['list']:
        if user_types['list'][key]['key'] == 'kolab':
            user_type_id = key

    user_type_info = user_types['list'][user_type_id]['attributes']

    params = {
            'user_type_id': user_type_id,
        }

    for attribute in user_type_info['form_fields']:
        attr_details = user_type_info['form_fields'][attribute]

        if isinstance(attr_details, dict):
            if 'optional' not in attr_details or attr_details['optional'] is False or attribute in user_details:
                params[attribute] = user_details[attribute]
        elif isinstance(attr_details, list):
            params[attribute] = user_details[attribute]

    fvg_params = params
    fvg_params['object_type'] = 'user'
    fvg_params['type_id'] = user_type_id
    fvg_params['attributes'] = [attr for attr in user_type_info['auto_form_fields'] if attr not in params]

    result = wap_client.user_add(params)
