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

import sys

import commands

import pykolab

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('create_mailbox', execute, description=description(), aliases='cm')

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option(
            '--metadata',
            dest    = "metadata",
            action  = "store",
            default = None,
            help    = _("Set metadata for folder to ANNOTATION=VALUE")
        )

    my_option_group.add_option(
            '--partition',
            dest    = "partition",
            action  = "store",
            default = None,
            help    = _("Create folder on PARTITION.")
        )

def description():
    return """Create a mailbox or sub-folder of an existing mailbox."""

def execute(*args, **kw):
    try:
        mailbox = conf.cli_args.pop(0)
    except IndexError, errmsg:
        log.error(_("Invalid argument"))
        sys.exit(1)

    if not conf.metadata == None:
        if len(conf.metadata.split('=')) == 2:
            annotation = conf.metadata.split('=')[0]
            annotation_value = conf.metadata.split('=')[1]
        else:
            log.error(_("Invalid argument for metadata"))
            sys.exit(1)

    imap = IMAP()
    imap.connect()

    imap.create_folder(mailbox, partition=conf.partition)

    if not conf.metadata == None:
        imap.set_metadata(mailbox, conf.metadata.split('=')[0], conf.metadata.split('=')[1])

