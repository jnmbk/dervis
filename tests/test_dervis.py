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
from StringIO import StringIO
from time import sleep
import os
import unittest
import requests
from dervis import iett, url_cache


class TestGtfsGenerators(unittest.TestCase):
    test_file = "test.zip"

    def test_generate_iett(self):
        iett.generate(self.test_file)
        self.assertTrue(os.path.exists(self.test_file))
        os.remove(self.test_file)

class TestUrllibCache(unittest.TestCase):
    test_url = 'https://raw.github.com/jnmbk/dervis/master/README.md'

    @property
    def cache_file(self):
        return url_cache.get_cache_file_name(self.test_url)

    def test_clear_cache(self):
        url_cache.urlopen(self.test_url)
        self.assertTrue(os.path.exists(
            url_cache.get_cache_file_name(self.test_url)))
        url_cache.urlopen(self.test_url)
        url_cache.clear(self.test_url)
        self.assertFalse(os.path.exists(self.cache_file))

    def test_cache_read(self):
        url_cache.clear(self.test_url)
        content = requests.get(self.test_url).content
        # second iteration hits cache
        for i in range(2):
            cached_content = url_cache.urlopen(self.test_url).read()
            self.assertEqual(cached_content, content)
        url_cache.clear(self.test_url)

    def test_cache_write(self):
        #make sure we don't write to cache when it is already available
        url_cache.urlopen(self.test_url)

        # let's change file content now
        open(self.cache_file, 'w').write(self.test_url)

        #this should do nothing since file exists
        url_cache.urlopen(self.test_url)
        self.assertEqual(open(self.cache_file).read(), self.test_url)

if __name__ == "__main__":
    unittest.main()
