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
from bs4 import BeautifulSoup
import transitfeed
from dervis import url_cache

_base_url = "http://harita.iett.gov.tr"
_timetable_url = _base_url + "/saat.php?hat=%s"
_stop_url = _base_url + "/XML/%shatDurak.xml"
_stop_order_url = _base_url + "/hat_sorgula_v3.php3?sorgu=durak&hat=%s"

# note that I can also get current bus locations from:
# "/XML/%sotod.xml" and "/XML/%sotog.xml" (g:gidiş d:dönüş)
# also this one gives predicted arrival per stop, which I can calculate from
# the data collected from above links doing:
# start_time + (tatal_route_time/2/total_route_length
# *route_length_from_start_to_this_stop)
# "/durak_saat_v3.php3?sorgu=saat&hat=%s&durak=A0083&yon=G"

def _get_route_codes():
    soup = BeautifulSoup(url_cache.urlopen(_base_url))
    return [i["value"] for i in soup.find(id="hat").findAll("option")[1:]]

def _get_stops(route_code):
    soup =  BeautifulSoup(url_cache.urlopen(_stop_url % route_code))
    return [(
        i.title.string, i.description.string,
        i.find('geo:long').string, i.find('geo:lat').string) for i in soup.findAll("item")]

def _get_timetable(route_code):
    soup =  BeautifulSoup(url_cache.urlopen(_timetable_url % route_code))
    #TODO: parse soup
    return soup

def _get_stop_order(route_code):
    soup = BeautifulSoup(url_cache.urlopen(_stop_order_url % route_code))
    #TODO: parse soup
    return soup

def generate(filename):
    schedule = transitfeed.Schedule()

    schedule.AddAgency("IETT", "http://www.iett.gov.tr", "Europe/Istanbul")

    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetWeekdayService(True)
    service_period.SetDateHasService('20070704')

    route_codes = _get_route_codes()
    stop_cache = []
    for route_code in route_codes:
        stops = _get_stops(route_code)
        for stop in stops:
            stop_key = stop[2] + stop[3]
            if not stop_key in stop_cache:
                stop_cache.append(stop_key)
                schedule.AddStop(lng=stop[2], lat=stop[3], name=stop[0])

        timetable = _get_timetable(route_code)
        stop_order = _get_stop_order(route_code)

    stop1 = schedule.AddStop(lng=-122, lat=37.2, name="Suburbia")
    stop2 = schedule.AddStop(lng=-122.001, lat=37.201, name="Civic Center")

    route = schedule.AddRoute(short_name="22", long_name="Civic Center Express",
        route_type="Bus")

    trip = route.AddTrip(schedule, headsign="To Downtown")
    trip.AddStopTime(stop1, stop_time='09:00:00')
    trip.AddStopTime(stop2, stop_time='09:15:00')

    trip = route.AddTrip(schedule, headsign="To Suburbia")
    trip.AddStopTime(stop1, stop_time='17:30:00')
    trip.AddStopTime(stop2, stop_time='17:45:00')

    schedule.Validate()
    schedule.WriteGoogleTransitFeed(filename)
