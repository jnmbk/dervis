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
from multiprocessing import Pool
import re
from bs4 import BeautifulSoup
from pyproj import Proj, transform
import requests
import requests_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dervis.database import Base, Stop


requests_cache.install_cache('dervis')
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.22'
                  ' (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.22',
}

_base_url = "http://harita.iett.gov.tr/yeni"
_timetable_url = _base_url + "/saat.php?hat=%s"
_stop_url = _base_url + "/geoRss.php3?hat=%s"
_stop_order_url = _base_url + "/hat_sorgula_v3.php3?sorgu=durak&hat=%s"

# note that I can also get current bus locations from:
# "/XML/%sotod.xml" and "/XML/%sotog.xml" (g:gidiş d:dönüş)
# also this one gives predicted arrival per stop, which I can calculate from
# the data collected from above links doing:
# start_time + (tatal_route_time/2/total_route_length
# *route_length_from_start_to_this_stop)
# "/durak_saat_v3.php3?sorgu=saat&hat=%s&durak=A0083&yon=G"

def _get_route_codes():
    soup = BeautifulSoup(requests.get("http://harita.iett.gov.tr/yeni/", headers=headers).text)
    return [i["value"] for i in soup.find(id="hat").findAll("option")[1:]]

projection = Proj(init="EPSG:3857")
def _convert_to_real_lat_lng(lng, lat):
    return projection(lng, lat, inverse=True)

def _get_stops(route_code):
    soup = BeautifulSoup(requests.get(_stop_url % route_code, headers=headers).text)
    return [(
        i.title.text, i.description.string.split('aaa')[0],
        _convert_to_real_lat_lng(i.find('geo:long').text,
        i.find('geo:lat').text)) for i in soup.findAll("item")]

def _get_timetable(route_code):
    soup = BeautifulSoup(requests.get(_timetable_url % route_code, headers=headers).text)
    try:
        name = soup.b.text
        duration = [int(s) for s in soup.center.text.split() if s.isdigit()][-1]
    except AttributeError:
        name = ''
    except IndexError:
        # iett has no duration defined for this route,
        # probably there is no data as well
        duration = "0"

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
    soup = BeautifulSoup(requests.get(_stop_order_url % route_code, headers=headers).text)
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

    route_name = soup.find("span", class_="kirmizi").text.strip()
    #TODO: also get stop names in case they are not on map
    return going, coming, route_name


def generate(filename, route_limit=1000):
    engine = create_engine('sqlite:///%s' % filename, echo=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    route_codes = _get_route_codes()[:route_limit]
    pool = Pool()
    stops_list = pool.map(_get_stops, route_codes)

    stop_cache = {}
    for route_code, stops in zip(route_codes, stops_list):
        for stop in stops:
            if not stop[1] in stop_cache.keys():
                stop_cache[stop[1].replace(u'Ş', "S:").replace(u'İ', "I:")] = Stop(
                    stop[1], stop[0], stop[2][1], stop[2][0])

    session.add_all(stop_cache.values())
    session.commit()

    # timetable_list = pool.map(_get_timetable, route_codes)
    # stop_order_list = pool.map(_get_stop_order, route_codes)
    # for route_code, timetable, stop_order in zip(route_codes, timetable_list, stop_order_list):
    #     if not stop_order[0]:
    #         #that route doesn't have any stops!
    #         continue
    #     route = schedule.AddRoute(
    #         short_name=route_code, long_name=stop_order[2], route_type="Bus")
    #     trip = route.AddTrip(
    #         schedule, headsign=stop_cache[stop_order[0][-1]][0])
    #
    #     for order, stop_key in enumerate(stop_order[0]):
    #         if order == 0:
    #             try:
    #                 stop = stop_cache[stop_key]
    #             except KeyError:
    #                 # ok, lazy iett guys didn't add this stop to the map
    #                 #TODO: try to calculate a possible position between other stops
    # #                previous_stop = stop_cache[stop_key]
    # #                stop_cache[stop_key] = schedule.AddStop(
    # #                    lng=previous_stop.stop_lng, lat=previous_stop.stop_lat, name=stop_key)
    # #                stop = stop_cache[stop_key]
    #                 continue
    #             finally:
    #                 for time in timetable[0]:
    #                     trip.AddStopTime(stop, stop_time=time)
    #     if stop_order[1] and stop_cache.has_key(stop_order[1][-1]):
    #         trip = route.AddTrip(
    #             schedule, headsign=stop_cache[stop_order[1][-1]][0])
    #         for order, stop_key in enumerate(stop_order[1]):
    #             if order==0:
    #                 try:
    #                     stop = stop_cache[stop_key]
    #                 except KeyError:
    #                     #TODO: try to calculate a possible position between other stops
    #                     continue
    #                 finally:
    #                     for time in timetable[1]:
    #                         trip.AddStopTime(stop, stop_time=time)
