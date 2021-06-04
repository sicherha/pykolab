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

from __future__ import print_function

import sys

import commands

import pykolab

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_quota', execute, description=description(), aliases=['lq'])

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--server',
                                dest    = "connect_server",
                                action  = "store",
                                default = None,
                                metavar = "SERVER",
                                help    = _("List mailboxes on server SERVER only."))

def description():
    return """List quota for a folder."""

def execute(*args, **kw):
    """
        List quota for a mailbox
    """

    try:
        quota_folder = conf.cli_args.pop(0)
    except IndexError:
        quota_folder = '*'

    imap = IMAP()

    if not conf.connect_server == None:
        imap.connect(server=conf.connect_server)
    else:
        imap.connect()

    folders = []

    quota_folders = imap.list_folders(quota_folder)
    for quota_folder in quota_folders:
        try:
            (used, quota) = imap.get_quota(quota_folder)
            print("Folder: %s" % (quota_folder))
            if not used == None and not quota == None:
                if quota == 0:
                    print(_("The quota for folder %s is set to literally allow 0KB of storage.") % (quota_folder), file=sys.stderr)
                    print("%d (Used: %d, Percentage: %s)" % (quota, used, u'\u221E'))
                else:
                    percentage = round(((float)(used)/(float)(quota)) * 100.0, 1)
                    print("%d (Used: %d, Percentage: %d)" % (quota, used, percentage))
            else:
                if used == None:
                    print("%d (Used: %d, Percentage: %d)" % (quota, 0, 0))
                else:
                    print("No quota")
        except:
            try:
                (quota_root, used, quota) = imap.get_quota_root(quota_folder)
                print("Folder: %s" % (quota_folder))
                if not quota_root == None and not used == None and not quota == None:
                    if quota == 0:
                        print(_("The quota for folder %s is set to literally allow 0KB of storage.") % (quota_folder), file=sys.stderr)
                        print("%d (Used: %d, Percentage: %d)" % (quota, used, u'\u221E'))
                    else:
                        percentage = round(((float)(used)/(float)(quota)) * 100.0, 1)
                        print("%d (Root: %s, Used: %d, Percentage: %d)" % (quota, quota_root, used, percentage))
                else:
                    if used == None and not quota_root == None:
                        print("%d (Root: %s, Used: %d, Percentage: %d)" % (quota, quota_root, 0, 0))
                    else:
                        print("No quota")
            except:
                print("Folder: %s" % (quota_folder))
                print("No quota root")

