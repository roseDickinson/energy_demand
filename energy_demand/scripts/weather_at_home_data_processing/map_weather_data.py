"""
Get a the closest weather@home grid cell data for an input list of coordinates
"""
import os
import pandas as pd
from haversine import haversine

from energy_demand.basic import basic_functions

def spatially_map_data(
        path_results,
        path_weather_at_home_stations,
        path_input_coordinates,
        scenarios
    ):
    scenario_names = ["NF{}".format(i) for i in range(1, 101)]

    # Path to scenarios
    path_to_scenario_data = os.path.join(path_results, '_realizations')
    result_out_path = os.path.join(path_results, '_spatially_mapped_realizations')
    basic_functions.create_folder(result_out_path)

    # Read in input stations and coordinages to map
    stations_to_map_to = pd.read_csv(path_input_coordinates)

    # Append new columns
    stations_to_map_to['value'] = 0
    stations_to_map_to['parameter'] = 0
    stations_to_map_to['scenario'] = 0
    stations_to_map_to['year'] = 0

    # Read in MARIUS grid weather stations
    print("... read in weather stations per attribute", flush=True)
    attributes = ['wss', 'rsds']
    weather_stations_per_attribute = {}
    for attribute in attributes:
        path_station = os.path.join(path_weather_at_home_stations, "stations_{}.csv".format(attribute))
        stations_grid_cells = pd.read_csv(path_station)
        stations_grid_cells = stations_grid_cells.set_index('station_id')

        # Convert into dict
        stations_grid_cells_dict = {}
        for index in stations_grid_cells.index:
            stations_grid_cells_dict[index] = {
                'longitude': stations_grid_cells.loc[index, 'longitude'],
                'latitude': stations_grid_cells.loc[index, 'latitude']
            }

        weather_stations_per_attribute[attribute] = stations_grid_cells_dict

    # Iterate geography and assign closest weather station data
    closest_weather_ids = {}
    for index in stations_to_map_to.index:

        closest_weather_ids[index] = {}

        # Marius weather station
        station_lat = stations_to_map_to.loc[index, 'Latitude']
        station_lon = stations_to_map_to.loc[index, 'Longitude']

        data_types = [('wind', 'wss'), ('insulation', 'rsds')]

        for name_attribute, attribute in data_types:

            # Get closest Met Office weather station
            closest_marius_station = get_closest_weather_station(
                latitude_reg=station_lat,
                longitude_reg=station_lon,
                weather_stations=weather_stations_per_attribute[attribute])

            closest_weather_ids[index][name_attribute] = closest_marius_station

    # Weather and solar data for all scenarios
    for scenario_nr in scenarios: #range(100):
        scenario_name = scenario_names[scenario_nr]
        print("... {} ".format(scenario_name), flush=True)

        for name_attribute, attribute in data_types:
            print("    ... {} ".format(name_attribute), flush=True)
            path_data = os.path.join(path_to_scenario_data, "weather_data_{}__{}.csv".format(scenario_name, attribute))
            data = pd.read_csv(path_data)

            for index in stations_to_map_to.index:
                print("        ... {} ".format(index), flush=True)
                closest_weather_station_id = closest_weather_ids[index][name_attribute]
                closest_data = data.loc[closest_weather_station_id]

                #region_id, Latitude, Longitude, region_name, scenario, parameter, value
                stations_to_map_to.loc[index, 'scenario'] = scenario_nr
                stations_to_map_to.loc[index, 'parameter'] = attribute
                stations_to_map_to.loc[index, 'value'] = closest_data

    # ----------------------------------------------------------
    # Write out data
    # ----------------------------------------------------------
    df = pd.DataFrame(stations_to_map_to, columns=['station_id', 'latitude', 'longitude'])
    result_file = os.path.join(result_out_path,  "remapped_and_append_weather_data.csv")
    stations_to_map_to.to_csv(result_file, index=False)


def calc_distance_two_points(lat_from, long_from, lat_to, long_to):
    """Calculate distance between two points

    https://pypi.org/project/haversine/#description

    Arguments
    ----------
    long_from : float
        Longitute coordinate from point
    lat_from : float
        Latitute coordinate from point
    long_to : float
        Longitute coordinate to point
    lat_to : float
        Latitue coordinate to point

    Return
    ------
    distance : float
        Distance
    """
    distance_in_km = haversine(
        (lat_from, long_from),
        (lat_to, long_to),
        unit='km')

    return distance_in_km

def get_closest_weather_station(
        latitude_reg,
        longitude_reg,
        weather_stations
    ):
    """
    """
    closest_dist = 99999999999

    for station_id in weather_stations:
        lat_to = weather_stations[station_id]["latitude"]
        long_to = weather_stations[station_id]["longitude"]

        dist_to_station = calc_distance_two_points(
            lat_from=latitude_reg,
            long_from=longitude_reg,
            lat_to=lat_to,
            long_to=long_to)

        if dist_to_station < closest_dist:
            closest_dist = dist_to_station
            closest_id = station_id

    return closest_id
