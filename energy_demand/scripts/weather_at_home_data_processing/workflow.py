"""
Script to extract weather data from weather@home for supply model


1. Download yearly data from here: http://catalogue.ceda.ac.uk/uuid/0cea8d7aca57427fae92241348ae9b03

2. Extract data to folder

3. Configure path below

4. Run this script to get only the relevant data for all weather@home scenarios from 2020 - 2049:

    Daily mean wind speed
    Daily mean solar information

Links
------
http://data.ceda.ac.uk//badc//weather_at_home/data/marius_time_series/CEDA_MaRIUS_Climate_Data_Description.pdf
http://data.ceda.ac.uk/badc/weather_at_home/data/marius_time_series/near_future/data/
https://medium.com/@rtjeannier/pandas-101-cont-9d061cb73bfc
"""
import os
from energy_demand.scripts.weather_at_home_data_processing import extract_weather_data
from energy_demand.scripts.weather_at_home_data_processing import create_realisation
from energy_demand.scripts.weather_at_home_data_processing import map_weather_data

# =================================
# Configuration
# =================================
path_extracted_files = "X:/nismod/data/energy_demand/J-MARIUS_data" # Path to folder with extracted files
path_stiching_table = "X:/nismod/data/energy_demand/J-MARIUS_data/stitching_table/stitching_table_nf.dat" # Path to stiching table
path_results = "X:/nismod/data/energy_supply/weather_files" # Path to store results
path_input_coordinates = os.path.abspath("X:/nismod/data/energy_supply/regions_input.csv") # Path to file with coordinates to map onto

extract_data = False
stich_together = True
append_closest_weather_data = False

if extract_data:
    # =================================
    # Extract shortwave and wind data, extends 360 to 365 days, writes coordinates
    # Note: As this script takes a long time to run, use multiple instance to run selected years
    # =================================
    extract_weather_data.weather_dat_prepare(
        path_extracted_files,
        path_results)#,
        #years=[2020])
    print("... finished extracting data")

if stich_together:
    # =================================
    # Stich data together to create weather@home realization
    # =================================
    create_realisation.generate_weather_at_home_realisation(
        path_results=path_results,
        path_stiching_table=path_stiching_table,
        scenarios=[50, 51]) #range(60, 71))
    print("... finished creating realisations")

if append_closest_weather_data:
    # =================================
    # Assign spatial conversion and write out in form as necessary by supply team
    # =================================
    map_weather_data.spatially_map_data(
        path_results=path_results,
        path_weather_at_home_stations=os.path.join(path_results, "_cleaned_csv"),
        path_input_coordinates=path_input_coordinates,
        scenarios=range(100))
    print("... append closest weather information")
