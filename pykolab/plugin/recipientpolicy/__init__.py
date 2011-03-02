# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 only
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

from pykolab.auth import Auth

class KolabRecipientpolicy(object):
    """
        Example plugin making quota adjustments given arbitrary conditions.
    """

    def __init__(self, conf=None):
        self.conf = conf

    def set_user_attrs_mail(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_attrs_mail' hook:

            - current user attributes
        """
        (user_attrs) = args
        mail = self.conf.get_raw('recipient_policy', 'primary_email') % self.normalize(user_attrs)
        return mail

    def set_user_attrs_alternative_mail(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_attrs_alternative_mail' hook:

            - current user attributes
        """

        (user_attrs) = args

        mail = self.conf.get_raw('recipient_policy', 'primary_email') % self.normalize(user_attrs)
        other_email_routines = self.conf.get_raw('recipient_policy', 'other_email')

        exec("other_email_routines = %s" % other_email_routines)

        alternative_email = []

        for routine in other_email_routines.keys():
            exec("retval = '%s'.%s" % (routine,other_email_routines[routine] % self.normalize(user_attrs)))
            alternative_email.append(retval)

        return alternative_email

    def normalize(self, user_attrs):
        if user_attrs.has_key('sn'):
            user_attrs['surname'] = user_attrs['sn'].replace(' ', '')

        if user_attrs.has_key('mail'):
            if len(user_attrs['mail'].split('@')) > 1:
                user_attrs['domain'] = user_attrs['mail'].split('@')[1]

        return user_attrs
