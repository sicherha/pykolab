import pytz
import datetime
import kolabformat

from pykolab.translate import _
from pykolab.xml import utils as xmlutils
from pykolab.xml.utils import ustr

def note_from_string(string):
    _xml = kolabformat.readNote(string, False)
    return Note(_xml)

def note_from_message(message):
    note = None
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "application/vnd.kolab+xml":
                payload = part.get_payload(decode=True)
                note = note_from_string(payload)

            # append attachment parts to Note object
            elif note and part.has_key('Content-ID'):
                note._attachment_parts.append(part)

    return note


class Note(kolabformat.Note):
    type = 'note'

    classification_map = {
        'PUBLIC': kolabformat.ClassPublic,
        'PRIVATE': kolabformat.ClassPrivate,
        'CONFIDENTIAL': kolabformat.ClassConfidential,
    }

    properties_map = {
        'uid':               'get_uid',
        'summary':           'summary',
        'description':       'description',
        'created':           'get_created',
        'lastmodified-date': 'get_lastmodified',
        'classification':    'get_classification',
        'categories':        'categories',
        'color':             'color',
    }

    def __init__(self, *args, **kw):
        self._attachment_parts = []
        kolabformat.Note.__init__(self, *args, **kw)

    def get_uid(self):
        uid = self.uid()
        if not uid == '':
            return uid
        else:
            self.__str__()
            return kolabformat.getSerializedUID()

    def get_created(self):
        try:
            return xmlutils.from_cdatetime(self.created(), True)
        except ValueError:
            return datetime.datetime.now()

    def get_lastmodified(self):
        try:
            _datetime = self.lastModified()
            if _datetime == None or not _datetime.isValid():
                self.__str__()
        except:
            return datetime.datetime.now(pytz.utc)

        return xmlutils.from_cdatetime(self.lastModified(), True)

    def set_summary(self, summary):
        self.setSummary(ustr(summary))

    def set_description(self, description):
        self.setDescription(ustr(description))

    def get_classification(self, translated=True):
        _class = self.classification()
        if translated:
            return self._translate_value(_class, self.classification_map)
        return _class

    def set_classification(self, classification):
        if classification in self.classification_map.keys():
            self.setClassification(self.classification_map[classification])
        elif classification in self.classification_map.values():
            self.setClassification(status)
        else:
            raise ValueError, _("Invalid classification %r") % (classification)

    def add_category(self, category):
        _categories = self.categories()
        _categories.append(ustr(category))
        self.setCategories(_categories)

    def _translate_value(self, val, map):
        name_map = dict([(v, k) for (k, v) in map.iteritems()])
        return name_map[val] if name_map.has_key(val) else 'UNKNOWN'

    def to_dict(self):
        if not self.isValid():
            return None

        data = dict()

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

            if val is not None:
                data[p] = val

        return data

    def __str__(self):
        xml = kolabformat.writeNote(self)
        error = kolabformat.error()

        if error == None or not error:
            return xml
        else:
            raise NoteIntegrityError, kolabformat.errorMessage()

class NoteIntegrityError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
