# -*- coding: utf-8 -*-
"""
Copyright (C) 2013  Uğur Çetin

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>
"""
import hashlib
import os
import requests

project_base = os.path.realpath(os.path.dirname(__file__)).rsplit(os.sep, 1)[0]
cache_dir = os.path.join(project_base, ".cache")

def get_cache_file_name(url):
    return os.path.join(cache_dir, hashlib.sha1(url).hexdigest())

def clear(url):
    file_name = get_cache_file_name(url)
    if os.path.exists(file_name):
        os.remove(file_name)

def urlopen(url):
    """fetches given url if not present in cache url content must be text"""
    file_name = get_cache_file_name(url)
    try:
        handle = open(file_name, 'r')
    except IOError:
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        handle = open(file_name, 'w')
        handle.write(requests.get(url).content)
        handle = open(file_name, 'r')
    return handle
