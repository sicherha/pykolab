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

import sys

import commands

import pykolab

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('list_quota', execute, description=description(), aliases=['lq'])

def description():
    return """List quota for a folder."""

def execute(*args, **kw):
    """
        List quota for a mailbox
    """

    try:
        quota_folder = conf.cli_args.pop(0)
    except IndexError, e:
        quota_folder = '*'

    imap = IMAP()
    imap.connect()

    folders = []

    quota_folders = imap.lm(quota_folder)
    for quota_folder in quota_folders:
        try:
            (used, quota) = imap.get_quota(quota_folder)
            print "Folder: %s" % (quota_folder)
            if not used == None and not quota == None:
                if quota == 0:
                    print >> sys.stderr, _("The quota for folder %s is set to literally allow 0KB of storage.") % (quota_folder)
                    print "%d (Used: %d, Percentage: %s)" % (quota, used, u'\u221E')
                else:
                    percentage = round(((float)(used)/(float)(quota)) * 100.0, 1)
                    print "%d (Used: %d, Percentage: %d)" % (quota, used, percentage)
            else:
                print "No quota"
        except:
            try:
                (quota_root, used, quota) = imap.get_quota_root(quota_folder)
                print "Folder: %s" % (quota_folder)
                if not quota_root == None and not used == None and not quota == None:
                    if quota == 0:
                        print >> sys.stderr, _("The quota for folder %s is set to literally allow 0KB of storage.") % (quota_folder)
                        print "%d (Used: %d, Percentage: %d)" % (quota, used, u'\u221E')
                    else:
                        percentage = round(((float)(used)/(float)(quota)) * 100.0, 1)
                        print "%d (Root: %s, Used: %d, Percentage: %d)" % (quota, quota_root, used, percentage)
                else:
                    print "No quota"
            except:
                print "Folder: %s" % (quota_folder)
                print "No quota root"

