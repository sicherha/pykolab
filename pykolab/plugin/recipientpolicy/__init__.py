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

from pykolab import utils
from pykolab.auth import Auth
from pykolab.translate import _

class KolabRecipientpolicy(object):
    """
        Example plugin making quota adjustments given arbitrary conditions.
    """

    def __init__(self, conf=None):
        self.conf = conf

    #def mail_domain_space_policy_check(self, kw={}, args=()):
        #(mail, alternative_mail, domain_name, domain_root_dn) = args

        ## Your actions go here. For example:
        #return (mail, alternative_mail)

    def set_user_attrs_mail(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_attrs_mail' hook:

            - current user attributes
        """
        (user_attrs) = args

        user_attrs = utils.normalize(user_attrs)

        try:
            mail = self.conf.get_raw('recipient_policy', 'primary_email') % user_attrs
            return mail
        except KeyError, e:
            self.conf.log.warning(_("Attribute substitution for 'mail' failed in Recipient Policy"))
            return "user@example.org"

    def set_user_attrs_alternative_mail(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_attrs_alternative_mail' hook:

            - current user attributes
        """

        (user_attrs) = args

        user_attrs = utils.normalize(user_attrs)

        other_email_routines = self.conf.get_raw('recipient_policy', 'other_email')

        exec("other_email_routines = %s" % other_email_routines)

        alternative_mail = []

        for routine in other_email_routines.keys():
            try:
                exec("retval = '%s'.%s" % (routine,other_email_routines[routine] % user_attrs))
            except KeyError, e:
                self.conf.log.warning(_("Attribute substitution for 'mail' failed in Recipient Policy"))
                retval = "user@example.org"
            alternative_mail.append(retval)

        return alternative_mail
