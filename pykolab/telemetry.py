#!/usr/bin/python
#
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

import os
import rfc822
import socket
import sys
import time

import sqlalchemy

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text

from sqlalchemy.interfaces import PoolListener

from sqlalchemy import create_engine
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
try:
    from sqlalchemy.orm import sessionmaker
except:
    from sqlalchemy.orm import create_session

from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint

import pykolab

from pykolab import utils
from pykolab.translate import _

conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.telemetry')

metadata = MetaData()

##
## Classes
##

class TelemetryCommand(object):
    def __init__(self, command):
        self.command = command

class TelemetryCommandArg(object):

    command = relationship(
            'TelemetryCommand',
            order_by='telemetry_command,id',
            backref='command_args'
        )

    def __init__(self, command, command_arg=''):
        self.command_id = command.id
        self.command_arg = command_arg

class TelemetryCommandIssue(object):

    session = relationship(
            'TelemetrySession',
            order_by='telemetry_session.id',
            backref='command_issues'
        )

    response = relationship(
            'TelemetryServerResponse',
            order_by='telemetry_server_response',
            backref='command_issue'
        )

    def __init__(self, command_tag, command, command_arg, session):
        self.command_tag = command_tag
        self.command_id = command.id
        self.command_arg_id = command_arg.id
        self.session_id = session.id

class TelemetryFile(object):

    #server = relationship(
            #'TelemetryServer',
            #backref='files'
        #)

    def __init__(self, filepath, contents):
        self.filepath = filepath
        self.contents = contents

class TelemetryLog(object):
    def __init__(self, log_file):
        self.log_file = log_file

        # We start out not being in a session
        self.session = None
        self.server_responding = False
        self.server_response = {}

        db = init_db()

        # TODO: Makes telemetry logs needs to be processed on the actual node
        server = db.query(
                TelemetryServer
            ).filter_by(
                    fqdn=socket.gethostname()
                ).first()

        if server == None:
            db.add(TelemetryServer(fqdn=socket.gethostname()))
            db.commit()
            server = db.query(
                    TelemetryServer
                ).filter_by(
                        fqdn=socket.gethostname()
                    ).first()

        self.server = server

        # Username is in the directory name
        user_name = os.path.basename(os.path.dirname(log_file))

        user = db.query(
                TelemetryUser
            ).filter_by(
                    sasl_username=user_name
                ).first()

        if user == None:
            db.add(TelemetryUser(sasl_username=user_name))
            db.commit()
            user = db.query(
                    TelemetryUser
                ).filter_by(
                        sasl_username=user_name
                    ).first()

        self.user = user

        # Session is at the end of the filename
        self.pid = os.path.basename(log_file)

        # Open the log file
        fp = open(self.log_file, 'r')

        # Insert log file in database
        db.add(TelemetryFile(filepath=log_file,contents=fp.read()))
        db.commit()

        # Go back to the beginning
        fp.seek(0)

        line_num = 0

        try:
            for line in fp:
                if line == None:
                    break

                line = line.strip()

                line_num += 1

                log.debug("%s (%d): %s" %(self.log_file,line_num,line), level=8)

                if line.startswith('---------- '):
                    # This is the actual start of a session
                    datetime = ' '.join(line.split(' ')[2:])

                    # Translate datetime into epoch
                    timestamp = (int)(time.mktime(rfc822.parsedate(datetime)))

                    session = db.query(
                            TelemetrySession
                        ).filter_by(
                                server_id=self.server.id,
                                pid=self.pid,
                                user_id=self.user.id,
                                start=timestamp
                            ).first()

                    if session == None:
                        db.add(
                                TelemetrySession(
                                        pid=self.pid,
                                        server=self.server,
                                        user=self.user,
                                        start=timestamp
                                    )
                            )

                        db.commit()

                        session = db.query(
                                TelemetrySession
                            ).filter_by(
                                    server_id=self.server.id,
                                    pid=self.pid,
                                    user_id=self.user.id,
                                    start=timestamp
                                ).first()

                    self.session = session

                    self.server_responding = False

                    if hasattr(self,'command_issue'):
                        del self.command_issue

                    continue

                if line.startswith('<') and not self.server_responding:
                    # <1310124946<00000003 LIST "" *
                    timestamp = line.split('<')[1]
                    client_command_tag = line.split('<')[2].split(' ')[0]
                    client_command = line.split('<')[2].split(' ')[1]
                    client_command_arg = ' '.join(
                            line.split('<')[2].split(' ')[2:]
                        )

                    command = db.query(
                            TelemetryCommand
                        ).filter_by(
                                command=client_command
                            ).first()

                    if command == None:
                        db.add(
                                TelemetryCommand(
                                        command=client_command
                                    )
                            )

                        db.commit()
                        command = db.query(
                                TelemetryCommand
                            ).filter_by(
                                    command=client_command
                                ).first()

                    command_arg = db.query(
                            TelemetryCommandArg
                        ).filter_by(
                                command_id=command.id,
                                command_arg=client_command_arg
                            ).first()

                    if command_arg == None:
                        db.add(
                                TelemetryCommandArg(
                                        command=command,
                                        command_arg=client_command_arg
                                    )
                            )

                        db.commit()
                        command_arg = db.query(
                                TelemetryCommandArg
                            ).filter_by(
                                    command_id=command.id,
                                    command_arg=client_command_arg
                                ).first()


                    command_issue = db.query(
                            TelemetryCommandIssue
                        ).filter_by(
                                command_tag=client_command_tag,
                                command_id=command.id,
                                command_arg_id=command_arg.id,
                                session_id=self.session.id
                            ).first()

                    if command_issue == None:
                        db.add(
                                TelemetryCommandIssue(
                                        command_tag=client_command_tag,
                                        command=command,
                                        command_arg=command_arg,
                                        session=self.session
                                    )
                            )

                        db.commit()
                        command_issue = db.query(
                                TelemetryCommandIssue
                            ).filter_by(
                                    command_tag=client_command_tag,
                                    command_id=command.id,
                                    command_arg_id=command_arg.id,
                                    session_id=self.session.id
                                ).first()

                    self.command_issue = command_issue

                    continue

                if line.startswith('>'):
                    self.server_responding = True

                    timestamp = line.split('>')[1]
                    server_response_line = ' '.join(line.split('>')[2:])

                    if hasattr(self,'command_issue'):
                        self.server_response[self.command_issue] = []

                        if hasattr(self.command_issue, 'command_tag'):
                            if server_response_line.startswith(self.command_issue.command_tag):
                                if self.server_responding:
                                    if hasattr(self,'command_issue'):
                                        self.server_response[self.command_issue].append(
                                                server_response_line
                                            )

                                        response = '\n'.join(
                                                self.server_response[self.command_issue]
                                            )

                                        db.add(
                                                TelemetryServerResponse(
                                                        command_issue=self.command_issue,
                                                        response=response
                                                    )
                                            )

                                        db.commit()

                                        self.server_response = {}

                                self.server_responding = False

                                continue

                    self.server_response[self.command_issue].append(
                            server_response_line
                        )

                    continue


                if line.startswith('*'):
                    if self.server_responding:
                        if hasattr(self,'command_issue'):
                            self.server_response[self.command_issue].append(
                                    line
                                )

                    continue

                if line == "":
                    if self.server_responding:
                        if hasattr(self,'command_issue'):
                            self.server_response[self.command_issue].append(
                                    line
                                )

                    continue

                if hasattr(self, 'command_issue'):
                    if hasattr(self.command_issue, 'command_tag'):
                        if line.startswith(self.command_issue.command_tag):
                            if self.server_responding:
                                self.server_response[self.command_issue].append(
                                        line
                                    )

                                response = '\n'.join(
                                        self.server_response[self.command_issue]
                                    )

                                db.add(
                                        TelemetryServerResponse(
                                                command_issue=self.command_issue,
                                                response=response
                                            )
                                    )

                                db.commit()

                                self.server_response = {}

                            self.server_responding = False

                            continue

        finally:
            fp.close()

class TelemetryServer(object):

    sessions = relationship(
            'TelemetrySession',
            order_by='telemetry_session.timestamp',
            backref='server'
        )

    #files = relationship(
            #'TelemetryFiles',
            #order_by='telemetry_file.filepath',
            #backref=server
        #)

    def __init__(self, fqdn):
        self.fqdn = fqdn

class TelemetryServerResponse(object):
    def __init__(self, command_issue, response):
        self.command_issue_id = command_issue.id
        self.response = response

class TelemetrySession(object):

    commands = relationship(
            'TelemetryCommand',
            order_by='telementry_command.id',
            backref='session'
        )

    server = relationship(
            'TelemetryServer',
            order_by='telemetry_server.id',
            backref='sessions'
        )

    user = relationship('TelemetryUser', uselist=False)

    def __init__(self, pid, user, server, start=0):
        self.pid = pid
        self.user_id = user.id
        self.server_id = server.id
        self.start = start

    def get_user(self):
        return self.user

class TelemetryUser(object):

    commands = relationship(
            'TelemetryCommand',
            order_by="telemetry_command.timestamp",
            backref="user"
        )

    sessions = relationship(
            'TelemetrySession',
            uselist=False
        )

    def __init__(self, sasl_username=None, created=(int)(time.time())):
        self.sasl_username = sasl_username
        self.created = created
        self.updated = (int)(time.time())

##
## Tables
##

telemetry_command_table = Table(
        'telemetry_command', metadata,
        Column('id', Integer, primary_key=True),
        Column('command', String(128), nullable=False),
    )

telemetry_command_arg_table = Table(
        'telemetry_command_arg', metadata,
        Column('id', Integer, primary_key=True),
        Column('command_id', ForeignKey('telemetry_command.id')),
        Column('command_arg', String(256)),
    )

telemetry_command_issue_table = Table(
        'telemetry_command_issue', metadata,
        Column('id', Integer, primary_key=True),
        Column('command_tag', String(16)),
        Column('command_id', ForeignKey('telemetry_command.id')),
        Column('command_arg_id', ForeignKey('telemetry_command_arg.id')),
        Column('session_id', ForeignKey('telemetry_session.id')),
    )

telemetry_file_table = Table(
        'telemetry_file', metadata,
        Column('id', Integer, primary_key=True),
        Column('filepath', String(256)),
        Column('contents', Text),
    )

telemetry_server_table = Table(
        'telemetry_server', metadata,
        Column('id', Integer, primary_key=True),
        Column('fqdn', String(64), nullable=False)
    )

Index(
        'fqdn',
        telemetry_server_table.c.fqdn
    )

telemetry_server_response_table = Table(
        'telemetry_server_response', metadata,
        Column('id', Integer, primary_key=True),
        Column('command_issue_id', ForeignKey('telemetry_command_issue.id')),
        Column('response', Text),
    )

telemetry_session_table = Table(
        'telemetry_session', metadata,
        Column('id', Integer, primary_key=True),
        Column('pid', Integer, nullable=False),
        Column('user_id', ForeignKey('telemetry_user.id')),
        Column('server_id', ForeignKey('telemetry_server.id')),
        Column('start', Integer, nullable=False),
    )

Index(
        'puss',
        telemetry_session_table.c.pid,
        telemetry_session_table.c.user_id,
        telemetry_session_table.c.server_id,
        telemetry_session_table.c.start,
        unique=True
    )

telemetry_user_table = Table(
        'telemetry_user', metadata,
        Column('id', Integer, primary_key=True),
        Column('sasl_username', String(64), nullable=False),
        Column('created', Integer, nullable=False),
        Column('updated', Integer, nullable=False),
    )

Index(
        'sasl_username',
        telemetry_user_table.c.sasl_username,
        unique=True
    )

##
## Table <-> Class Mappers
##

mapper(TelemetryCommand, telemetry_command_table)
mapper(TelemetryCommandArg, telemetry_command_arg_table)
mapper(TelemetryCommandIssue, telemetry_command_issue_table)
mapper(TelemetryFile, telemetry_file_table)
mapper(TelemetryServer, telemetry_server_table)
mapper(TelemetryServerResponse, telemetry_server_response_table)
mapper(TelemetrySession, telemetry_session_table)
mapper(TelemetryUser, telemetry_user_table)

##
## Functions
##

def expire_sessions(retention=7):
    """
        Expire sessions older then 'retention' days
    """
    start_max = ((int)(time.time()) - (retention * 24 * 60 * 60))
    #start_max = (int)(time.time())
    log.info(_("Expiring sessions that started before or on %d") %(start_max))

    db = init_db()

    sessions = db.query(
            TelemetrySession
        ).filter(
                telemetry_session_table.c.start <= start_max
            ).order_by(
                    telemetry_session_table.c.start
                )

    for session in sessions:
        log.debug(_("Expiring session ID: %d") %(session.id), level=8)

        # Expire related information
        command_issue_ids = db.query(
                TelemetryCommandIssue
            ).filter_by(session_id=session.id)

        for command_issue_id in command_issue_ids:
            # Expire server reponses
            server_responses = db.query(
                    TelemetryServerResponse
                ).filter_by(
                        command_issue_id=command_issue_id.id
                    ).delete()

            db.delete(command_issue_id)
            db.commit()

        log.debug(
                _("Session with ID %d expired from database") %(session.id),
                level=8
            )

        db.delete(session)
        db.commit()

def init_db():
    """
        Returns a SQLAlchemy Session() instance.
    """

    db = None
    db_uri = None

    if conf.has_section('kolab_telemetry'):
        if conf.has_option('kolab_telemetry', 'uri'):
            db_uri = conf.get('kolab_telemetry', 'uri')

    if not db_uri == None:
        echo = conf.debuglevel > 8
        engine = create_engine(db_uri, echo=echo)

        try:
            metadata.create_all(engine)
        except sqlalchemy.exc.OperationalError, e:
            log.error(_("Operational Error in telemetry database: %s" %(e)))

        Session = sessionmaker(bind=engine)
        db = Session()

    if db == None:
        log.error(_("No database available"))

    return db
