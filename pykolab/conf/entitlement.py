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

from ConfigParser import ConfigParser
import hashlib
import OpenSSL
import os
import StringIO
import subprocess
import sys

from pykolab.translate import _

import pykolab
log = pykolab.getLogger('pykolab.conf')

class Entitlement(object):
    def __init__(self, *args, **kw):
        self.entitlement = {}

        self.entitlement_files = []

        ca_cert_file = '/etc/pki/tls/certs/mirror.kolabsys.com.ca.cert'
        customer_cert_file = '/etc/pki/tls/private/mirror.kolabsys.com.client.pem'
        customer_key_file = '/etc/pki/tls/private/mirror.kolabsys.com.client.pem'

        # Licence lock and key verification.
        self.entitlement_verification = [
                'f700660f456a60c92ab2f00d0f1968230920d89829d42aa27d30f678',
                '95783ba5521ea54aa3a32b7949f145aa5015a4c9e92d12b9e4c95c14'
            ]

        if os.access(ca_cert_file, os.R_OK):
            # Verify /etc/kolab/mirror_ca.crt
            ca_cert = OpenSSL.crypto.load_certificate(
                    OpenSSL.SSL.FILETYPE_PEM,
                    open(ca_cert_file).read()
                )

            if (bool)(ca_cert.has_expired()):
                raise Exception, _("Invalid entitlement verification " + \
                        "certificate at %s" % (ca_cert_file))

            # TODO: Check validity and warn ~1-2 months in advance.

            ca_cert_issuer = ca_cert.get_issuer()
            ca_cert_subject = ca_cert.get_subject()

            ca_cert_issuer_hash = subprocess.Popen(
                    [
                            'openssl',
                            'x509',
                            '-in',
                            ca_cert_file,
                            '-noout',
                            '-issuer_hash'
                        ],
                    stdout=subprocess.PIPE
                ).communicate()[0].strip()

            ca_cert_issuer_hash_digest = hashlib.sha224(ca_cert_issuer_hash).hexdigest()

            if not ca_cert_issuer_hash_digest in self.entitlement_verification:
                raise Exception, _("Invalid entitlement verification " + \
                        "certificate at %s") % (ca_cert_file)

            ca_cert_subject_hash = subprocess.Popen(
                    [
                            'openssl',
                            'x509',
                            '-in',
                            ca_cert_file,
                            '-noout',
                            '-subject_hash'
                        ],
                    stdout=subprocess.PIPE
                ).communicate()[0].strip()

            ca_cert_subject_hash_digest = hashlib.sha224(ca_cert_subject_hash).hexdigest()

            if not ca_cert_subject_hash_digest in self.entitlement_verification:
                raise Exception, _("Invalid entitlement verification " + \
                        "certificate at %s") % (ca_cert_file)

            customer_cert_issuer_hash = subprocess.Popen(
                    [
                            'openssl',
                            'x509',
                            '-in',
                            customer_cert_file,
                            '-noout',
                            '-issuer_hash'
                        ],
                    stdout=subprocess.PIPE
                ).communicate()[0].strip()

            customer_cert_issuer_hash_digest = hashlib.sha224(customer_cert_issuer_hash).hexdigest()

            if not customer_cert_issuer_hash_digest in self.entitlement_verification:
                raise Exception, _("Invalid entitlement verification " + \
                        "certificate at %s") % (customer_cert_file)

            if not ca_cert_issuer.countryName == ca_cert_subject.countryName:
                raise Exception, _("Invalid entitlement certificate")

            if not ca_cert_issuer.organizationName == ca_cert_subject.organizationName:
                raise Exception, _("Invalid entitlement certificate")

            if os.path.isdir('/etc/kolab/entitlement.d/') and \
                    os.access('/etc/kolab/entitlement.d/', os.R_OK):

                for root, dirs, files in os.walk('/etc/kolab/entitlement.d/'):
                    if not root == '/etc/kolab/entitlement.d/':
                        continue
                    for entitlement_file in files:
                        log.debug(_("Parsing entitlement file %s") % (entitlement_file), level=8)

                        if os.access(os.path.join(root, entitlement_file), os.R_OK):
                            self.entitlement_files.append(
                                    os.path.join(root, entitlement_file)
                                )

                        else:
                            print >> sys.stderr, \
                                    _("License file %s not readable!") % (
                                            os.path.join(root, entitlement_file)
                                        )

            else:
                print >> sys.stderr, _("No entitlement directory found")

            for entitlement_file in self.entitlement_files:

                decrypt_command = [
                        'openssl',
                        'smime',
                        '-decrypt',
                        '-recip',
                        customer_cert_file,
                        '-in',
                        entitlement_file
                    ]

                decrypt_process = subprocess.Popen(
                        decrypt_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )

                verify_command = [
                        'openssl',
                        'smime',
                        '-verify',
                        '-certfile',
                        ca_cert_file,
                        '-CAfile',
                        ca_cert_file,
                        '-inform',
                        'DER'
                    ]

                verify_process = subprocess.Popen(
                        verify_command,
                        stdin=decrypt_process.stdout,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )

                (stdout, stderr) = verify_process.communicate()
                license = License(stdout, self.entitlement)
                license.verify_certificate(customer_cert_file)
                self.entitlement = license.get()

        else:
            print "Error reading entitlement certificate authority file"

    def get(self):
        if len(self.entitlement.keys()) == 0:
            return None
        else:
            return self.entitlement

class License(object):
    entitlement = {}

    def __init__(self, new_entitlement, existing_entitlement):
        self.parser = ConfigParser()
        fp = StringIO.StringIO(new_entitlement)
        self.parser.readfp(fp)

        self.entitlement['users'] = self.parser.get('kolab_entitlements', 'users')
        self.entitlement['margin'] = self.parser.get('kolab_entitlements', 'margin')

    def verify_certificate(self, customer_cert_file):
        # Verify the certificate section as well.
        cert_serial = self.parser.get('mirror_ca', 'serial_number')
        cert_issuer_hash = self.parser.get('mirror_ca', 'issuer_hash')
        cert_subject_hash = self.parser.get('mirror_ca', 'subject_hash')

        customer_cert_serial = subprocess.Popen(
                [
                        'openssl',
                        'x509',
                        '-in',
                        customer_cert_file,
                        '-noout',
                        '-serial'
                    ],
                stdout=subprocess.PIPE
            ).communicate()[0].strip().split('=')[1]

        if not customer_cert_serial == cert_serial:
            raise Exception, _("Invalid entitlement verification " + \
                    "certificate at %s") % (customer_cert_file)

        customer_cert_issuer_hash = subprocess.Popen(
                [
                        'openssl',
                        'x509',
                        '-in',
                        customer_cert_file,
                        '-noout',
                        '-issuer_hash'
                    ],
                stdout=subprocess.PIPE
            ).communicate()[0].strip()

        if not customer_cert_issuer_hash == cert_issuer_hash:
            raise Exception, _("Invalid entitlement verification " + \
                    "certificate at %s") % (customer_cert_file)

        customer_cert_subject_hash = subprocess.Popen(
                [
                        'openssl',
                        'x509',
                        '-in',
                        customer_cert_file,
                        '-noout',
                        '-subject_hash'
                    ],
                stdout=subprocess.PIPE
            ).communicate()[0].strip()

        if not customer_cert_subject_hash == cert_subject_hash:
            raise Exception, _("Invalid entitlement verification " + \
                    "certificate at %s") % (customer_cert_file)

    def get(self):
        return self.entitlement
