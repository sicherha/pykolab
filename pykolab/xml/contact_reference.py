import kolabformat

"""
    def __eq__(self, *args): return _kolabformat.ContactReference___eq__(self, *args)
    def isValid(self): return _kolabformat.ContactReference_isValid(self)
    def setName(self, *args): return _kolabformat.ContactReference_setName(self, *args)
    def email(self): return _kolabformat.ContactReference_email(self)
    def uid(self): return _kolabformat.ContactReference_uid(self)
    def name(self): return _kolabformat.ContactReference_name(self)
    def type(self): return _kolabformat.ContactReference_type(self)
"""

class ContactReference(kolabformat.ContactReference):
    properties_map = {
        'email': 'email',
        'name':  'name',
        'type':  'type',
        'uid':   'uid',
    }

    def __init__(self, email=None, name=""):
        if email == None:
            kolabformat.ContactReference.__init__(self)
        elif isinstance(email, kolabformat.ContactReference):
            kolabformat.ContactReference.__init__(self, email.email(), email.name(), email.uid())
        else:
            kolabformat.ContactReference.__init__(self, email, name)

    def get_email(self):
        return self.email()

    def get_name(self):
        return self.name()

    def set_cn(self, value):
        self.setName(value)

    def set_email(self, email):
        kolabformat.ContactReference.__init__(self, email, self.name(), self.uid())

    def set_name(self, name):
        self.setName(name)

    def to_dict(self):
        data = dict()

        for p, getter in self.properties_map.items():
            val = None
            if hasattr(self, getter):
                val = getattr(self, getter)()
            if val is not None:
                data[p] = val

        return data
