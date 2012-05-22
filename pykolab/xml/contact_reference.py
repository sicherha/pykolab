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
    def __init__(self, email=None):
        if email == None:
            kolabformat.ContactReference.__init__(self)
        else:
            kolabformat.ContactReference.__init__(self, email)

    def get_email(self):
        return self.email()

    def get_name(self):
        return self.name()

    def set_email(self, email):
        kolabformat.ContactReference.__init__(self, email)

    def set_name(self, name):
        self.setName(name)
