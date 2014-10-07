import kolabformat

class Contact(kolabformat.Contact):
    type = 'contact'

    def __init__(self, *args, **kw):
        kolabformat.Contact.__init__(self, *args, **kw)

    def get_uid(self):
        uid = self.uid()
        if not uid == '':
            return uid
        else:
            self.__str__()
            return kolabformat.getSerializedUID()

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
        self.setName(name)

    def to_ditc(self):
        # TODO: implement this
        return dict(name=self.name())

    def __str__(self):
        return kolabformat.writeContact(self)
