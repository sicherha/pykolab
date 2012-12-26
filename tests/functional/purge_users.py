import pykolab

from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP

conf = pykolab.getConf()

def purge_users():
    wap_client.authenticate(conf.get("ldap", "bind_dn"), conf.get("ldap", "bind_pw"))

    users = wap_client.users_list()
    for user in users['list']:
        wap_client.user_delete({'user': user})

    from tests.functional.purge_imap import purge_imap
    purge_imap()
