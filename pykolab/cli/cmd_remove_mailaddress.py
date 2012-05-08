# -*- coding: utf-8 -*-
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
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

import commands

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('remove_mail', execute, description=description())

def description():
    return """Remove a user's mail address."""

def execute(*args, **kw):
    uid = conf.cli_args.pop(0)
    email_address = conf.cli_args.pop(0)

    user = auth.find_user('uid', uid)
    user = {
            'dn': user
        }

    user['mail'] = auth.get_user_attribute('klab.cc', user, 'mail')
    user['mailalternateaddress'] = auth.get_user_attribute('klab.cc', user, 'mailalternateaddress')

    if user['mail'] == email_address:
        auth.set_user_attribute('klab.cc', user, 'mail', '')

    if email_address in user['mailalternateaddress']:
        _user_addresses = []
        for address in user['mailalternateaddress']:
            if not address == email_address:
                _user_addresses.append(address)

        auth.set_user_attribute('klab.cc', user, 'mailAlternateAddress', _user_addresses)
