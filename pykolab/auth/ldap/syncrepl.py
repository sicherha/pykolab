#!/usr/bin/python

import anydbm
import ldap
import ldap.syncrepl
import ldapurl

import pykolab

from pykolab import utils

log = pykolab.getLogger('pykolab.syncrepl')
conf = pykolab.getConf()

class DNSync(ldap.ldapobject.LDAPObject,ldap.syncrepl.SyncreplConsumer):

    callback = None

    def __init__(self, filename, *args, **kwargs):
        if kwargs.has_key('callback'):
            self.callback = kwargs['callback']
            del kwargs['callback']

        ldap.ldapobject.LDAPObject.__init__(self, *args, **kwargs)
        self.__db = anydbm.open(filename, 'c', 0640)
        self.__presentUUIDs = {}

    def syncrepl_set_cookie(self,cookie):
        self.__db['cookie'] = cookie

    def syncrepl_get_cookie(self):
        if 'cookie' in self.__db:
            return self.__db['cookie']

    def syncrepl_delete(self, uuids):
        log.debug("syncrepl_delete uuids: %r" % (uuids), level=8)

        # Get the unique_attribute name to issue along with our
        # callback (if any)
        unique_attr = conf.get('ldap', 'unique_attribute')
        if unique_attr == None:
            unique_attr = 'entryuuid'

        if unique_attr == 'nsuniqueid':
            log.warning(
                    _("The name of the persistent, unique attribute " + \
                    "is very probably not compatible with the use of " + \
                    "syncrepl.")
                )
            

        for uuid in uuids:
            dn = self.__db[uuid]

            log.debug("syncrepl_delete dn: %r" % (dn), level=8)

            if not self.callback == None:
                self.callback(
                        change_type='delete',
                        previous_dn=None,
                        change_number=None,
                        dn=dn,
                        entry={
                                unique_attr: uuid
                            }
                    )

            del self.__db[uuid]

    def syncrepl_present(self, uuids, refreshDeletes=False):
        if uuids is None:
            if refreshDeletes is False:
                nonpresent = []
                for uuid in self.__db.keys():
                    if uuid == 'cookie': continue
                    if uuid in self.__presentUUIDs: continue
                    nonpresent.append(uuid)
                self.syncrepl_delete(nonpresent)
            self.__presentUUIDs = {}
        else:
            for uuid in uuids:
                self.__presentUUIDs[uuid] = True

    def syncrepl_entry(self, dn, attrs, uuid):
        attrs = utils.normalize(attrs)

        if uuid in self.__db:
            odn = self.__db[uuid]
            if odn != dn:
                if not self.callback == None:
                    self.callback(
                            change_type='moddn',
                            previous_dn=odn,
                            change_number=None,
                            dn=dn,
                            entry=attrs
                        )

            else:
                if not self.callback == None:
                    self.callback(
                            change_type='modify',
                            previous_dn=None,
                            change_number=None,
                            dn=self.__db[uuid],
                            entry=attrs
                        )

        else:
            if not self.callback == None:
                self.callback(
                        change_type='add',
                        previous_dn=None,
                        change_number=None,
                        dn=dn,
                        entry=attrs
                    )

        self.__db[uuid] = dn
