
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

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

from pykolab import telemetry
from pykolab.cli import commands

def __init__():
    commands.register('examine_session', execute, group='telemetry', description="Examine a Telemetry session.")

def execute(*args, **kw):
    db = telemetry.init_db()

    wanted = False

    if session_id == None:
        try:
            wanted = conf.cli_args.pop(0)
        except:
            log.error(_("Unspecified session identifier"))
            sys.exit(1)

    if not wanted:
        wanted = session_id

    session_wanted = None

    try:
        _wanted = (int)(wanted)
        session_wanted = _wanted
    except:
        user_wanted = wanted

    if not session_wanted == None:
        session = db.query(
                telemetry.TelemetrySession
            ).filter_by(
                    id=session_wanted
                ).first()

        if session == None:
            log.error(_("Invalid session identifier"))
            sys.exit(1)

        user = db.query(
                telemetry.TelemetryUser
            ).filter_by(
                    id=session.user_id
                ).first()

        server = db.query(
                telemetry.TelemetryServer
            ).filter_by(
                    id=session.server_id
                ).first()

    else:
        user = db.query(
                telemetry.TelemetryUser
            ).filter_by(
                sasl_username=user_wanted
                ).first()

        sessions = db.query(
                telemetry.TelemetrySession
            ).filter_by(
                    user_id=user.id
                ).order_by(
                        telemetry.telemetry_session_table.c.start
                    )

        for session in sessions:
            self.action_telemetry_examine_session(session_id=session.id)

        return

    print(_("Session by %s on server %s") % (user.sasl_username,server.fqdn))

    command_issues = db.query(
            telemetry.TelemetryCommandIssue
        ).filter_by(
                session_id=session.id
            )

    for command_issue in command_issues:
        command = db.query(
                telemetry.TelemetryCommand
            ).filter_by(
                    id=command_issue.command_id
                ).first()

        command_arg = db.query(
                telemetry.TelemetryCommandArg
            ).filter_by(
                    id=command_issue.command_arg_id
                ).first()

        print("Client(%d): %s %s %s" % (
                command_issue.id,
                command_issue.command_tag,
                command.command,
                command_arg.command_arg
            ))

        server_responses = db.query(
                telemetry.TelemetryServerResponse
            ).filter_by(
                    command_issue_id=command_issue.id
                )

        for server_response in server_responses:
            server_response_lines = server_response.response.split('\n');
            for server_response_line in server_response_lines:
                print("Server(%d): %s" % (
                        server_response.id,
                        server_response_line
                    ))

