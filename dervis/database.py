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
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Stop(Base):
    __tablename__ = 'stops'

    id = Column(String, primary_key=True)
    name = Column(String)
    lat = Column(String)
    lng = Column(String)

    def __init__(self, id, name, lat, lng):
        self.id, self.name, self.lat, self.lng = id, name, lat, lng

    def __repr__(self):
        return "<Stop('%s')>" % self.name
