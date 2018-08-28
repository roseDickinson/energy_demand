"""Allows to run HIRE locally outside the SMIF framework

    Tools
    # -------
    Profiling:  https://jiffyclub.github.io/snakeviz/
    python -m cProfile -o program.prof main.py
    snakeviz program.prof
regional_specific, crit_all_the_same
#TODO Interface energy demand
#TODO Make that congruence value map is better loaded from seperate file (e.g. populatio ndensity)
#TODO Create own .py chart file for every chart
#TODO Import weather data loading and importing whole range of weather scenarios
#TODO Replace geopanda csv loading
#TODO Take disaggregation completely out?
#TODO Test if technology type can be left empty in technology spreadsheet
#TODO Try to remove tech_type
#TODO Write out full result. Then write function to aggregate accordingly
#TODO replace create_csv_file by pandas
#TODO SIMple aggregation. Write out sectormodel, enduse, region, fueltypes.... --> Do all aggregation based on that
"""
import os
import sys
import time
import logging
from collections import defaultdict
import numpy as np
from energy_demand.basic import date_prop
from energy_demand.plotting import plotting_results
from energy_demand import model
from energy_demand.basic import testing_functions
from energy_demand.basic import lookup_tables
from energy_demand.assumptions import general_assumptions
from energy_demand.assumptions import strategy_vars_def
from energy_demand.read_write import data_loader
from energy_demand.basic import logger_setup
from energy_demand.read_write import write_data
from energy_demand.read_write import read_data
from energy_demand.basic import basic_functions
from energy_demand.scripts import s_disaggregation
from energy_demand.validation import lad_validation
from energy_demand.basic import demand_supply_interaction
from energy_demand.read_write import load_parameter_values
from energy_demand.scripts import s_generate_scenario_parameters
from energy_demand.scripts.init_scripts import scenario_initalisation
from energy_demand.scripts.init_scripts import spatial_explicit_modelling_strategy_vars
from energy_demand.scripts.init_scripts import create_spatial_diffusion_factors

def energy_demand_model(regions, data, assumptions):
    """Main function of energy demand model to calculate yearly demand

    Arguments
    ----------
    data : dict
        Data container

    Returns
    -------
    result_dict : dict
        A nested dictionary containing all data for energy supply model with
        timesteps for every hour in a year.
        [fueltype : region : timestep]
    modelrun_obj : dict
        Object of a yearly model run

    Note
    ----
    This function is executed in the wrapper
    """
    logging.info("... Number of modelled regions: %s", len(regions))

    modelrun = model.EnergyDemandModel(
        regions=regions,
        data=data,
        assumptions=assumptions)

    # Calculate base year demand
    fuels_in = testing_functions.test_function_fuel_sum(
        data,
        data['fuel_disagg'],
        data['criterias']['mode_constrained'],
        assumptions.enduse_space_heating)

    # Log model results
    write_data.logg_info(modelrun, fuels_in, data)
    logging.info("... finished running energy demand model simulation")
    return modelrun

if __name__ == "__main__":
    """
    """
    data = {}

    # Paths
    if len(sys.argv) != 2:
        print("Please provide a local data path:")
        local_data_path = os.path.abspath('data')
    else:
        local_data_path = sys.argv[1]

    path_main = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', "energy_demand/config_data"))

    # Load data
    data['criterias'] = {}
    data['criterias']['mode_constrained'] = True                    # True: Technologies are defined in ED model and fuel is provided, False: Heat is delievered not per technologies
    data['criterias']['virtual_building_stock_criteria'] = True     # True: Run virtual building stock model

    fast_model_run = False
    if fast_model_run == True:
        data['criterias']['write_txt_additional_results'] = False
        data['criterias']['validation_criteria'] = False    # For validation, the mode_constrained must be True
        data['criterias']['plot_crit'] = False
        data['criterias']['crit_plot_enduse_lp'] = False
        data['criterias']['writeYAML_keynames'] = False
    else:
        data['criterias']['write_txt_additional_results'] = True
        data['criterias']['validation_criteria'] = True
        data['criterias']['plot_crit'] = False
        data['criterias']['crit_plot_enduse_lp'] = True
        data['criterias']['writeYAML_keynames'] = True

    # -------------------
    # Other configuration
    # -------------------
    RESILIENCEPAPERPOUTPUT = True                                      # Output data for resilience paper

    # If the smif configuration files what to be written, set this to true. The program will abort after they are written to YAML files
    data['criterias']['writeYAML'] = False

    data['criterias']['reg_selection'] = False
    data['criterias']['reg_selection_csv_name'] = "msoa_regions_ed.csv" # CSV file stored in 'region' folder with simulated regions
    data['criterias']['MSOA_crit'] = False

    # --- Model running configurations
    user_defined_base_yr = 2015
    simulated_yrs = [2015, 2050]

    # --- Region definition configuration
    name_region_set = os.path.join(local_data_path, 'region_definitions', "lad_2016_uk_simplified.shp")        # LAD

    #name_population_dataset = os.path.join(local_data_path, 'scenarios', 'uk_pop_high_migration_2015_2050.csv')
    #name_population_dataset = os.path.join(local_data_path, 'scenarios', 'uk_pop_constant_2015_2050.csv') # Constant scenario
    name_population_dataset = os.path.join(local_data_path, 'scenarios', 'MISTRAL_pop_gva/data', 'pop-a_econ-c_fuel-c/population__lad.csv') # Constant scenario
    # MSOA model run
    #name_region_set_selection = "msoa_regions_ed.csv"
    #name_region_set = os.path.join(local_data_path, 'region_definitions', 'msoa_uk', "msoa_lad_2015_uk.shp")    # MSOA
    #name_population_dataset = os.path.join(local_data_path, 'scenarios', 'uk_pop_high_migration_2015_2050.csv')

    # GVA datasets
    name_gva_dataset = os.path.join(local_data_path, 'scenarios', 'MISTRAL_pop_gva/data', 'pop-a_econ-c_fuel-c/gva_per_head__lad_sector.csv') # Constant scenario
    name_gva_dataset_per_head = os.path.join(local_data_path, 'scenarios', 'MISTRAL_pop_gva/data', 'pop-a_econ-c_fuel-c/gva_per_head__lad.csv') # Constant scenario
    # -------------------------------
    # User defined strategy variables
    # -------------------------------
    user_defined_strategy_vars = {
        'f_eff_achieved': 0            # Efficiency improvements
        #'flat_heat_pump_profile_both': 1 #Flat heat pump dsm
        #'enduse_change__ss_fans': 0.5   # 50% improvement
    }

    # -----
    # Paths
    # -----
    name_scenario_run = "_result_local_data_{}".format(str(time.ctime()).replace(":", "_").replace(" ", "_"))

    data['paths'] = data_loader.load_paths(path_main)
    data['local_paths'] = data_loader.get_local_paths(local_data_path)
    data['result_paths'] = data_loader.get_result_paths(
        os.path.join(os.path.join(local_data_path, "..", "results"), name_scenario_run))

    data['scenario_data'] = defaultdict(dict)
    data['lookups'] = lookup_tables.basic_lookups()
    data['enduses'], data['sectors'], data['fuels'] = data_loader.load_fuels(data['paths'], data['lookups'])

    data['regions'] = read_data.get_region_names(name_region_set)
    data['reg_nrs'] = len(data['regions'])

    reg_centroids = read_data.get_region_centroids(name_region_set)
    data['reg_coord'] = basic_functions.get_long_lat_decimal_degrees(reg_centroids)

    data['scenario_data']['population'] = data_loader.read_scenario_data(name_population_dataset)

    # Read GVA sector specific data
    data['scenario_data']['gva_industry_service'] = data_loader.read_scenario_data_gva(name_gva_dataset, all_dummy_data=False)
    data['scenario_data']['gva_per_head'] = data_loader.read_scenario_data(name_gva_dataset_per_head)

    # Read sector assignement lookup values
    data['gva_sector_lu'] = lookup_tables.economic_sectors_regional_MISTRAL()

    # -----------------------------
    # Assumptions
    # -----------------------------
    data['assumptions'] = general_assumptions.Assumptions(
        base_yr=user_defined_base_yr,
        curr_yr=2015,
        simulated_yrs=simulated_yrs,
        paths=data['paths'],
        enduses=data['enduses'],
        sectors=data['sectors'],
        fueltypes=data['lookups']['fueltypes'],
        fueltypes_nr=data['lookups']['fueltypes_nr'])

    # -----------------------
    # Calculate population density for base year
    # -----------------------
    region_objects = read_data.get_region_objects(name_region_set)
    data['pop_density'] = {}
    for region in region_objects:
        region_name = region['properties']['name']
        region_area = region['properties']['st_areasha']
        data['pop_density'][region_name] = data['scenario_data']['population'][data['assumptions'].base_yr][region_name] / region_area

    # Load standard strategy variable values
    strategy_vars = strategy_vars_def.load_param_assump(
        data['paths'],
        data['local_paths'],
        data['assumptions'],
        writeYAML=data['criterias']['writeYAML'])
    data['assumptions'].update('strategy_vars', strategy_vars)

    # -----------
    # Load smif parameters (if run locally, the standard values are loaded)
    # Add standard narrative
    # -----------
    strategy_vars = strategy_vars_def.load_smif_parameters(
        data_handle=strategy_vars,
        strategy_variable_names=strategy_vars.keys(),
        assumptions=data['assumptions'],
        mode='local')
    data['assumptions'].update('strategy_vars', strategy_vars)

    # --------------
    # Update user defined strategy variables
    # --------------
    for var_name, var_value in user_defined_strategy_vars.items():
        data['assumptions'].strategy_vars[var_name]['scenario_value'] = var_value


    data['tech_lp'] = data_loader.load_data_profiles(
        data['paths'], data['local_paths'],
        data['assumptions'].model_yeardays,
        data['assumptions'].model_yeardays_daytype,)

    data['technologies'] = general_assumptions.update_technology_assumption(
        data['assumptions'].technologies,
        data['assumptions'].strategy_vars['f_eff_achieved']['scenario_value'],
        data['assumptions'].strategy_vars['gshp_fraction_ey']['scenario_value'])

    data['weather_stations'], data['temp_data'] = data_loader.load_temp_data(data['local_paths'])

    if data['criterias']['virtual_building_stock_criteria']:
        data['scenario_data']['floor_area']['rs_floorarea'], data['scenario_data']['floor_area']['ss_floorarea'], data['service_building_count'], rs_regions_without_floorarea, ss_regions_without_floorarea = data_loader.floor_area_virtual_dw(
            data['regions'],
            data['sectors']['all_sectors'],
            data['local_paths'],
            data['scenario_data']['population'][data['assumptions'].base_yr],
            data['assumptions'].base_yr)

        # Add all areas with no floor area data
        data['assumptions'].update("rs_regions_without_floorarea", rs_regions_without_floorarea)
        data['assumptions'].update("ss_regions_without_floorarea", ss_regions_without_floorarea)

    # Lookup table to import industry sectoral gva
    #lookup_tables.industrydemand_name_sic2007()

    print("Start Energy Demand Model with python version: " + str(sys.version))
    print("Info model run")
    print("Nr of Regions " + str(data['reg_nrs']))

    # Optain population data for disaggregation
    if data['criterias']['MSOA_crit']:
        name_population_dataset = data['local_paths']['path_population_data_for_disaggregation_MSOA']
    else:
        name_population_dataset = data['local_paths']['path_population_data_for_disaggregation_LAD']
    data['pop_for_disag'] =  data_loader.read_scenario_data(name_population_dataset)


    # --------------------
    # Disaggregate fuel
    # --------------------
    data['fuel_disagg'] = s_disaggregation.disaggregate_demand(data)

    # ------------------------------------------------
    # Calculate spatial diffusion factors
    # ------------------------------------------------
    f_reg, f_reg_norm, f_reg_norm_abs, crit_all_the_same = create_spatial_diffusion_factors(
        strategy_vars=data['assumptions'].strategy_vars,
        fuel_disagg=data['fuel_disagg'],
        regions=data['regions'],
        real_values=data['pop_density'],
        speed_con_max=strategy_vars['speed_con_max']['scenario_value']) #TODO LOAD REAL VALUES FROM DATA CSV

    # ------------------------------------------------
    # Initialise scenario
    # ------------------------------------------------
    init_cont = {}
    init_cont['rs_sig_param_tech'], init_cont['ss_sig_param_tech'], init_cont['is_sig_param_tech'] = scenario_initalisation(
        data,
        f_reg,
        f_reg_norm,
        f_reg_norm_abs,
        crit_all_the_same)

    for key, value in init_cont.items():
        setattr(data['assumptions'], key, value)

    # --------------------------
    # Spatial explicit modelling
    # --------------------------
    regional_strategy_vars = spatial_explicit_modelling_strategy_vars(
        data['assumptions'],
        data['regions'],
        data['fuel_disagg'],
        f_reg,
        f_reg_norm,
        f_reg_norm_abs)
    data['assumptions'].update('strategy_vars', regional_strategy_vars)

    # ------------------------------------------------------
    # Annual parameter generation (calculate parameter value for every year)
    # ------------------------------------------------------
    regional_strategy_vars, non_regional_strategy_vars = s_generate_scenario_parameters.generate_annual_param_vals(
        data['regions'],
        data['assumptions'].strategy_vars,
        simulated_yrs,
        path=local_data_path)

    data['assumptions'].update('regional_strategy_vars', regional_strategy_vars)
    data['assumptions'].update('non_regional_strategy_vars', non_regional_strategy_vars)
    
    # ------------------------------------------------
    # Spatial Validation
    # ------------------------------------------------
    if data['criterias']['validation_criteria'] == True:
        lad_validation.spatial_validation_lad_level(
            data['fuel_disagg'],
            data['lookups'],
            data['result_paths'],
            data['paths'],
            data['regions'],
            data['reg_coord'],
            data['criterias']['plot_crit'])

    # -----------------------------------
    # Only selection of regions to simulate
    # -------------------------------------
    if data['criterias']['reg_selection']:
        region_selection = read_data.get_region_selection(
            os.path.join(
                data['local_paths']['local_path_datafolder'],
                "region_definitions",
                data['criterias']['reg_selection_csv_name']))
        #region_selection = ['E02003237', 'E02003238']

        data['reg_nrs'] = len(region_selection)
    else:
        region_selection = data['regions']

    # -------------------------------------------
    # Create .ini file with simulation information
    # -------------------------------------------
    write_data.write_simulation_inifile(
        data['result_paths']['data_results'],
        data,
        region_selection)

    for sim_yr in data['assumptions'].simulated_yrs:
        print("Simulation for year --------------:  " + str(sim_yr))

        # Set current year
        setattr(data['assumptions'], 'curr_yr', sim_yr)

        fuel_in, fuel_in_biomass, fuel_in_elec, fuel_in_gas, fuel_in_heat, fuel_in_hydro, fuel_in_solid_fuel, fuel_in_oil, tot_heating = testing_functions.test_function_fuel_sum(
            data,
            data['fuel_disagg'],
            data['criterias']['mode_constrained'],
            data['assumptions'].enduse_space_heating)

        # -----------------------
        # Main model run function
        # -----------------------
        sim_obj = energy_demand_model(region_selection, data, data['assumptions'])

        # ------------------------------------------------
        # Temporal Validation
        # ------------------------------------------------
        if data['criterias']['validation_criteria'] == True and sim_yr == data['assumptions'].base_yr:
            lad_validation.temporal_validation_lad(
                sim_obj.ed_fueltype_national_yh,
                sim_obj.ed_fueltype_regs_yh,
                data['lookups']['fueltypes'],
                data['result_paths'],
                data['paths'],
                region_selection,
                data['reg_coord'],
                data['assumptions'].seasons,
                data['assumptions'].model_yeardays_daytype,
                data['criterias']['plot_crit'])

        # -------------------------
        # Write for resilience paper
        # -------------------------
        if RESILIENCEPAPERPOUTPUT:

            if round(np.sum(sim_obj.ed_fueltype_national_yh), 2)!= round(np.sum(sim_obj.results_unconstrained), 2):
                print("Should be the same")
                raise Exception

            write_data.resilience_paper(
                sim_yr,
                data['result_paths']['data_results_model_runs'],
                "resilience_paper",
                "result_risk_paper_{}_".format(sim_yr),
                sim_obj.results_unconstrained,
                ['residential', 'service', 'industry'],
                data['regions'],
                data['lookups']['fueltypes'],
                fueltype_str='electricity')

        # --------------------------------------------------------
        # Reshape day and hours to yearhous (from (365, 24) to 8760)
        # --------------------------------------------------------

        # np.array with constrained demands for heating {constrained_techs: np.array(fueltype, sectors, region, periods)}
        results_constrained_reshaped = {}

        for heating_tech, submodel_techs in sim_obj.results_constrained.items():
            results_constrained_reshaped[heating_tech] = submodel_techs.reshape(
                len(data['assumptions'].submodels_names),
                data['reg_nrs'],
                data['lookups']['fueltypes_nr'],
                8760)
        results_constrained = results_constrained_reshaped

        # np.array of all fueltypes(fueltype, sectors, region, periods)
        results_unconstrained = sim_obj.results_unconstrained.reshape(
            len(data['assumptions'].submodels_names),
            data['reg_nrs'],
            data['lookups']['fueltypes_nr'],
            8760)

        # Testing
        if round(np.sum(sim_obj.ed_fueltype_national_yh), 2)!= round(np.sum(sim_obj.results_unconstrained), 2):
            logging.warning("Should be the same {} {}".format(
                round(np.sum(sim_obj.ed_fueltype_national_yh), 2),
                round(np.sum(sim_obj.results_unconstrained), 2)))
            raise Exception

        # -------------------------------------
        # # Generate YAML file with keynames for `sector_model`
        # -------------------------------------
        if data['criterias']['writeYAML_keynames']:
            if data['criterias']['mode_constrained']:

                supply_results = demand_supply_interaction.constrained_results(
                    results_constrained,
                    results_unconstrained,
                    data['assumptions'].submodels_names,
                    data['lookups']['fueltypes'],
                    data['technologies'])

                write_data.write_yaml_output_keynames(
                    data['local_paths']['yaml_parameters_keynames_constrained'], supply_results.keys())
            else:
                supply_results = demand_supply_interaction.unconstrained_results(
                    results_unconstrained,
                    data['assumptions'].submodels_names,
                    data['lookups']['fueltypes'])

                write_data.write_yaml_output_keynames(
                    data['local_paths']['yaml_parameters_keynames_unconstrained'], supply_results.keys())

        # --------------------------
        # Write out all calculations
        # --------------------------
        if data['criterias']['write_txt_additional_results']:

            ed_fueltype_regs_yh = sim_obj.ed_fueltype_regs_yh
            out_enduse_specific = sim_obj.tot_fuel_y_enduse_specific_yh
            tot_fuel_y_max_enduses = sim_obj.tot_fuel_y_max_enduses
            ed_fueltype_national_yh = sim_obj.ed_fueltype_national_yh

            reg_load_factor_y = sim_obj.reg_load_factor_y
            reg_load_factor_yd = sim_obj.reg_load_factor_yd
            reg_load_factor_winter = sim_obj.reg_seasons_lf['winter']
            reg_load_factor_spring = sim_obj.reg_seasons_lf['spring']
            reg_load_factor_summer = sim_obj.reg_seasons_lf['summer']
            reg_load_factor_autumn = sim_obj.reg_seasons_lf['autumn']

            if data['criterias']['crit_plot_enduse_lp']:

                # Maybe move to result folder in a later step
                path_folder_lp = os.path.join(data['result_paths']['data_results'], 'individual_enduse_lp')
                basic_functions.delete_folder(path_folder_lp)
                basic_functions.create_folder(path_folder_lp)

                winter_week, _, _, _ = date_prop.get_seasonal_weeks()

                # Plot electricity
                for enduse, ed_yh in sim_obj.tot_fuel_y_enduse_specific_yh.items():
                    plotting_results.plot_enduse_yh(
                        name_fig="individ__electricity_{}_{}".format(enduse, sim_yr),
                        path_result=path_folder_lp,
                        ed_yh=ed_yh[data['lookups']['fueltypes']['electricity']],
                        days_to_plot=winter_week)

            # -------------------------------------------
            # Write annual results to txt files
            # -------------------------------------------
            print("... Start writing results to file")
            path_runs = data['result_paths']['data_results_model_runs']

            write_data.write_supply_results(
                sim_yr,
                "result_tot_yh",
                path_runs,
                sim_obj.ed_fueltype_regs_yh,
                "result_tot_submodels_fueltypes")
            write_data.write_enduse_specific(
                sim_yr,
                path_runs,
                out_enduse_specific,
                "out_enduse_specific")
            write_data.write_lf(
                path_runs,
                "result_reg_load_factor_y",
                [sim_yr],
                reg_load_factor_y,
                'reg_load_factor_y')
            write_data.write_lf(
                path_runs,
                "result_reg_load_factor_yd",
                [sim_yr],
                reg_load_factor_yd,
                'reg_load_factor_yd')
            write_data.write_lf(
                path_runs,
                "result_reg_load_factor_winter",
                [sim_yr],
                reg_load_factor_winter,
                'reg_load_factor_winter')
            write_data.write_lf(
                path_runs,
                "result_reg_load_factor_spring",
                [sim_yr],
                reg_load_factor_spring,
                'reg_load_factor_spring')
            write_data.write_lf(
                path_runs,
                "result_reg_load_factor_summer",
                [sim_yr],
                reg_load_factor_summer,
                'reg_load_factor_summer')
            write_data.write_lf(
                path_runs,
                "result_reg_load_factor_autumn",
                [sim_yr],
                reg_load_factor_autumn,
                'reg_load_factor_autumn')

            # -------------------------------------------
            # Write population files of simulation year
            # -------------------------------------------
            pop_array_reg = np.zeros((len(data['regions'])), dtype="float")
            for reg_array_nr, reg in enumerate(data['regions']):
                pop_array_reg[reg_array_nr] = data['scenario_data']['population'][sim_yr][reg]

            write_data.write_scenaric_population_data(
                sim_yr,
                data['result_paths']['model_run_pop'],
                pop_array_reg)
            print("... Finished writing results to file")

    print("-------------------------")
    print("... Finished running HIRE")
    print("-------------------------")
