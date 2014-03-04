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

import os
import tempfile
import time

from email import message_from_string
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.parser import Parser
from email.utils import formataddr
from email.utils import getaddresses

import modules

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/gpgencrypt/'

def __init__():
    modules.register('gpgencrypt', execute, description=description())

def description():
    return """Encrypt messages to the recipient(s)."""

def execute(*args, **kw):
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT' ]:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    # TODO: Test for correct call.
    filepath = args[0]

    if kw.has_key('stage'):
        log.debug(_("Issuing callback after processing to stage %s") % (kw['stage']), level=8)
        log.debug(_("Testing cb_action_%s()") % (kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' % (kw['stage'])):
            log.debug(_("Attempting to execute cb_action_%s()") % (kw['stage']), level=8)
            exec('modules.cb_action_%s(%r, %r)' % (kw['stage'],'gpgencrypt',filepath))

    log.debug(_("Executing module gpgencrypt for %r, %r") % (args, kw), level=8)

    new_filepath = os.path.join('/var/spool/pykolab/wallace/gpgencrypt/incoming', os.path.basename(filepath))

    if not filepath == new_filepath:
        log.debug("Renaming %r to %r" % (filepath, new_filepath))
        os.rename(filepath, new_filepath)
        filepath = new_filepath

    # parse message headers
    # @TODO: make sure we can use True as the 2nd argument here
    message = Parser().parse(open(filepath, 'r'), True)

    # Possible gpgencrypt answers are limited to ACCEPT only
    answers = [ 'ACCEPT' ]

# from Mail::GnuPG.is_encrypted
# 
#sub is_encrypted {
#  my ($self,$entity) = @_;
#  return 1
#    if (($entity->effective_type =~ m!multipart/encrypted!)
#    ||
#    ($entity->as_string =~ m!^-----BEGIN PGP MESSAGE-----!m));
#  return 0;
#}

    message_already_encrypted = False

    for part in message.walk():
        if part.get_content_type() in [ "application/pgp-encrypted" ]:
            message_already_encrypted = True
            log.debug(_("Message is already encrypted (app/pgp-enc content-type)"), level=8)

    if message.get_content_type() in [ "multipart/encrypted" ]:
        message_already_encrypted = True
        log.debug(_("Message already encrypted by main content-type header"), level=8)

    if message_already_encrypted:
        return filepath

    try:
        # What are recipient addresses to encrypt to (bitmask)?
        # 1 - organization key
        # 2 - envelope to
        # 4 - to
        # 8 - cc
        # 16 - resent-to
        # 32 - resent-cc
        encrypt_to_rcpts = conf.get('wallace', 'gpgencrypt_to_rcpts')
        if encrypt_to_rcpts == None:
            encrypt_to_rcpts = 14
        else:
            encrypt_to_rcpts = (int)(encrypt_to_rcpts)

        # Only encrypt to keys that are trusted
        strict_crypt = conf.get('wallace', 'gpgencrypt_strict')
        if strict_crypt == None:
            strict_crypt = False

        # Organization key ID
        if encrypt_to_rcpts & 1:
            encrypt_to_org = conf.get('wallace', 'gpgencrypt_to_org_key')
            if encrypt_to_org == None and encrypt_to_rcpts & 1:
                if strict_crypt:
                    log.error(_("Configured to encrypt to a key not configured, and strict policy enabled. Bailing out."))
                    modules.cb_action_REJECT('gpgencrypt',filepath)
                else:
                    log.error(_("Configured to encrypt to a key not configured, but continuing anyway (see 'gpgencrypt_strict')."))
        else:
            encrypt_to_org = []

        # Bounce the message if encryption fails?
        force_crypt = conf.get('wallace', 'gpgencrypt_force')
        if force_crypt == None:
            force_crypt = False

        # Retrieve keys from remote server(s) automatically?
        retrieve_keys = conf.get('wallace', 'gpgencrypt_retrieve_keys')
        if retrieve_keys == None:
            retrieve_keys = False

        if retrieve_keys:
            gpgserver = conf.get('wallace', 'gpgencrypt_server')
            if gpgserver == None:
                gpgserver = 'pgp.mit.edu'

        encrypt_to = []
        if encrypt_to_rcpts & 2:
            encrypt_to.extend(message.get_all('X-Kolab-To', []))

        if encrypt_to_rcpts & 4:
            encrypt_to.extend(message.get_all('to', []))

        if encrypt_to_rcpts & 8:
            encrypt_to.extend(message.get_all('cc', []))

        if encrypt_to_rcpts & 16:
            encrypt_to.extend(message.get_all('resent-to', []))

        if encrypt_to_rcpts & 32:
            encrypt_to.extend(message.get_all('resent-cc', []))

        recipients = [address for displayname,address in getaddresses(encrypt_to)]

        log.debug(_("Recipients: %r") % (recipients))

        # Split between recipients we can encrypt for/to, and ones we can not
        encrypt_rcpts = []
        nocrypt_rcpts = []


        import gnupg
        gpg = gnupg.GPG(gnupghome='/var/lib/kolab/.gnupg', verbose=conf.debuglevel > 8)
        gpg.encoding = 'utf-8'

        local_keys = gpg.list_keys()
        log.debug(_("Current keys: %r") % (local_keys), level=8)

        for recipient in recipients:
            key_local = False

            log.debug(_("Retrieving key for recipient: %r") % (recipient))

            for key in local_keys:
                for address in [x for x in [address for displayname,address in getaddresses(key['uids'])] if x == recipient]:
                    log.debug(_("Found matching address %r") % (address))
                    key_local = key['keyid']

            if key_local == False:
                if retrieve_keys:
                    remote_keys = gpg.search_keys(recipient, gpgserver)
                    if len(remote_keys) == 1:
                        for address in [x for x in [address for displayname,address in getaddresses(remote_keys[0]['uids'])] if x == recipient]:
                            log.debug(_("Found matching address %r in remote keys") % (address))
                            gpg.recv_keys(gpgserver, remote_keys[0]['keyid'])
                            local_keys = gpg.list_keys()
                    else:
                        nocrypt_rcpts.append(recipient)

            for key in local_keys:
                for address in [x for x in [address for displayname,address in getaddresses(key['uids'])] if x == recipient]:
                    log.debug(_("Found matching address %r") % (address))
                    key_local = key['keyid']
            if not key_local == False:
                encrypt_rcpts.append(key_local)

        payload = message.get_payload()
        print "payload:", payload
        if len(encrypt_rcpts) < 1:
            return filepath

        encrypted_data = gpg.encrypt(payload, encrypt_rcpts, always_trust=True)
        encrypted_string = str(encrypted_data)

        print "encrypted string:", encrypted_string

        message.set_payload(encrypted_string)

        (fp, new_filepath) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/gpgencrypt/ACCEPT")
        os.write(fp, message.as_string())
        os.close(fp)
        os.unlink(filepath)

        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','gpgencrypt', new_filepath))
    except Exception, errmsg:
        log.error(_("An error occurred: %r") % (errmsg))
        if conf.debuglevel > 8:
            import traceback
            traceback.print_exc()
