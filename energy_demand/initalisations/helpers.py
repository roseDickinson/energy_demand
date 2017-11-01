"""Short diverse helper functions
"""
import numpy as np

def init_fuel_tech_p_by(all_enduses_with_fuels, fueltypes_nr):
    """Helper function to define stocks for all enduse and fueltype

    Arguments
    ----------
    all_enduses_with_fuels : dict
        Provided fuels
    fueltypes_nr : int
        Nr of fueltypes

    Returns
    -------
    fuel_tech_p_by : dict

    """
    fuel_tech_p_by = {}

    for enduse in all_enduses_with_fuels:
        fuel_tech_p_by[enduse] = dict.fromkeys(range(fueltypes_nr), {})

    return fuel_tech_p_by

def service_type_tech_by_p(lu_fueltypes, fuel_tech_p_by):
    """Initialise dict and fill with zeros

    Arguments
    ----------
    lu_fueltypes : dict
        Look-up dictionary
    fuel_tech_p_by : dict
        Fuel fraction per technology for base year

    Return
    -------
    service_fueltype_tech_by_p : dict
        Fraction of service per fueltype and technology for base year
    """
    service_fueltype_tech_by_p = {}
    for fueltype_int in lu_fueltypes.values():
        service_fueltype_tech_by_p[fueltype_int] = dict.fromkeys(fuel_tech_p_by[fueltype_int].keys(), 0)

    return service_fueltype_tech_by_p

def init_dict_brackets(first_level_keys):
    """Initialise a  dictionary with one level

    Arguments
    ----------
    first_level_keys : list
        First level data

    Returns
    -------
    one_level_dict : dict
         dictionary
    """
    one_level_dict = {}

    for first_key in first_level_keys:
        one_level_dict[first_key] = {}

    return one_level_dict

def add_undef_techs(heat_pumps, all_specified_tech_enduse, enduse):
    """Add technology to dict

    Arguments
    ----------
    heat_pumps : list
        List with heat pumps
    all_specified_tech_enduse_by : dict
        Technologey per enduse
    enduse : str
        Enduse

    Return
    -------
    all_specified_tech_enduse : dict
        Specified techs per enduse
    """
    for heat_pump in heat_pumps:
        if heat_pump not in all_specified_tech_enduse[enduse]:
            all_specified_tech_enduse[enduse].append(heat_pump)

    return all_specified_tech_enduse

def get_def_techs(fuel_tech_p_by):
    """Collect all technologies across all fueltypes for all endueses where
    a service share is defined for the end_year

    Arguments
    ----------
    fuel_tech_p_by : dict
        Fuel share per technology for base year

    Returns
    -------
    all_defined_tech_service_ey : dict
        All defined technologies with service in end year
    """
    all_defined_tech_service_ey = {}
    for enduse in fuel_tech_p_by:
        all_defined_tech_service_ey[enduse] = []
        for fueltype in fuel_tech_p_by[enduse]:
            all_defined_tech_service_ey[enduse].extend(fuel_tech_p_by[enduse][fueltype])

    return all_defined_tech_service_ey

def get_nested_dict_key(nested_dict):
    """Get all keys of nested dict

    Arguments
    ----------
    nested_dict : dict
        Nested dictionary

    Return
    ------
    all_nested_keys : list
        Key of nested dict
    """
    all_nested_keys = []
    for entry in nested_dict:
        for value in nested_dict[entry].keys():
            all_nested_keys.append(value)

    return all_nested_keys

def helper_set_same_eff_all_tech(technologies, eff_achieved_factor=1):
    """Helper function to assing same achieved efficiency

    Arguments
    ----------
    technologies : dict
        Technologies
    eff_achieved_factor : float,default=1
        Factor showing the fraction of how much an efficiency is achieved

    Returns
    -------
    technologies : dict
        Adapted technolog
    """
    for technology in technologies:
        technologies[technology]['eff_achieved'] = eff_achieved_factor

    return technologies
