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

"""
    SASL authentication daemon for multi-domain Kolab deployments.

    The SASL authentication daemon can use the domain name space or realm
    in the login credentials to determine the backend authentication
    database, and authenticate the credentials supplied against that
    backend.
"""

from optparse import OptionParser
from ConfigParser import SafeConfigParser

import os
import shutil
import time
import traceback

import pykolab

from pykolab.auth import Auth
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('saslauthd')
conf = pykolab.getConf()

class SASLAuthDaemon(object):
    def __init__(self):
        daemon_group = conf.add_cli_parser_option_group(_("Daemon Options"))

        daemon_group.add_option(  "--fork",
                                dest    = "fork_mode",
                                action  = "store_true",
                                default = False,
                                help    = _("Fork to the background."))

        conf.finalize_conf()

    def run(self):
        """
            Run the SASL authentication daemon.
        """

        exitcode = 0

        try:
            pid = 1
            if conf.fork_mode:
                pid = os.fork()

            if pid == 0:
                log.remove_stdout_handler()

            self.do_saslauthd()

        except SystemExit, e:
            exitcode = e
        except KeyboardInterrupt:
            exitcode = 1
            log.info(_("Interrupted by user"))
        except AttributeError, e:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://bugzilla.kolabsys.com")
        except TypeError, e:
            exitcode = 1
            traceback.print_exc()
            log.error(_("Type Error: %s") % e)
        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://bugzilla.kolabsys.com")
        sys.exit(exitcode)

    def do_saslauthd(self):
        """
            Create the actual listener socket, and handle the authentication.

            The actual authentication handling is passed on to the appropriate
            backend authentication classes through the more generic Auth().
        """
        import binascii
        import socket
        import struct

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # TODO: The saslauthd socket path could be a setting.
        try:
            os.remove('/var/run/saslauthd/mux')
        except:
            # TODO: Do the "could not remove, could not start dance"
            pass

        s.bind('/var/run/saslauthd/mux')
        os.chmod('/var/run/saslauthd/mux', 0777)

        s.listen(5)

        while 1:
            (clientsocket, address) = s.accept()
            received = clientsocket.recv(4096)

            login = []

            start = 0
            end = 2

            while end < len(received):
                (length,) = struct.unpack("!H", received[start:end])
                start += 2
                end += length
                (value,) = struct.unpack("!%ds" %(length), received[start:end])
                start += length
                end = start + 2
                login.append(value)

            auth = Auth()
            if auth.authenticate(login):
                clientsocket.send(struct.pack("!H2s", 2, "OK"))
            else:
                clientsocket.send(struct.pack("!H2s", 2, "NO"))

            clientsocket.close()
