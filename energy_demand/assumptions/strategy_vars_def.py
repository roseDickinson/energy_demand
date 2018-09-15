"""Strategy variable assumptions provided as parameters to smif
"""
import logging
from collections import defaultdict

from energy_demand.basic import basic_functions
from energy_demand.read_write import narrative_related

def load_smif_parameters(
        data_handle,
        assumptions=False,
        default_streategy_vars=False,
        mode='smif'
    ):
    """Get all model parameters from smifself.
    Create the dict `strategy_vars` and store
    all strategy variables (single and multidimensional/nested)
    and their standard narrative (single timestep).

    Arguments
    ---------
    data_handle : dict
        Data handler
    strategy_variable_names : list
        All strategy variable names
    assumptions : obj
        Assumptions
    mode : str
        Criteria to define in which mode this function is run

    Returns
    -------
    strategy_vars : dict
        Updated strategy variables

    Example
    --------
    The strategy variables are stored as follows:
    {'param_name_single_dim': {standard_narrative},
    'param_multi_single_dim': {
        'sub_param_name1': {standard_narrative},
        'sub_param_name2': {standard_narrative},
    }}
    """
    strategy_vars = defaultdict(dict)

    # Load all standard variables of parameters
    #default_streategy_vars = load_param_assump(
    #    assumptions=assumptions)

    # ------------------------------------------------------------
    # Create default narrative for every simulation parameter
    # ------------------------------------------------------------
    for var_name, var_entries in default_streategy_vars.items():

        crit_single_dim = narrative_related.check_multidimensional_var(var_entries)

        if crit_single_dim:

            # Get scenario value
            if mode == 'smif':  #smif mode

                try:
                    scenario_value = data_handle.get_parameter(var_name)
                except:
                    logging.warning("IMPORTANT WARNING: Pparamter could not be loaded from smif: `%s`", var_name)

                    # ------------------------------------
                    #TODO
                    # This needs to be fixed by directly loading multiple paramters from SMIF
                    scenario_value = var_entries['default_value']
            else: #local running
                #scenario_value = var_entries['default_value']
                scenario_value = var_entries['scenario_value']

            # Create default narrative with only one timestep from simulation base year to simulation end year
            created_narrative = narrative_related.default_narrative(
                end_yr=assumptions.simulation_end_yr,
                value_by=var_entries['default_value'],                # Base year value,
                value_ey=scenario_value,
                diffusion_choice=var_entries['diffusion_type'],       # Sigmoid or linear,
                base_yr=assumptions.base_yr,
                regional_specific=var_entries['regional_specific'])   # Criteria whether the same for all regions or not

            strategy_vars[var_name] = created_narrative

            #strategy_vars[var_name]['affected_sector'] = var_entries['affected_sector'] #NEW SECTOR SPECIFIC
            #strategy_vars[var_name]['affected_enduse'] = var_entries['affected_enduse'] #NEW SECTOR SPECIFIC

        else:

            # Standard narrative for multidimensional narrative
            for sub_var_name, sub_var_entries in var_entries.items():

                # Get scenario value
                if mode == 'smif':  #smif mode
                    try:
                        scenario_value = data_handle.get_parameter(sub_var_name)
                    except:
                        logging.warning("IMPORTANT WARNING: The paramter `%s` could not be loaded from smif ", var_name)

                        # ------------------------------------
                        #TODO
                        # This needs to be fixed by directly loading multiple paramters from SMIF
                        #scenario_value = sub_var_entries['default_value']
                        scenario_value = sub_var_entries['scenario_value']

                # Narrative
                created_narrative = narrative_related.default_narrative(
                    end_yr=assumptions.simulation_end_yr,
                    value_by=sub_var_entries['default_value'],                # Base year value,
                    value_ey=scenario_value,
                    diffusion_choice=sub_var_entries['diffusion_type'],       # Sigmoid or linear,
                    base_yr=assumptions.base_yr,
                    regional_specific=sub_var_entries['regional_specific'])   # Criteria whether the same for all regions or not

                strategy_vars[var_name][sub_var_name] = created_narrative #{'multi_scenario_values': created_narrative}
                #strategy_vars[var_name][sub_var_name] =['affected_sector'] = var_entries['affected_sector'] #NEW SECTOR SPECIFIC

    return strategy_vars

def load_param_assump(
        paths=None,
        local_paths=None,
        assumptions=None,
        writeYAML=False
    ):
    """All assumptions of the energy demand model
    are loaded and added to the data dictionary

    Arguments
    ---------
    paths : dict
        Paths
    assumptions : dict
        Assumptions

    Returns
    -------
    data : dict
        Data dictionary with added ssumption dict
    """
    strategy_vars = defaultdict(dict)

    # ------------------
    # Spatial explicit diffusion
    # ------------------
    strategy_vars['spatial_explicit_diffusion'] = {
        "name": "spatial_explicit_diffusion",
        "absolute_range": (0, 1),
        "description": "Criteria to define spatial or non spatial diffusion",
        "suggested_range": (0, 1),
        "default_value": assumptions.spatial_explicit_diffusion,
        "units": 'years',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    strategy_vars['speed_con_max'] = {
        "name": "speed_con_max",
        "absolute_range": (0, 99),
        "description": "Maximum speed of penetration (for spatial explicit diffusion)",
        "suggested_range": (0, 99),
        "default_value": assumptions.speed_con_max,
        "units": None,
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # -----------
    # Demand management of heat pumps
    # -----------
    strategy_vars['flat_heat_pump_profile_both'] = {
        "name": "flat_heat_pump_profile_both",
        "absolute_range": (0, 1),
        "description": "Heat pump profile flat or with actual data",
        "suggested_range": (0, 1),
        "default_value": assumptions.flat_heat_pump_profile_both,
        "units": 'bool',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    strategy_vars['flat_heat_pump_profile_only_water'] = {
        "name": "flat_heat_pump_profile_only_water",
        "absolute_range": (0, 1),
        "description": "Heat pump profile flat or with actual data only for water heating",
        "suggested_range": (0, 1),
        "default_value": assumptions.flat_heat_pump_profile_only_water,
        "units": 'bool',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # ----------------------
    # Heat pump technology mix
    # Source: Hannon 2015: Raising the temperature of the UK heat pump market: Learning lessons from Finland
    # ----------------------
    strategy_vars['gshp_fraction_ey'] = {
        "name": "gshp_fraction_ey",
        "absolute_range": (0, 1),
        "description": "Relative GSHP (%) to GSHP+ASHP",
        "suggested_range": (assumptions.gshp_fraction, 0.5),
        "default_value": assumptions.gshp_fraction,
        "units": 'decimal',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # ============================================================
    #  Demand management assumptions (daily demand shape)
    #  An improvement in load factor improvement can be assigned
    #  for every enduse (peak shaving)
    #
    #  Example: 0.2 --> Improvement in load factor until ey
    # ============================================================
    enduses_demand_managent = {

        #Residential submodule
        'demand_management_improvement__rs_space_heating': 0,
        'demand_management_improvement__rs_water_heating': 0,
        'demand_management_improvement__rs_lighting': 0,
        'demand_management_improvement__rs_cooking': 0,
        'demand_management_improvement__rs_cold': 0,
        'demand_management_improvement__rs_wet': 0,
        'demand_management_improvement__rs_consumer_electronics': 0,
        'demand_management_improvement__rs_home_computing': 0,

        # Submodel Service (Table 5.5a)
        'demand_management_improvement__ss_space_heating': 0,
        'demand_management_improvement__ss_water_heating': 0,
        'demand_management_improvement__ss_cooling_humidification': 0,
        'demand_management_improvement__ss_fans': 0,
        'demand_management_improvement__ss_lighting': 0,
        'demand_management_improvement__ss_catering': 0,
        'demand_management_improvement__ss_small_power': 0,
        'demand_management_improvement__ss_ICT_equipment': 0,
        'demand_management_improvement__ss_cooled_storage': 0,
        'demand_management_improvement__ss_other_gas': 0,
        'demand_management_improvement__ss_other_electricity': 0,

        # Industry submodule
        'demand_management_improvement__is_high_temp_process': 0,
        'demand_management_improvement__is_low_temp_process': 0,
        'demand_management_improvement__is_drying_separation': 0,
        'demand_management_improvement__is_motors': 0,
        'demand_management_improvement__is_compressed_air': 0,
        'demand_management_improvement__is_lighting': 0,
        'demand_management_improvement__is_space_heating': 0,
        'demand_management_improvement__is_other': 0,
        'demand_management_improvement__is_refrigeration': 0}

    # Helper function to create description of parameters for all enduses
    for demand_name, scenario_value in enduses_demand_managent.items():
        strategy_vars[demand_name] = {
            "name": demand_name,
            "absolute_range": (0, 1),
            "description": "reduction in load factor for enduse {}".format(demand_name),
            "suggested_range": (0, 1),
            "default_value": 0,
            "units": 'decimal',
            'affected_enduse': [demand_name.split("__")[1]],
            'regional_specific': True,
            'diffusion_type': 'linear'}

    # =======================================
    # Climate Change assumptions
    # Temperature changes for every month for future year
    # =======================================
    temps = {
        'climate_change_temp_d__Jan': 0,
        'climate_change_temp_d__Feb': 0,
        'climate_change_temp_d__Mar': 0,
        'climate_change_temp_d__Apr': 0,
        'climate_change_temp_d__May': 0,
        'climate_change_temp_d__Jun': 0,
        'climate_change_temp_d__Jul': 0,
        'climate_change_temp_d__Aug': 0,
        'climate_change_temp_d__Sep': 0,
        'climate_change_temp_d__Oct': 0,
        'climate_change_temp_d__Nov': 0,
        'climate_change_temp_d__Dec': 0}

    for month_python, _ in enumerate(temps):
        month_str = basic_functions.get_month_from_int(month_python + 1)
        name = "climate_change_temp_d__{}".format(month_str)
        strategy_vars[name] = {
            "name": name,
            "absolute_range": (-0, 10),
            "description": "Temperature change for month {}".format(month_str),
            "suggested_range": (-5, 5),
            "default_value": 0,
            "units": '°C',
            'regional_specific': False,
            'diffusion_type': 'linear'}

    # ============================================================
    # Base temperature assumptions for heating and cooling demand
    # The diffusion is asumed to be linear
    # ============================================================
    strategy_vars['rs_t_base_heating_future_yr'] = {
        "name": "rs_t_base_heating_future_yr",
        "absolute_range": (0, 20),
        "description": "Base temperature assumption residential heating",
        "suggested_range": (13, 17),
        "default_value": assumptions.t_bases.rs_t_heating_by, #15.5
        "units": '°C',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # Future base year temperature
    strategy_vars['ss_t_base_heating_future_yr'] = {
        "name": "ss_t_base_heating_future_yr",
        "absolute_range": (0, 20),
        "description": "Base temperature assumption service sector heating",
        "suggested_range": (13, 17),
        "default_value": assumptions.t_bases.ss_t_heating_by, #15.5
        "units": '°C',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # Cooling base temperature
    # Future base year temperature
    strategy_vars['ss_t_base_cooling_future_yr'] = {
        "name": "ss_t_base_cooling_future_yr",
        "absolute_range": (0, 25),
        "description": "Base temperature assumption service sector cooling",
        "suggested_range": (13, 17),
        "default_value": assumptions.t_bases.ss_t_cooling_by, #5
        "units": '°C',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # Future base year temperature
    strategy_vars['is_t_base_heating_future_yr'] = {
        "name": "is_t_base_heating_future_yr",
        "absolute_range": (0, 20),
        "description": "Base temperature assumption service sector heating",
        "suggested_range": (13, 17),
        "default_value": assumptions.t_bases.is_t_heating_by, #15.5
        "units": '°C',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # ============================================================
    # Smart meter assumptions (Residential)
    #
    # DECC 2015: Smart Metering Early Learning Project: Synthesis report
    # https://www.gov.uk/government/publications/smart-metering-early-learning-project-and-small-scale-behaviour-trials
    # Reasonable assumption is between 0.03 and 0.01 (DECC 2015)
    # ============================================================
    strategy_vars['smart_meter_improvement_p'] = {
        "name": "smart_meter_improvement_p",
        "absolute_range": (0, 1),
        "description": "Improvement of smart meter penetration",
        "suggested_range": (0, 0.9),
        "default_value": assumptions.smart_meter_assump['smart_meter_p_by'],
        "units": 'decimal',
        'regional_specific': True,
        'diffusion_type': 'linear'}

    # ============================================================
    # Cooling
    # ============================================================
    strategy_vars['cooled_floorarea__ss_cooling_humidification'] = {
        "name": "cooled_floorarea__ss_cooling_humidification",
        "absolute_range": (0, 1),
        "description": "Change in cooling of floor area (service sector)",
        "suggested_range": (-1, 1),
        "default_value": assumptions.cooled_ss_floorarea_by,
        "units": 'decimal',
        'regional_specific': True,
        'diffusion_type': 'linear'}

    # ============================================================
    # Industrial processes
    # ============================================================
    strategy_vars['p_cold_rolling_steel'] = {
        "name": "p_cold_rolling_steel",
        "absolute_range": (0, 1),
        "description": "Sectoral share of cold rolling in steel manufacturing)",
        "suggested_range": (0, 1),
        "default_value": assumptions.p_cold_rolling_steel_by,
        "units": 'decimal',
        'regional_specific': True,
        'diffusion_type': 'linear'}

    # ============================================================
    # Heat recycling & reuse
    # ============================================================
    strategy_vars['heat_recoved__rs_space_heating'] = {
        "name": "heat_recoved__rs_space_heating",
        "absolute_range": (0, 1),
        "description": "Reduction in heat because of heat recovery and recycling (residential sector)",
        "suggested_range": (0, 1),
        "default_value": 0,
        "units": 'decimal',
        'affected_enduse': ['rs_space_heating'],
        'regional_specific': True,
        'diffusion_type': 'linear'}

    strategy_vars['heat_recoved__ss_space_heating'] = {
        "name": "heat_recoved__ss_space_heating",
        "absolute_range": (0, 1),
        "description": "Reduction in heat because of heat recovery and recycling (service sector)",
        "suggested_range": (0, 1),
        "default_value": 0,
        "units": 'decimal',
        'affected_enduse': ['ss_space_heating'],
        'regional_specific': True,
        'diffusion_type': 'linear'}

    strategy_vars['heat_recoved__is_space_heating'] = {
        "name": "heat_recoved__is_space_heating",
        "absolute_range": (0, 1),
        "description": "Reduction in heat because of heat recovery and recycling (industry sector)",
        "suggested_range": (0, 1),
        "default_value": 0,
        "units": 'decimal',
        'affected_enduse': ['is_space_heating'],
        'regional_specific': True,
        'diffusion_type': 'linear'}

    # ============================================================
    # Air leakage
    # ============================================================
    strategy_vars['air_leakage__rs_space_heating'] = {
        "name": "air_leakage__rs_space_heating",
        "absolute_range": (0, 1),
        "description": "Reduction in heat because of air leakage improvement (residential sector)",
        "suggested_range": (0, 1),
        "default_value": 0,
        "units": 'decimal',
        'affected_enduse': ['rs_space_heating'],
        'regional_specific': True,
        'diffusion_type': 'linear'}

    strategy_vars['air_leakage__ss_space_heating'] = {
        "name": "air_leakage__ss_space_heating",
        "absolute_range": (0, 1),
        "description": "Reduction in heat because of of air leakage improvementservice sector)",
        "suggested_range": (0, 1),
        "default_value": 0,
        "units": 'decimal',
        'affected_enduse': ['ss_space_heating'],
        'regional_specific': True,
        'diffusion_type': 'linear'}

    strategy_vars['air_leakage__is_space_heating'] = {
        "name": "air_leakage__is_space_heating",
        "absolute_range": (0, 1),
        "description": "Reduction in heat because of air leakage improvement (industry sector)",
        "suggested_range": (0, 1),
        "default_value": 0,
        "units": 'decimal',
        "affected_enduse": ['is_space_heating'],
        'regional_specific': True,
        'diffusion_type': 'linear'}

    # ---------------------------------------------------------
    # General change in fuel consumption for specific enduses
    # ---------------------------------------------------------
    #   With these assumptions, general efficiency gain (across all fueltypes)
    #   can be defined for specific enduses. This may be e.g. due to general
    #   efficiency gains or anticipated increases in demand.
    #   NTH: Specific hanges per fueltype (not across al fueltesp)
    #
    #   Change in fuel until the simulation end year (
    #   if no change set to 1, if e.g. 10% decrease change to 0.9)
    # -------------------------------------------------------
    enduse_overall_change_enduses = {

        # Submodel Residential
        'rs_space_heating': 0,
        'rs_water_heating': 0,
        'rs_lighting': 0,
        'rs_cooking': 0,
        'rs_cold': 0,
        'rs_wet': 0,
        'rs_consumer_electronics': 0,
        'rs_home_computing': 0,

        # Submodel Service (Table 5.5a)
        # same % improvements from baseline over all sectors
        'ss_space_heating': 0,
        'ss_water_heating': 0,
        'ss_cooling_humidification': 0,
        'ss_fans': 0,
        'ss_lighting': 0,
        'ss_catering': 0,
        'ss_small_power': 0,
        'ss_ICT_equipment': 0,
        'ss_cooled_storage': 0,
        'ss_other_gas': 0,
        'ss_other_electricity': 0,

        # Submodel Industry
        # same % improvements from baseline over all sectors
        'is_high_temp_process': 0,
        'is_low_temp_process': 0,
        'is_drying_separation': 0,
        'is_motors': 0,
        'is_compressed_air': 0,
        'is_lighting': 0,
        'is_space_heating': 0,
        'is_other': 0,
        'is_refrigeration': 0}

    # Helper function to create description of parameters for all enduses
    for enduse_name, param_value in enduse_overall_change_enduses.items():
        strategy_vars[enduse_name] = {
            "name": enduse_name,
            "absolute_range": (-1, 1),
            "description": "Enduse specific change {}".format(enduse_name),
            "suggested_range": (0, 1),
            "default_value": 0,
            "units": 'decimal',
            'affected_enduse': [enduse_name],
            'affected_sector': [],
            'regional_specific': True,
            'diffusion_type': 'linear'}

    # ============================================================
    # Technologies & efficiencies
    # ============================================================

    # --Assumption how much of technological efficiency is reached
    strategy_vars["f_eff_achieved"] = {
        "name": "f_eff_achieved",
        "absolute_range": (0, 1),
        "description": "Fraction achieved of efficiency improvements",
        "suggested_range": (0, 1),
        "default_value": 0, # Default is no efficiency improvement
        "units": 'decimal',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    # --------------------------------------
    # Floor area per person change
    # ---------------------------------------
    strategy_vars["assump_diff_floorarea_pp"] = {
        "name": "assump_diff_floorarea_pp",
        "absolute_range": (-1, 1),
        "description": "Change in floor area per person (%, 1=100%)",
        "suggested_range": (0, 1),
        "default_value": 0,
        "units": 'decimal',
        'regional_specific': False,
        'diffusion_type': 'linear'}

    '''
    # -----------------------
    # Create parameter file only with fully descried parameters and write to yaml file
    # TODO UPDATE TODO TODO
    # -----------------------
    if not paths:
        pass
    else:
        strategy_vars_write = copy.copy(strategy_vars)

        # Delete affected_enduse
        for var in strategy_vars_write:
            try:
                del var['affected_enduse']
            except KeyError:
                pass

        if writeYAML:
            # Delete existing files
            basic_functions.del_file(local_paths['yaml_parameters_constrained'])
            basic_functions.del_file(local_paths['yaml_parameters_scenario'])

            # Write new files
            write_data.write_yaml_param_complete(
                local_paths['yaml_parameters_constrained'],
                strategy_vars_write)
            write_data.write_yaml_param_scenario(
                local_paths['yaml_parameters_scenario'],
                strategy_vars)

            raise Exception("The smif parameters are read and written to {}".format(local_paths['yaml_parameters_scenario']))
    '''

    strategy_vars_out = autocomplete_strategy_vars(strategy_vars)

    return dict(strategy_vars_out)

def autocomplete_strategy_vars(strategy_vars, narrative_crit=False):
    """TODO
    Autocomplete all narratives with 'affected_enduse'
    """
    if not narrative_crit:
        # --strategy_vars-- Convert to dict for loacl running purposes
        strategy_vars_out = defaultdict(dict)

        for var_name, var_entries in strategy_vars.items():

            crit_single_dim = narrative_related.check_multidimensional_var(var_entries)

            if crit_single_dim:

                strategy_vars_out[var_name] = var_entries

                # If no 'affected_enduse' defined, add empty list of affected enduses
                strategy_vars_out[var_name]['scenario_value'] = var_entries['default_value'] #scenario_value
                if 'affected_enduse' not in var_entries:
                    strategy_vars_out[var_name]['affected_enduse'] = []
            else:
                for sub_var_name, sub_var_entries in var_entries.items():
                    strategy_vars_out[var_name][sub_var_name] = sub_var_entries

                    strategy_vars_out[var_name][sub_var_name]['scenario_value'] = var_entries['default_value'] #scenario_value
    
                    # If no 'affected_enduse' defined, add empty list of affected enduses
                    if 'affected_enduse' not in sub_var_entries:
                        strategy_vars_out[var_name][sub_var_name]['affected_enduse'] = []
    else:
        # Same but narratives which need to be iterated
        strategy_vars_out = defaultdict(dict)

        for var_name, var_entries in strategy_vars.items():

            crit_single_dim = narrative_related.check_multidimensional_var(var_entries)

            if crit_single_dim:

                updated_narratives = []
                for narrative in var_entries:

                    # If no 'affected_enduse' defined, add empty list of affected enduses
                    if 'affected_enduse' not in narrative:
                        narrative['affected_enduse'] = []

                    updated_narratives.append(narrative)

                strategy_vars_out[var_name] = updated_narratives

            else:
                for sub_var_name, sub_var_entries in var_entries.items():

                    updated_narratives = []
                    for narrative in sub_var_entries:

                        # If no 'affected_enduse' defined, add empty list of affected enduses
                        if 'affected_enduse' not in narrative:
                            narrative['affected_enduse'] = []

                        updated_narratives.append(narrative)

                    strategy_vars_out[var_name][sub_var_name] = updated_narratives

    return strategy_vars_out

def get_affected_enduse(strategy_vars, name):
    """Get all defined affected enduses of a scenario variable

    Arguments
    ---------
    strategy_vars : dict
        Dict with all defined strategy variables
    name : str
        Name of variable to get

    Returns
    -------
    enduses : list
        AFfected enduses of scenario variable
    """
    try:
        for var in strategy_vars:
            if var['name'] == name:
                enduses = var['affected_enduse']

                return enduses
    except KeyError:
        # Not affected enduses defined
        enduses = []

        return enduses
