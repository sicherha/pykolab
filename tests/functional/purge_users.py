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

    auth = Auth()
    domains = auth.list_domains()

    imap = IMAP()
    imap.connect()

    folders = []

    for domain,aliases in domains:
        folders.extend(imap.lm("user/%%@%s" % (domain)))

    for folder in folders:
        user = folder.replace('user/','')

        recipient = auth.find_recipient(user)

        if len(recipient) == 0 or recipient == []:
            try:
                imap.dm(folder)
            except:
                pass

