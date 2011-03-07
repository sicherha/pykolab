#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
#
# Paul James Adams <adams a kolabsys.com>
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

import os, random, sys

if __name__ == "__main__":
    wanted_num = int(sys.argv[1])

    contact_tpl_file = open('./kaddress-contact.tpl', 'r')
    contact_tpl_orig = contact_tpl_file.read()
    contact_tpl_file.close()

    users = ['john', 'joe', 'max']
    domains = ['doe.org', 'sixpack.com', 'imum.net']
    uid_alloc = []

    alphabet = "abcdefghijklmnopqrstuvwxwz"

    user_num = 0

    for user in users:
        num = 0
        while num <= wanted_num:
            uid = "%s.%s" %(str(random.randint(1000000000,9999999999)),str(random.randint(0,999)).zfill(3))
            if not uid in uid_alloc:
                uid_alloc.append(uid)
            else:
                continue

            domain = domains[random.randint(0,2)]

            contact_tpl = contact_tpl_orig

            birthday = ""
            if random.randint(0,100) >= 75:
                year = str(random.randint(1960, 2010))
                month = str(random.randint(1,12)).zfill(2)
                day = str(random.randint(1,27)).zfill(2)
                birthday = "%s-%s-%s" % (year, month, day)

            middle_names = ""
            if random.randint(0,100) >= 50:
                middle_names = ''.join(random.sample(alphabet, random.randint(4, 8))).capitalize()

            number = ""
            if random.randint(0,100) >= 25:
                number = "+441234567890"

            given_name = ''.join(random.sample(alphabet, random.randint(4, 8))).capitalize()
            last_name  = ''.join(random.sample(alphabet, random.randint(4, 8))).capitalize()

            contact = {
                'uid': uid,
                'user': user,
                'user_email': "%s@%s" % (user, domain),
                'given_name': given_name,
                'middle_names': middle_names,
                'last_name': last_name,
                'full_name': "%s %s %s" % (given_name, middle_names, last_name),
                'display_name': "%s %s" % (given_name, last_name),
                'email_address': "%s@%s" % (given_name, domain),
                'number': number,
                'birthday': birthday
                }

            directory = "/kolab/var/imapd/spool/domain/%s/%s/%s/user/%s/Contacts" %(domains[user_num][0],domains[user_num],user[0],user)
            if not os.path.isdir(directory):
                directory = "./kolab/var/imapd/spool/domain/%s/%s/%s/user/%s/Contacts" %(domains[user_num][0],domains[user_num],user[0],user)
                if not os.path.isdir(directory):
                    os.makedirs(directory)

            out = open("%s/%d." %(directory,num), 'w')

            for key in contact.keys():
                contact_tpl = contact_tpl.replace("@@%s@@" % key, '%s' % contact[key])

            out.write(contact_tpl)
            out.close()

            try:
                os.chown("%s/%d." %(directory,num), 19415, 19415)
            except:
                pass
            num += 1

        user_num += 1
