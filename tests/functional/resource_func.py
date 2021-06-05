import pykolab

from pykolab import wap_client

conf = pykolab.getConf()


def resource_add(type, cn, members=None, owner=None, **kw):
    if type is None or type == '':
        raise Exception

    if cn is None or cn == '':
        raise Exception

    resource_details = {
        'cn': cn,
        'kolabtargetfolder': "shared/Resources/" + cn + "@example.org",
        'uniquemember': members,
        'owner': owner,
        'ou': 'ou=resources,dc=example,dc=org'
    }

    resource_details.update(kw)

    bind_dn = conf.get('ldap', 'bind_dn')
    bind_pw = conf.get('ldap', 'bind_pw')
    domain = conf.get('kolab', 'primary_domain')
    result = wap_client.authenticate(bind_dn, bind_pw, domain)

    type_id = 0
    resource_types = wap_client.resource_types_list()

    for key in resource_types['list']:
        if resource_types['list'][key]['key'] == type:
            type_id = key

    if type_id == 0:
        raise Exception

    resource_type_info = resource_types['list'][type_id]['attributes']

    params = {}

    for attribute in resource_type_info['form_fields']:
        attr_details = resource_type_info['form_fields'][attribute]

        if isinstance(attr_details, dict):
            if 'optional' not in attr_details or attr_details['optional'] is False or attribute in resource_details:
                params[attribute] = resource_details[attribute]
        elif isinstance(attr_details, list):
            params[attribute] = resource_details[attribute]

    fvg_params = params
    fvg_params['object_type'] = 'resource'
    fvg_params['type_id'] = type_id
    fvg_params['attributes'] = [attr for attr in resource_type_info['auto_form_fields'] if attr not in params]

    result = wap_client.resource_add(params)
    result['dn'] = "cn=" + result['cn'] + ",ou=Resources,dc=example,dc=org"
    return result


def purge_resources():
    bind_dn = conf.get('ldap', 'bind_dn')
    bind_pw = conf.get('ldap', 'bind_pw')
    domain = conf.get('kolab', 'primary_domain')
    result = wap_client.authenticate(bind_dn, bind_pw, domain)

    resources = wap_client.resources_list()

    for resource in resources['list']:
        wap_client.resource_delete({'id': resource})

    # from tests.functional.purge_imap import purge_imap
    # purge_imap()
