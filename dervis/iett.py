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
    try:
        name = soup.b.text
    except AttributeError:
        name = ''
    duration = [int(s) for s in soup.center.text.split() if s.isdigit()][-1]

    weekdays_g=[]
    weekdays_d=[]
    sat_g=[]
    sat_d=[]
    sun_g=[]
    sun_d=[]

    for times in soup.find_all("tr")[4:]:
        for counter, time in enumerate(times.find_all("td")):
            text = time.text.strip()
            if text:
                i = text.find(':')
                text = text[i-2:i+3] + ":00"
                if counter == 0: weekdays_g.append(text)
                if counter == 1: weekdays_d.append(text)
                if counter == 2: sat_g.append(text)
                if counter == 3: sat_d.append(text)
                if counter == 4: sun_g.append(text)
                if counter == 5: sun_d.append(text)

    #recalculate hours, they should be like 23, 24, 25...
    for i in range(len(weekdays_d) - 1):
        if weekdays_d[i] > weekdays_d[i+1]:
            hour = int(weekdays_d[i+1][:2]) + 24
            weekdays_d[i+1] = str(hour) + weekdays_d[i+1][2:]

    for i in range(len(weekdays_g) - 1):
        if weekdays_g[i] > weekdays_g[i + 1]:
            hour = int(weekdays_g[i + 1][:2]) + 24
            weekdays_g[i + 1] = str(hour) + weekdays_g[i + 1][2:]

    return weekdays_d, weekdays_g, sat_d, sat_g, sun_d, sun_g, name, duration

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
    service_period.SetStartDate('20130101')
    service_period.SetEndDate('20131231')

    route_codes = _get_route_codes()
    stop_cache = {}
    for route_code in route_codes:
        stops = _get_stops(route_code)
        for stop in stops:
            if not stop[1] in stop_cache.keys():
                stop_cache[stop[1].replace(u'Ş', "S:").replace(u'İ', "I:")] = schedule.AddStop(
                    lng=stop[2], lat=stop[3], name=stop[0])

    for route_code in route_codes:
        timetable = _get_timetable(route_code)
        stop_order = _get_stop_order(route_code)

        route = schedule.AddRoute(
            short_name=route_code, long_name=stop_order[2], route_type="Bus")
        trip = route.AddTrip(
            schedule, headsign=stop_cache[stop_order[0][-1]][0])

        for order, stop_key in enumerate(stop_order[0]):
            if order == 0:
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
                    for time in timetable[0]:
                        trip.AddStopTime(stop, stop_time=time)
        if stop_order[1]:
            trip = route.AddTrip(
                schedule, headsign=stop_cache[stop_order[1][-1]][0])
        for order, stop_key in enumerate(stop_order[1]):
            if order==0:
                try:
                    stop = stop_cache[stop_key]
                except KeyError:
                    #TODO: try to calculate a possible position between other stops
                    continue
                finally:
                    for time in timetable[1]:
                        trip.AddStopTime(stop, stop_time=time)

    schedule.Validate()
    schedule.WriteGoogleTransitFeed(filename)
