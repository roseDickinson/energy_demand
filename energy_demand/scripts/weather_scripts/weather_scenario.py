"""Script to prepare weather data
Load weather simulation data

1. Download yearly data from here: http://catalogue.ceda.ac.uk/uuid/0cea8d7aca57427fae92241348ae9b03

2. Extract data

3. Run this script to get only the relevant data

Links
------
http://data.ceda.ac.uk//badc//weather_at_home/data/marius_time_series/CEDA_MaRIUS_Climate_Data_Description.pdf
http://data.ceda.ac.uk/badc/weather_at_home/data/marius_time_series/near_future/data/
"""
import os
import pytemperature
import xarray as xr
import numpy as np
import pandas as pd

from energy_demand.basic import basic_functions
from energy_demand.read_write import write_data

def create_realisation(
        realisation_nrs,
        realisation_path,
        realisation_out_path,
        path_stiching_table
    ):
    """
    """
    # Create result path
    basic_functions.create_folder(realisation_out_path)

    # Read in stiching table
    df_path_stiching_table = pd.read_table(path_stiching_table, sep=" ")
    
    # Set year as index
    df_path_stiching_table = df_path_stiching_table.set_index('year')

    # Realisations
    realisations = list(df_path_stiching_table.columns)

    columns = ['timestep', 'station_id', 'stiching_name', 'yearday', 't_min', 't_max',]

    for i in range(realisation_nrs):

        realisation = realisations[i]

        realisation_out = []
        
        for year in range(2020, 2050):
            stiching_name = df_path_stiching_table[realisation][year]

            # If year 2015 - 2019, take base year weather

            path_weather_data = os.path.join(realisation_path, str(year), stiching_name)
    
            # Read t_min, t_max, stations)
            t_min = np.load(os.path.join(path_weather_data, "t_min.npy"))
            t_max = np.load(os.path.join(path_weather_data, "t_max.npy"))
            stations = pd.read_csv(os.path.join(path_weather_data, "stations.csv"))

            for station_cnt, station_id in enumerate(stations):
                t_min_station = t_min[station_cnt]
                t_max_station = t_max[station_cnt]
                for yearday in range(365):
                    realisation_out.append(
                        [year, station_id, stiching_name, yearday, t_min_station[yearday], t_max_station[yearday]])

        # Write_to_csv
        df = pd.DataFrame(realisation_out, columns=columns)
        path_out_csv = os.path.join(realisation_out_path, "weather_data_{}".format(realisation))
        df.to_csv(path_out_csv, index=False)


    pass

def get_temp_data_from_nc(path_nc_file, attribute_to_keep):
    """Open c file, convert it into dataframe,
    clean it and extract attribute data
    """
    # Open as xarray
    x_array_data = xr.open_dataset(path_nc_file)

    # Convert to dataframe
    df = x_array_data.to_dataframe()

    # Add index as columns
    df = df.reset_index()

    # Drop unnecessary columns
    df = df.drop(['time_bnds', 'rotated_latitude_longitude', 'rlat', 'rlon', 'bnds', 'height'], axis=1)

    # Drop all missing value
    df = df.dropna(subset=[attribute_to_keep])

    return df

def convert_to_celcius(df, attribute_to_convert):
    """# Convert Kelvin to Celsius (# Kelvin to Celsius)
    """
    df[attribute_to_convert] = df[attribute_to_convert].apply(pytemperature.k2c)
    return df

def extend_360_day_to_365(df, attribute):
    """Add evenly distributed days across the 360 days

    Return
    ------
    out_list : list
        Returns list with days with the following attributes
        e.g. [[lat, long, yearday365, value]]
    """
    # Copy the following position of day in the 360 year
    days_to_duplicate = [60, 120, 180, 240, 300]
    out_list = []

    # Copy every 60th day over the year and duplicate it. Do this five times --> get from 360 to 365 days
    day_cnt, day_cnt_365 = 0, 0
    for i in df.index:
        day_cnt += 1

        latitude = df.get_value(i,'lat')
        longitude = df.get_value(i,'lon')
        value = df.get_value(i, attribute)

        # Copy extra day
        if day_cnt in days_to_duplicate:
            out_list.append([latitude, longitude, day_cnt_365, value])
            day_cnt_365 += 1

        # Copy day
        day_cnt_365 += 1
        out_list.append([latitude, longitude, day_cnt_365, value])

        # Reset counter if next weather station
        if day_cnt == 360:
            day_cnt = 0
            day_cnt_365 = 0

    return out_list

def write_weather_data(data_list):
    """Write weather data to array
    data_list : list
        [[lat, long, yearday365, value]]
    """
    station_coordinates = []

    assert not len(data_list) % 365 #Check if dividable by 365
    nr_stations = int(len(data_list) / 365)

    stations_data = np.zeros((nr_stations, 365))
    station_data = np.zeros((365))

    station_id_cnt = 0
    cnt = 0

    for row in data_list:
        station_data[cnt] = row[3]

        if cnt == 364:

            # 365 day data for weather station
            stations_data[station_id_cnt] = station_data

            # Weather station metadata
            station_lon = row[1]
            station_lat = row[0]

            station_id = "station_id_{}".format(station_id_cnt)

            #ID, latitude, longitude
            station_coordinates.append([station_id, station_lat, station_lon])

            # Reset
            station_data = np.zeros((365))
            station_id_cnt += 1
            cnt = -1
        cnt += 1

    return station_coordinates, stations_data

def weather_dat_prepare(data_path, result_path, years_to_clean=range(2020, 2049)):
    """
    """
    print("folder_name " + str(years_to_clean))

    # Create reulst folders
    result_folder = os.path.join(result_path, "_weather_data_cleaned")
    basic_functions.create_folder(result_folder)

    for folder_name in years_to_clean:

        year = folder_name

        # Create folder
        path_year = os.path.join(result_folder, str(year))
        basic_functions.create_folder(path_year)

        path_realizations = os.path.join(path, str(year))
        realization_names = os.listdir(path_realizations)

        for realization_name in realization_names:
            print("... processing {}  {}".format(str(year), str(realization_name)), flush=True)

            # Create folder
            path_realization = os.path.join(path_year, realization_name)
            basic_functions.create_folder(path_realization)
            
            # Data to extract
            path_tasmin = os.path.join(path_realizations, realization_name, 'daily', 'WAH_{}_tasmin_daily_g2_{}.nc'.format(realization_name, year))
            path_tasmax = os.path.join(path_realizations, realization_name, 'daily', 'WAH_{}_tasmax_daily_g2_{}.nc'.format(realization_name, year))
            
            # Load data
            print("     ..load data", flush=True)
            df_min = get_temp_data_from_nc(path_tasmin, 'tasmin')
            df_max = get_temp_data_from_nc(path_tasmax, 'tasmax')

            # Convert Kelvin to Celsius (# Kelvin to Celsius)
            print("     ..convert temp", flush=True)
            df_min = convert_to_celcius(df_min, 'tasmin')
            df_max = convert_to_celcius(df_max, 'tasmax')

            # Convert 360 day to 365 days
            print("     ..extend day", flush=True)
            list_min = extend_360_day_to_365(df_min, 'tasmin')
            list_max = extend_360_day_to_365(df_max, 'tasmax')

            # Write out single weather stations as numpy array
            print("     ..write out", flush=True)
            station_coordinates, stations_t_min = write_weather_data(list_min)
            station_coordinates, stations_t_max = write_weather_data(list_max)

            # Write to csv
            np.save(os.path.join(path_realization, "t_min.npy"), stations_t_min)
            np.save(os.path.join(path_realization, "t_max.npy"), stations_t_max)

            #write_data.write_yaml(station_coordinates, os.path.join(path_realization, "stations.yml"))
            df = pd.DataFrame(station_coordinates, columns=['station_id', 'latitude', 'longitude'])
            df.to_csv(os.path.join(path_realization, "stations.csv"), index=False)

    print("... finished cleaning weather data")

'''# ------------------------
# Create realisation
# ------------------------
path = "X:/nismod/data/energy_demand/J-MARIUS_data"
result_path = "X:/nismod/data/energy_demand/J-MARIUS_data"
realisation_path = "X:/nismod/data/energy_demand/J-MARIUS_data/_weather_data_cleaned"
realisation_out_path = "X:/nismod/data/energy_demand/J-MARIUS_data/_weather_realisation"
path_stiching_table = "X:/nismod/data/energy_demand/J-MARIUS_data/stitching_table/stitching_table_nf.dat"

create_realisation(
    realisation_nrs=10,
    realisation_path=realisation_path,
    realisation_out_path=realisation_out_path,
    path_stiching_table=path_stiching_table)'''
'''
# ------------------------
# Clean scenario data
# ------------------------
path = "X:/nismod/data/energy_demand/J-MARIUS_data"
result_path = "X:/nismod/data/energy_demand/J-MARIUS_data"

years_to_clean = [2046, 2047]

weather_dat_prepare(path, result_path, years_to_clean)'''
