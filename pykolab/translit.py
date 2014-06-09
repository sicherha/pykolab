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

import pykolab
from pykolab.translate import _

log = pykolab.getLogger('pykolab.translit')

locale_translit_map = {
        'ru_RU': 'cyrillic'
    }

translit_map = {
        'cyrillic': {
                u'А': 'A',
                u'а': 'a',
                u'Б': 'B',
                u'б': 'b',
                u'В': 'V',
                u'в': 'v',
                u'Г': 'G',
                u'г': 'g',
                u'Д': 'D',
                u'д': 'd',
                u'Е': 'E',
                u'е': 'e',
                u'Ё': 'Yo',
                u'ё': 'e',
                u'Ж': 'Zh',
                u'ж': 'zh',
                u'З': 'Z',
                u'з': 'z',
                u'И': 'I',
                u'и': 'i',
                u'Й': 'J',
                u'й': 'j',
                u'К': 'K',
                u'к': 'k',
                u'Л': 'L',
                u'л': 'l',
                u'М': 'M',
                u'м': 'm',
                u'Н': 'N',
                u'н': 'n',
                u'О': 'O',
                u'о': 'o',
                u'П': 'P',
                u'п': 'p',
                u'Р': 'R',
                u'р': 'r',
                u'С': 'S',
                u'с': 's',
                u'Т': 'T',
                u'т': 't',
                u'У': 'U',
                u'у': 'u',
                u'Ф': 'F',
                u'ф': 'f',
                u'Х': 'Kh',
                u'х': 'kh',
                u'Ц': 'Tc',
                u'ц': 'tc',
                u'Ч': 'Ch',
                u'ч': 'ch',
                u'Ш': 'Sh',
                u'ш': 'sh',
                u'Щ': 'Shch',
                u'щ': 'shch',
                u'Ъ': '',
                u'ъ': '',
                u'Ы': 'Y',
                u'ы': 'y',
                u'Ь': '',
                u'ь': '',
                u'Э': 'E',
                u'э': 'e',
                u'Ю': 'Yu',
                u'ю': 'yu',
                u'Я': 'Ya',
                u'я': 'ya',
            }
    }

def transliterate(_input, lang, _output_expected=None):
    _translit_name = locale_translit_map[lang]

    _output = ''

    if not isinstance(_input, unicode):
        for char in _input.decode('utf-8'):
            if translit_map[_translit_name].has_key(char):
                _output += translit_map[_translit_name][char]
            elif char in [repr(x) for x in translit_map[_translit_name].keys()]:
                _output += translit_map[_translit_name][[char in [raw(x) for x in translit_map[_translit_name].keys()]][0]]
            else:
                _output += char
    else:
        for char in _input:
            if translit_map[_translit_name].has_key(char):
                _output += translit_map[_translit_name][char]
            elif char in [repr(x) for x in translit_map[_translit_name].keys()]:
                _output += translit_map[_translit_name][[char in [raw(x) for x in translit_map[_translit_name].keys()]][0]]
            else:
                _output += char

    return _output

