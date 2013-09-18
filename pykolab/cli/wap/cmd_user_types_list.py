# -*- coding: utf-8 -*-
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
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

import pykolab
from pykolab.cli import commands

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_user_types', execute, group='wap', description="List WAP user types.")

def execute(*args, **kw):
    from pykolab import wap_client
    # Create the authentication object.
    # TODO: Binds with superuser credentials!
    wap_client.authenticate()
    user_types = wap_client.user_types_list()

    for user_type in user_types['list']:
        type = user_types['list'][user_type]
        print "%-15s - %s" % (type['key'], type['description'])
