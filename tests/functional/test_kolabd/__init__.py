import pykolab


def setup_package():
    conf = pykolab.getConf()
    conf.finalize_conf(fatal=False)

