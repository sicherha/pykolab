# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import pykolab

from pykolab import utils
from pykolab.translate import _

conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.plugins.recipientpolicy')

class KolabRecipientpolicy(object):
    """
        Example plugin making quota adjustments given arbitrary conditions.
    """

    def __init__(self):
        pass

    def add_options(self, *args,  **kw):
        pass

    #def mail_domain_space_policy_check(self, kw={}, args=()):
        #(mail, alternative_mail, domain_name, domain_root_dn) = args

        ## Your actions go here. For example:
        #return (mail, alternative_mail)

    def set_primary_mail(self, *args, **kw):
        """
            The arguments passed to the 'set_user_attrs_mail' hook:

            primary_mail - the policy
            user_attrs - the current user attributes
            primary_domain - the domain to use in the primary mail attribute
            secondary_domains - the secondary domains that are aliases

            Return the new primary mail address
        """

        user_attrs = utils.normalize(kw['entry'])

        if not user_attrs.has_key('domain'):
            user_attrs['domain'] = kw['primary_domain']
        elif not user_attrs['domain'] == kw['primary_domain']:
            user_attrs['domain'] = kw['primary_domain']

        if not user_attrs.has_key('preferredlanguage'):
            default_locale = conf.get(user_attrs['domain'], 'default_locale')
            if default_locale == None:
                default_locale = conf.get('kolab', 'default_locale')
            if default_locale == None:
                default_locale = 'en_US'

            user_attrs['preferredlanguage'] = default_locale

        try:
            mail = kw['primary_mail'] % user_attrs
            mail = utils.translate(mail, user_attrs['preferredlanguage'])
            mail = mail.lower()
            return mail
        except KeyError:
            log.warning(_("Attribute substitution for 'mail' failed in Recipient Policy"))
            if user_attrs.has_key('mail'):
                return user_attrs['mail']
            else:
                return None

    def set_secondary_mail(self, *args, **kw):
        """
            The arguments passed to the 'set_user_attrs_alternative_mail' hook:

            primary_mail - the policy
            user_attrs - the current user attributes
            primary_domain - the domain to use in the primary mail attribute
            secondary_domains - the secondary domains that are aliases

            Return a list of secondary mail addresses
        """

        user_attrs = utils.normalize(kw['entry'])

        if not user_attrs.has_key('domain'):
            user_attrs['domain'] = kw['primary_domain']
        elif not user_attrs['domain'] == kw['primary_domain']:
            user_attrs['domain'] = kw['primary_domain']

        if not user_attrs.has_key('preferredlanguage'):
            default_locale = conf.get(user_attrs['domain'], 'default_locale')
            if default_locale == None:
                default_locale = conf.get(user_attrs['domain'], 'default_locale')
            if default_locale == None:
                default_locale = 'en_US'

            user_attrs['preferredlanguage'] = default_locale

        try:
            exec("alternative_mail_routines = %s" % kw['secondary_mail'])
        except Exception:
            log.error(_("Could not parse the alternative mail routines"))

        alternative_mail = []

        log.debug(_("Alternative mail routines: %r") % (alternative_mail_routines), level=8)
        _domains = [ kw['primary_domain'] ] + kw['secondary_domains']

        for attr in [ 'givenname', 'sn', 'surname' ]:
            try:
                user_attrs[attr] = utils.translate(user_attrs[attr], user_attrs['preferredlanguage'])
            except Exception:
                log.error(_("An error occurred in composing the secondary mail attribute for entry %r") % (user_attrs['id']))
                if conf.debuglevel > 8:
                    import traceback
                    traceback.print_exc()
                return []

        for number in alternative_mail_routines:
            for routine in alternative_mail_routines[number]:
                try:
                    exec("retval = '%s'.%s" % (routine,alternative_mail_routines[number][routine] % user_attrs))

                    log.debug(_("Appending additional mail address: %s") % (retval), level=8)
                    alternative_mail.append(retval)

                except Exception as errmsg:
                    log.error(_("Policy for secondary email address failed: %r") % (errmsg))
                    if conf.debuglevel > 8:
                        import traceback
                        traceback.print_exc()
                    return []

                for _domain in kw['secondary_domains']:
                    user_attrs['domain'] = _domain
                    try:
                        exec("retval = '%s'.%s" % (routine,alternative_mail_routines[number][routine] % user_attrs))

                        log.debug(_("Appending additional mail address: %s") % (retval), level=8)
                        alternative_mail.append(retval)

                    except KeyError:
                        log.warning(_("Attribute substitution for 'alternative_mail' failed in Recipient Policy"))

        alternative_mail = utils.normalize(alternative_mail)

        alternative_mail = list(set(alternative_mail))

        return alternative_mail
