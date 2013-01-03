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
import re
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
        i.title.string, i.description.string.split('aaa')[0],
        i.find('geo:long').string, i.find('geo:lat').string) for i in soup.findAll("item")]

def _get_timetable(route_code):
    soup =  BeautifulSoup(url_cache.urlopen(_timetable_url % route_code))
    #TODO: parse soup
    return soup

def _get_stop_order(route_code):
    soup = BeautifulSoup(url_cache.urlopen(_stop_order_url % route_code))
    # get stops for going and coming directions
    going = []
    for i in soup.find_all('a', href=re.compile(r".*\byon=G\b.*")):
        href = i['href']
        start = href.find('durak=')+6
        going.append(href[start:href.find('&', start)])

    coming = []
    for i in soup.find_all('a', href=re.compile(r".*\byon=D\b.*")):
        href = i['href']
        start = href.find('durak=')+6
        coming.append(href[start:href.find('&', start)])

    route_name = soup.find("span", class_="kirmizi").string
    #TODO: also get stop names in case they are not on map
    return going, coming, route_name

def generate(filename):
    schedule = transitfeed.Schedule()

    schedule.AddAgency("IETT", "http://www.iett.gov.tr", "Europe/Istanbul")

    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetWeekdayService(True)
    service_period.SetDateHasService('20070704')

    route_codes = _get_route_codes()
    stop_cache = {}
    for route_code in route_codes:
        stops = _get_stops(route_code)
        for stop in stops:
            if not stop[1] in stop_cache.keys():
                stop_cache[stop[1]] = schedule.AddStop(
                    lng=stop[2], lat=stop[3], name=stop[0])

    for route_code in route_codes:
        timetable = _get_timetable(route_code)
        stop_order = _get_stop_order(route_code)

        route = schedule.AddRoute(
            short_name=route_code, long_name=stop_order[2], route_type="Bus")
        trip = route.AddTrip(
            schedule, headsign=stop_cache[stop_order[0][-1]][0])
        for stop_key in stop_order[0]:
            try:
                stop = stop_cache[stop_key]
            except KeyError:
                # ok, lazy iett guys didn't add this stop to the map
                #TODO: try to calculate a possible position between other stops
#                previous_stop = stop_cache[stop_key]
#                stop_cache[stop_key] = schedule.AddStop(
#                    lng=previous_stop.stop_lng, lat=previous_stop.stop_lat, name=stop_key)
#                stop = stop_cache[stop_key]
                continue
            finally:
                trip.AddStopTime(stop, stop_time='09:00:00')
        if stop_order[1]:
            trip = route.AddTrip(
                schedule, headsign=stop_cache[stop_order[1][-1]][0])
        for stop_key in stop_order[1]:
            try:
                stop = stop_cache[stop_key]
            except KeyError:
                #TODO: try to calculate a possible position between other stops
                continue
            finally:
                trip.AddStopTime(stop, stop_time='09:00:00')

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
