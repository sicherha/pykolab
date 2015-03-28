import kolabformat
import datetime
import pytz
import base64

from pykolab.xml import utils as xmlutils
from pykolab.xml.utils import ustr

def contact_from_vcard(string):
    # TODO: implement this
    pass

def contact_from_string(string):
    _xml = kolabformat.readContact(string, False)
    return Contact(_xml)

def contact_from_message(message):
    contact = None
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "application/vcard+xml":
                payload = part.get_payload(decode=True)
                contact = contact_from_string(payload)

            # append attachment parts to Contact object
            elif contact and part.has_key('Content-ID'):
                contact._attachment_parts.append(part)

    return contact


class Contact(kolabformat.Contact):
    type = 'contact'

    related_map = {
        'manager': kolabformat.Related.Manager,
        'assistant': kolabformat.Related.Assistant,
        'spouse': kolabformat.Related.Spouse,
        'children': kolabformat.Related.Child,
        None: kolabformat.Related.NoRelation,
    }

    addresstype_map = {
        'home': kolabformat.Address.Home,
        'work': kolabformat.Address.Work,
    }

    phonetype_map = {
        'home':    kolabformat.Telephone.Home,
        'work':    kolabformat.Telephone.Work,
        'text':    kolabformat.Telephone.Text,
        'main':    kolabformat.Telephone.Voice,
        'homefax': kolabformat.Telephone.Fax,
        'workfax': kolabformat.Telephone.Fax,
        'mobile':  kolabformat.Telephone.Cell,
        'video':   kolabformat.Telephone.Video,
        'pager':   kolabformat.Telephone.Pager,
        'car':     kolabformat.Telephone.Car,
        'other':   kolabformat.Telephone.Textphone,
    }

    emailtype_map = {
        'home': kolabformat.Email.Home,
        'work': kolabformat.Email.Work,
        'other': kolabformat.Email.Work,
    }

    urltype_map = {
        'homepage': kolabformat.Url.NoType,
        'blog': kolabformat.Url.Blog,
    }

    keytype_map = {
        'pgp': kolabformat.Key.PGP,
        'pkcs7': kolabformat.Key.PKCS7_MIME,
        None: kolabformat.Key.Invalid,
    }

    gender_map = {
        'female': kolabformat.Contact.Female,
        'male': kolabformat.Contact.Male,
        None: kolabformat.Contact.NotSet,
    }

    properties_map = {
        'uid':               'get_uid',
        'lastmodified-date': 'get_lastmodified',
        'fn':                'name',
        'nickname':          'nickNames',
        'title':             'titles',
        'email':             'emailAddresses',
        'tel':               'telephones',
        'url':               'urls',
        'im':                'imAddresses',
        'address':           'addresses',
        'note':              'note',
        'freebusyurl':       'freeBusyUrl',
        'birthday':          'bDay',
        'anniversary':       'anniversary',
        'categories':        'categories',
        'lang':              'languages',
        'gender':            'get_gender',
        'gpspos':            'gpsPos',
        'key':               'keys',
    }

    def __init__(self, *args, **kw):
        self._attachment_parts = []
        kolabformat.Contact.__init__(self, *args, **kw)

    def get_uid(self):
        uid = self.uid()
        if not uid == '':
            return uid
        else:
            self.__str__()
            return kolabformat.getSerializedUID()

    def get_lastmodified(self):
        try:
            _datetime = self.lastModified()
            if _datetime == None or not _datetime.isValid():
                self.__str__()
        except:
            return datetime.datetime.now(pytz.utc)

        return xmlutils.from_cdatetime(self.lastModified(), True)

    def get_email(self, preferred=True):
        if preferred:
            return self.emailAddresses()[self.emailAddressPreferredIndex()]
        else:
            return [x for x in self.emailAddresses()]

    def set_email(self, email, preferred_index=0):
        if isinstance(email, basestring):
            self.setEmailAddresses([email], preferred_index)
        else:
            self.setEmailAddresses(email, preferred_index)

    def add_email(self, email):
        if isinstance(email, basestring):
            self.add_emails([email])
        elif isinstance(email, list):
            self.add_emails(email)

    def add_emails(self, emails):
        preferred_email = self.get_email()
        emails = [x for x in set(self.get_email(preferred=False) + emails)]
        preferred_email_index = emails.index(preferred_email)
        self.setEmailAddresses(emails, preferred_email_index)

    def set_name(self, name):
        self.setName(ustr(name))

    def get_gender(self, translated=True):
        _gender = self.gender()
        if translated:
            return self._translate_value(_gender, self.gender_map)
        return _gender

    def _translate_value(self, val, map):
        name_map = dict([(v, k) for (k, v) in map.iteritems()])
        return name_map[val] if name_map.has_key(val) else 'UNKNOWN'

    def to_dict(self):
        if not self.isValid():
            return None

        data = self._names2dict(self.nameComponents())

        for p, getter in self.properties_map.iteritems():
            val = None
            if hasattr(self, getter):
                val = getattr(self, getter)()
            if isinstance(val, kolabformat.cDateTime):
                val = xmlutils.from_cdatetime(val, True)
            elif isinstance(val, kolabformat.vectori):
                val = [int(x) for x in val]
            elif isinstance(val, kolabformat.vectors):
                val = [str(x) for x in val]
            elif isinstance(val, kolabformat.vectortelephone):
                val = [self._struct2dict(x, 'number', self.phonetype_map) for x in val]
            elif isinstance(val, kolabformat.vectoremail):
                val = [self._struct2dict(x, 'address', self.emailtype_map) for x in val]
            elif isinstance(val, kolabformat.vectorurl):
                val = [self._struct2dict(x, 'url', self.urltype_map) for x in val]
            elif isinstance(val, kolabformat.vectorkey):
                val = [self._struct2dict(x, 'key', self.keytype_map) for x in val]
            elif isinstance(val, kolabformat.vectoraddress):
                val = [self._address2dict(x) for x in val]
            elif isinstance(val, kolabformat.vectorgeo):
                val = [[x.latitude, x.longitude] for x in val]

            if val is not None:
                data[p] = val

        affiliations = self.affiliations()
        if len(affiliations) > 0:
            _affiliation = self._affiliation2dict(affiliations[0])
            if _affiliation.has_key('address'):
                data['address'].extend(_affiliation['address'])
                _affiliation.pop('address', None)
            data.update(_affiliation)

        data.update(self._relateds2dict(self.relateds()))

        if self.photoMimetype():
            data['photo'] = dict(mimetype=self.photoMimetype(), base64=base64.b64encode(self.photo()))
        elif self.photo():
            data['photo'] = dict(uri=self.photo())

        return data

    def _names2dict(self, namecomp):
        names_map = {
            'surname':    'surnames',
            'given':      'given',
            'additional': 'additional',
            'prefix':     'prefixes',
            'suffix':     'suffixes',
        }

        data = dict()

        for p, getter in names_map.iteritems():
            val = None
            if hasattr(namecomp, getter):
                val = getattr(namecomp, getter)()
            if isinstance(val, kolabformat.vectors):
                val = [str(x) for x in val][0] if len(val) > 0 else None
            if val is not None:
                data[p] = val

        return data

    def _affiliation2dict(self, affiliation):
        props_map = {
            'organization': 'organisation',
            'department':   'organisationalUnits',
            'role':         'roles',
        }

        data = dict()

        for p, getter in props_map.iteritems():
            val = None
            if hasattr(affiliation, getter):
                val = getattr(affiliation, getter)()
            if isinstance(val, kolabformat.vectors):
                val = [str(x) for x in val][0] if len(val) > 0 else None
            if val is not None:
                data[p] = val

        data.update(self._relateds2dict(affiliation.relateds(), True))

        addresses = affiliation.addresses()
        if len(addresses):
            data['address'] = [self._address2dict(adr, 'office') for adr in addresses]

        return data

    def _address2dict(self, adr, adrtype=None):
        props_map = {
            'label':    'label',
            'street':   'street',
            'locality': 'locality',
            'region':   'region',
            'code':     'code',
            'country':  'country',
        }
        addresstype_map = dict([(v, k) for (k, v) in self.addresstype_map.iteritems()])

        data = dict()

        if adrtype is None:
            adrtype = addresstype_map.get(adr.types(), None)

        if adrtype is not None:
            data['type'] = adrtype

        for p, getter in props_map.iteritems():
            val = None
            if hasattr(adr, getter):
                val = getattr(adr, getter)()
            if isinstance(val, kolabformat.vectors):
                val = [str(x) for x in val][0] if len(val) > 0 else None
            if val is not None:
                data[p] = val

        return data

    def _relateds2dict(self, relateds, aslist=True):
        data = dict()

        related_map = dict([(v, k) for (k, v) in self.related_map.iteritems()])
        for rel in relateds:
            reltype = related_map.get(rel.relationTypes(), None)
            val = rel.uri() if rel.type() == kolabformat.Related.Uid else rel.text()
            if reltype and val is not None:
                if aslist:
                    if not data.has_key(reltype):
                        data[reltype] = []
                    data[reltype].append(val)
                else:
                    data[reltype] = val

        return data

    def _struct2dict(self, struct, propname, map):
        type_map = dict([(v, k) for (k, v) in map.iteritems()])
        result = dict()

        if hasattr(struct, 'types'):
            result['type'] = type_map.get(struct.types(), None)
        elif hasattr(struct, 'type'):
            result['type'] = type_map.get(struct.type(), None)

        if hasattr(struct, propname):
            result[propname] = getattr(struct, propname)()

        return result

    def __str__(self):
        xml = kolabformat.writeContact(self)
        error = kolabformat.error()

        if error == None or not error:
            return xml
        else:
            raise ContactIntegrityError, kolabformat.errorMessage()


class ContactIntegrityError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
