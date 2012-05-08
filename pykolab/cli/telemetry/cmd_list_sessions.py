
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

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

from pykolab import telemetry
from pykolab.cli import commands

def __init__():
    commands.register('list_sessions', execute, group='telemetry', description="List IMAP sessions using Telemetry.")

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("List Options"))
    my_option_group.add_option( '--since',
                                dest    = "since",
                                action  = "store",
                                default = 0,
                                help    = _("Display sessions since ..."))

def execute(*args, **kw):
    db = telemetry.init_db()

    sessions = db.query(
            telemetry.TelemetrySession
        ).order_by(
                telemetry.telemetry_session_table.c.start
            )

    for session in sessions:
        user = db.query(
                telemetry.TelemetryUser
            ).filter_by(
                    id=session.user_id
                ).first()

        print _("Session for user %s started at %s with ID %s") % (
                user.sasl_username,
                session.start,
                session.id
            )

