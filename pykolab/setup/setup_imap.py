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

from augeas import Augeas
from Cheetah.Template import Template
import os
import subprocess

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register(
            'imap',
            execute,
            description=description(),
            after=['ldap']
        )

def description():
    return _("Setup IMAP.")

def execute(*args, **kw):
    """
        Apply the necessary settings to /etc/imapd.conf
    """

    configdirectory = "/var/lib/imap/"
    partition_default = "/var/spool/imap/"
    sievedir = "/var/lib/imap/sieve/"

    if os.path.isdir("/var/lib/cyrus/"):
        configdirectory = "/var/lib/cyrus/"
        sievedir = "/var/lib/cyrus/sieve/"

    if os.path.isdir("/var/spool/cyrus/"):
        partition_default = "/var/spool/cyrus/"

    imapd_settings = {
            "ldap_servers": conf.get('ldap', 'ldap_uri'),
            "ldap_base": conf.get('ldap', 'base_dn'),
            "ldap_bind_dn": conf.get('ldap', 'service_bind_dn'),
            "ldap_password": conf.get('ldap', 'service_bind_pw'),
            "ldap_filter": '(|(&(|(uid=%s)(uid=cyrus-murder))(uid=%%U))(&(|(uid=%%U)(mail=%%U@%%d)(mail=%%U@%%r))(objectclass=kolabinetorgperson)))' % (conf.get('cyrus-imap', 'admin_login')),
            "ldap_user_attribute": conf.get('cyrus-sasl', 'result_attribute'),
            "ldap_group_base": conf.get('ldap', 'base_dn'),
            "ldap_group_filter": "(&(cn=%u)(objectclass=ldapsubentry)(objectclass=nsroledefinition))",
            "ldap_group_scope": "one",
            "ldap_member_base": conf.get('ldap','user_base_dn'),
            "ldap_member_method": "attribute",
            "ldap_member_attribute": "nsrole",
            "admins": conf.get('cyrus-imap', 'admin_login'),
            "postuser": "shared",
            "configdirectory": configdirectory,
            "partition_default": partition_default,
            "sievedir": sievedir
        }

    template_file = None

    if os.path.isfile('/etc/kolab/templates/imapd.conf.tpl'):
        template_file = '/etc/kolab/templates/imapd.conf.tpl'
    elif os.path.isfile('/usr/share/kolab/templates/imapd.conf.tpl'):
        template_file = '/usr/share/kolab/templates/imapd.conf.tpl'
    elif os.path.isfile(os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'imapd.conf.tpl'))):
        template_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'imapd.conf.tpl'))

    if not template_file == None:
        fp = open(template_file, 'r')
        template_definition = fp.read()
        fp.close()

        t = Template(template_definition, searchList=[imapd_settings])
        fp = open('/etc/imapd.conf', 'w')
        fp.write(t.__str__())
        fp.close()

    else:
        log.error(_("Could not write out Cyrus IMAP configuration file /etc/imapd.conf"))
        return

    cyrus_settings = {}

    template_file = None

    if os.path.isfile('/etc/kolab/templates/cyrus.conf.tpl'):
        template_file = '/etc/kolab/templates/cyrus.conf.tpl'
    elif os.path.isfile('/usr/share/kolab/templates/cyrus.conf.tpl'):
        template_file = '/usr/share/kolab/templates/cyrus.conf.tpl'
    elif os.path.isfile(os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'cyrus.conf.tpl'))):
        template_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'cyrus.conf.tpl'))

    if not template_file == None:
        fp = open(template_file, 'r')
        template_definition = fp.read()
        fp.close()

        t = Template(template_definition, searchList=[cyrus_settings])
        fp = open('/etc/cyrus.conf', 'w')
        fp.write(t.__str__())
        fp.close()

    else:
        log.error(_("Could not write out Cyrus IMAP configuration file /etc/cyrus.conf"))
        return

    annotations = [
            "/vendor/kolab/activesync,mailbox,string,backend,value.priv,r",
            "/vendor/kolab/color,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/displayname,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/folder-test,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/folder-type,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/incidences-for,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/pxfb-readable-for,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/uniqueid,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/kolab/h-share-attr-desc,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/horde/share-params,mailbox,string,backend,value.shared value.priv,a",
            "/vendor/x-toltec/test,mailbox,string,backend,value.shared value.priv,a",
        ]

    fp = open('/etc/imapd.annotations.conf', 'w')
    fp.write("\n".join(annotations))
    fp.close()

    if os.path.isfile('/etc/default/kolab-saslauthd'):
        myaugeas = Augeas()
        setting = os.path.join('/files/etc/default/kolab-saslauthd','START')

        if not myaugeas.get(setting) == 'yes':
            myaugeas.set(setting,'yes')
            myaugeas.save()

        myaugeas.close()

    imapservice = 'cyrus-imapd.service'
    if os.path.isfile('/usr/lib/systemd/system/cyrus.service'):
        imapservice = 'cyrus.service'

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['systemctl', 'stop', 'saslauthd.service'])
        subprocess.call(['systemctl', 'restart', 'kolab-saslauthd.service'])
        subprocess.call(['systemctl', 'restart', imapservice])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['service', 'saslauthd', 'stop'])
        subprocess.call(['service', 'kolab-saslauthd', 'restart'])
        subprocess.call(['service', 'cyrus-imapd', 'restart'])
    elif os.path.isfile('/usr/sbin/service'):
        subprocess.call(['/usr/sbin/service','saslauthd','stop'])
        subprocess.call(['/usr/sbin/service','kolab-saslauthd','restart'])
        subprocess.call(['/usr/sbin/service','cyrus-imapd','restart'])
    else:
        log.error(_("Could not start the cyrus-imapd and kolab-saslauthd services."))

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['systemctl', 'disable', 'saslauthd.service'])
        subprocess.call(['systemctl', 'enable', 'kolab-saslauthd.service'])
        subprocess.call(['systemctl', 'enable', imapservice])
    elif os.path.isfile('/sbin/chkconfig'):
        subprocess.call(['chkconfig', 'saslauthd', 'off'])
        subprocess.call(['chkconfig', 'kolab-saslauthd', 'on'])
        subprocess.call(['chkconfig', 'cyrus-imapd', 'on'])
    elif os.path.isfile('/usr/sbin/update-rc.d'):
        subprocess.call(['/usr/sbin/update-rc.d', 'saslauthd', 'disable'])
        subprocess.call(['/usr/sbin/update-rc.d', 'kolab-saslauthd', 'defaults'])
        subprocess.call(['/usr/sbin/update-rc.d', 'cyrus-imapd', 'defaults'])
    else:
        log.error(_("Could not configure to start on boot, the " + \
                "cyrus-imapd and kolab-saslauthd services."))
