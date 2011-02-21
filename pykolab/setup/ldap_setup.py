# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 only
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

import getpass
import logging
import os
import sys

try:
    import ldap
except ImportError, e:
    print >> sys.stderr, _("Cannot load Python LDAP libraries.")

from pykolab.translate import _
from pykolab import constants
from pykolab import utils

def setup():
    """
        Setup LDAP from here.

        # Register with existing LDAP tree?
        #* Verify schema loaded
        #* Forget about flexibility
        # Create new LDAP tree
        #* OpenLDAP
    """

    (service, other_services) = utils.is_service([
            'dirsrv',
            'ldap',
            'slapd'
        ])

    for item in other_services:
        print >> sys.stderr, _("Warning: LDAP Service '%s' is available on " + \
                            "this system as well.") % item

    print _("Found system service %s.") % service

    #ldap_uri = utils.ask_question(_("LDAP URI (read/write)"), "ldap://ldap.%s" %(constants.domainname))
    ldap_uri = utils.ask_question(_("LDAP URI (read/write)"), "ldap://localhost")
    manager_dn = utils.ask_question("Manager DN", "cn=Directory Manager")
    #manager_pw = utils.ask_question("Manager Password", password=True)
    manager_pw = utils.ask_question("Manager Password", "verysecret", password=True)

    try:
        con = ldap.initialize(ldap_uri)
        con.bind(manager_dn, manager_pw, ldap.AUTH_SIMPLE)
    except TypeError:
        # This is a funny input error ("")
        print >> sys.stderr, _("Could not connect to LDAP server due to " + \
                "invalid LDAP URI format or no local socket")
        sys.exit(1)
    except ldap.INVALID_CREDENTIALS, e:
        print >> sys.stderr, _("Your username or password are incorrect")
        sys.exit(1)
    except ldap.LDAPError, e:
        print >> sys.stderr, _("Could not connect to LDAP server due to " + \
                "invalid LDAP URI (or invalid format) or no local socket")
        sys.exit(1)
    except ldap.SERVER_DOWN, e:
        print >> sys.stderr, e['desc']
        sys.exit(1)

    # Returns a list of dicts (empty list if not found)
    kolab_config_dn_results = con.search_s('cn=kolab,cn=config', ldap.SCOPE_SUBTREE, '(cn=kolab)', ['cn'])

    if len(kolab_config_dn_results) == 1:
        print >> sys.stdout, "Success: Found cn=kolab,cn=config"

    else:
        initialize_kolab_config_dn(con)

    #if not service == "":
        #if service in constants.SERVICE_MAP.keys():
            #exec("setup_%s()" % constants.SERVICE_MAP['%s' % service]['type'])
    #else:
        ## No service found on the local system, so ask a bunch of questions.
        ##
        ## - ldap uri
        ## - manager dn
        ## - manager pw
        #pass

def setup_389ds():
    """
        Executes for a local 389 Directory Server installation.
    """

    for (path, directories, files) in os.walk("/etc/dirsrv/"):
        for directory in directories:
            if directory.startswith('slapd-'):
                print "Found a dirsrv instance %r" % directory
                dirsrv_instance = directory

#    if dirsrv_instance == '':
#        # Apparently we're working with a remote dirsrv... are we going to have
#        # to set up the local directory service as well??
#        raise NotImplementedError, _("Initializing a 389 Directory Server has not been implemented yet. Please use setup-ds-admin")
#
#    elif dirsrv_instance == 'slapd-localhost':
#        # The server is on localhost
#        ldap_conn = ldap.initialize(uri="ldap://localhost:389")
#        try:
#            ldap_conn.start_tls_s()
#        except ldap.LDAPError, e:
#            pass
#
#    else:
#        pass

def setup_openldap():
    print "im an openldap system!"


def initialize_kolab_config_dn(ldap_con=None):
    if ldap_con == None:
        return

    ldif = """
dn: cn=kolab,cn=config
cirUpdateSchedule: New
cn: kolab
objectClass: top
objectClass: extensibleobject
"""
