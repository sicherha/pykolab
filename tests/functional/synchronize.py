from pykolab.auth import Auth


def synchronize_once():
    auth = Auth()
    auth.connect()
    auth.synchronize(mode='_paged_search')
