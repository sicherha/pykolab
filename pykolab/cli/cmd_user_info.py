# -*- coding: utf-8 -*-
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
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

from __future__ import print_function

import sys

import commands

import pykolab

from pykolab import utils
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('user_info', execute, description="Display user information.")

def execute(*args, **kw):
    from pykolab import wap_client

    try:
        user = conf.cli_args.pop(0)
    except IndexError:
        user = utils.ask_question(_("Email address"))

    result = wap_client.authenticate(username=conf.get("ldap", "bind_dn"), password=conf.get("ldap", "bind_pw"))

    if len(user.split('@')) > 1:
        wap_client.system_select_domain(user.split('@')[1])

    user_info = wap_client.user_find({'mail':user})

    if user_info == None or not user_info:
        print(_("No such user %s") % (user), file=sys.stderr)
        sys.exit(0)

    unic_attrs = ['displayname', 'givenname', 'cn', 'sn', 'ou', 'entrydn']

    for (k,v) in user_info.iteritems():
        if k in unic_attrs:
            print("%s: %s" % (k,v))
        else:
            print("%s: %r" % (k,v))
