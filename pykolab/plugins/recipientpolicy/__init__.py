# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 or, at your option, any later version
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

    def set_primary_mail(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_attrs_mail' hook:

            - current user attributes
        """

        (user_attrs, primary_domain, secondary_domains) = args

        user_attrs = utils.normalize(user_attrs)

        if not user_attrs.has_key('domain'):
            user_attrs['domain'] = primary_domain
        elif not user_attrs['domain'] == primary_domain:
            user_attrs['domain'] = primary_domain

        try:
            mail = kw['primary_mail'] % user_attrs
            return mail.lower()
        except KeyError, e:
            self.conf.log.warning(_("Attribute substitution for 'mail' failed in Recipient Policy"))
            return user_attrs['mail'].lower()

    def set_secondary_mail(self, kw={}, args=()):
        """
            The arguments passed to the 'set_user_attrs_alternative_mail' hook:

            - current user attributes
        """

        (user_attrs, primary_domain, secondary_domains) = args

        user_attrs = utils.normalize(user_attrs)

        user_attrs['standard_domain'] = primary_domain

        exec("alternative_mail_routines = %s" % kw['secondary_mail'])

        alternative_mail = []

        for routine in alternative_mail_routines.keys():
            for _domain in [ primary_domain ] + secondary_domains:
                user_attrs['domain'] = _domain
                try:
                    exec("retval = '%s'.%s" % (routine,alternative_mail_routines[routine] % user_attrs))
                except KeyError, e:
                    self.conf.log.warning(_("Attribute substitution for 'alternative_mail' failed in Recipient Policy"))
                alternative_mail.append(retval)

        return alternative_mail
