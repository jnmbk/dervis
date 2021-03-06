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
from dervis import iett


class TestGtfsGenerators(unittest.TestCase):
    test_file = "test.sqlite3"

    def test_generate_iett(self):
        iett.generate(self.test_file, 20)

if __name__ == "__main__":
    unittest.main()
