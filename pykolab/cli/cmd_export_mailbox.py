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

import commands

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('export_mailbox', execute)

def cli_options():
    my_option_group = conf.add_cli_parser_option_group(_("CLI Options"))
    my_option_group.add_option( '--all',
                                dest    = "all",
                                action  = "store_true",
                                default = False,
                                help    = _("All folders this user has access to"))

def execute(*args, **kw):
    import os
    import subprocess

    user = conf.cli_args.pop(0)

    # TODO: /etc/imapd.conf is not the definitive location for the
    # imapd.conf configuration file.
    partition_proc = subprocess.Popen(
            ['grep', '^partition', '/etc/imapd.conf'],
            stdout=subprocess.PIPE
        )

    partitions = [
            x.split(':')[1].strip()
            for x in partition_proc.communicate()[0].split('\n')
            if len(x.split(':')) > 1
        ]

    # TODO: ctl_mboxlist is not necessarily in this location.
    ctl_mboxlist_args = [ '/usr/lib/cyrus-imapd/ctl_mboxlist', '-d' ]
    ctl_mboxlist = subprocess.Popen(
            ctl_mboxlist_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    mboxlist_proc = subprocess.Popen(
            ['grep', '-E', '\s*%s\s*.*i.*p.*' % (user)],
            stdin=ctl_mboxlist.stdout,
            stdout=subprocess.PIPE
        )

    ctl_mboxlist.stdout.close()

    # TODO: Handle errors from ctl_mboxlist process (stderr)
    mboxlist_output = mboxlist_proc.communicate()[0]

    zipper_args = [ 'zip', '-r', '%s.zip' % (user) ]
    directories = []

    for mbox_internal in mboxlist_output.split('\n'):
        if len(mbox_internal.split('\t')[0].split('!')) > 1:
            domain = mbox_internal.split('\t')[0].split('!')[0]
            mailbox = '/'.join(
                    mbox_internal.split(
                            '\t'
                        )[0].split(
                                '!'
                            )[1].split(
                                    '.'
                                )[1:]
                )

            for partition in partitions:
                mbox_dir = '%s/domain/%s/%s/%s/user/%s/' % (
                        partition,
                        domain[0],
                        domain,
                        user[0],
                        mailbox
                    )

                if os.path.isdir(mbox_dir):
                    directories.append(mbox_dir)

                else:
                    log.debug(
                            _('%s is not a directory') % (mbox_dir),
                            level=5
                        )

    if not len(directories) == 0:
        zipper_output = subprocess.Popen(
                zipper_args + directories,
                stdout=subprocess.PIPE
            ).communicate()[0]

        print(_("ZIP file at %s.zip") % (user), file=sys.stderr)
    else:
        print(_("No directories found for user %s") % (user), file=sys.stderr)
        sys.exit(1)

