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

try:
    from pykolab.constants import domain
except ImportError:
    domain = 'pykolab'

import gettext
import os

N_ = lambda x: x
_ = lambda x: current.lgettext(x)

localedir = '/usr/local/share/locale'
current = gettext.translation(domain, localedir, fallback=True)

def getDefaultLangs():
    languages = []
    for envar in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        val = os.environ.get(envar)
        if val:
            languages = val.split(':')
            break
    if 'C' not in languages:
        languages.append('C')

    # now normalize and expand the languages
    nelangs = []
    for lang in languages:
        for nelang in gettext._expand_lang(lang):
            if nelang not in nelangs:
                nelangs.append(nelang)
    return nelangs

def setUserLanguage(lang):
    global current

    langs = []
    for l in gettext._expand_lang(lang):
        if l not in langs:
            langs.append(l)

    try:
        current = gettext.translation(domain, localedir, languages=langs, fallback=True)
    except:
        pass
