import pykolab

from pykolab import wap_client

conf = pykolab.getConf()

def resource_add(type, cn, members=None, owner=None, **kw):
    if type == None or type == '':
        raise Exception

    if cn == None or cn == '':
        raise Exception

    resource_details = {
        'cn': cn,
        'kolabtargetfolder': "shared/Resources/" + cn + "@example.org",
        'uniquemember': members,
        'owner': owner
    }

    resource_details.update(kw)

    result = wap_client.authenticate(conf.get('ldap', 'bind_dn'), conf.get('ldap', 'bind_pw'), conf.get('kolab', 'primary_domain'))

    type_id = 0
    resource_types = wap_client.resource_types_list()

    for key in resource_types['list'].keys():
        if resource_types['list'][key]['key'] == type:
            type_id = key

    if type_id == 0:
        raise Exception

    resource_type_info = resource_types['list'][type_id]['attributes']

    params = {}

    for attribute in resource_type_info['form_fields'].keys():
        attr_details = resource_type_info['form_fields'][attribute]

        if isinstance(attr_details, dict):
            if not attr_details.has_key('optional') or attr_details['optional'] == False or resource_details.has_key(attribute):
                params[attribute] = resource_details[attribute]
        elif isinstance(attr_details, list):
            params[attribute] = resource_details[attribute]

    fvg_params = params
    fvg_params['object_type'] = 'resource'
    fvg_params['type_id'] = type_id
    fvg_params['attributes'] = [attr for attr in resource_type_info['auto_form_fields'].keys() if not attr in params.keys()]

    result = wap_client.resource_add(params)
    result['dn'] = "cn=" + result['cn'] + ",ou=Resources,dc=example,dc=org"
    return result


def purge_resources():
    wap_client.authenticate(conf.get("ldap", "bind_dn"), conf.get("ldap", "bind_pw"), conf.get('kolab', 'primary_domain'))

    resources = wap_client.resources_list()

    for resource in resources['list']:
        wap_client.resource_delete({'id': resource})

    #from tests.functional.purge_imap import purge_imap
    #purge_imap()

