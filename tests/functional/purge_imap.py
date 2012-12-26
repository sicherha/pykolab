import time

import pykolab

from pykolab import wap_client
from pykolab.imap import IMAP

conf = pykolab.getConf()

def purge_imap():
    time.sleep(2)

    imap = IMAP()
    imap.connect()

    for folder in imap.lm():
        try:
            imap.dm(folder)
        except:
            pass
