"""Script to disaggregate national data into regional data
"""
import os
import logging
import copy
from collections import defaultdict
from energy_demand.profiles import hdd_cdd
from energy_demand.basic import testing_functions
'''
============================================
MEthod to derive GVA/POP SERVICE FLOOR AREAS
============================================

1. Step
Get correlation between regional GVA and (regional floor area/reg pop) of every sector of base year
-- Get this correlation for every region and build national correlation

2. Step
Calculate future regional floor area demand based on GVA and pop projection
'''

def disaggregate_base_demand(
        regions,
        base_yr,
        curr_yr,
        fuels,
        scenario_data,
        assumptions,
        reg_coord,
        weather_stations,
        temp_data,
        sectors,
        all_sectors,
        enduses
    ):
    """This function disaggregates fuel demand based on
    region specific parameters for the base year. The residential,
    service and industry demand is disaggregated according to
    different factors.

    Arguments
    ----------
    base_yr
    curr_yr
    fuels
    scenario_data
    assumptions
    reg_coord
    weather_stations
    temp_data
    sectors
    all_sectors
    enduses

    Returns
    -------
    data : dict
    """
    # -------------------------------------
    # Factors to choose for disaggregation
    # -------------------------------------
    # Disaggregate residential submodel data
    rs_fuel_disagg = rs_disaggregate(
        regions,
        base_yr,
        curr_yr,
        fuels['rs_fuel_raw'],
        scenario_data,
        assumptions,
        reg_coord,
        weather_stations,
        temp_data,
        enduses['rs_enduses'],
        crit_limited_disagg_pop_hdd=False,   # Only pop
        crit_limited_disagg_pop=False,      # Only pop and hdd
        crit_full_disagg=True)             # Full disaggregation

    # Disaggregate service submodel data
    ss_fuel_disagg = ss_disaggregate(
        fuels['ss_fuel_raw'],
        assumptions,
        scenario_data,
        base_yr,
        curr_yr,
        regions,
        reg_coord,
        temp_data,
        weather_stations,
        enduses['ss_enduses'],
        sectors['ss_sectors'],
        all_sectors,
        crit_limited_disagg_pop_hdd=True,   # Only pop
        crit_limited_disagg_pop=False,      # Only pop and hdd
        crit_full_disagg=True)             # Full disaggregation

    # Disaggregate industry submodel data with employment statistics
    is_fuel_disagg = is_disaggregate(
        base_yr,
        fuels['is_fuel_raw'],
        regions,
        enduses['is_enduses'],
        sectors['is_sectors'],
        scenario_data['employment_stats'],
        scenario_data,
        crit_limited_disagg_pop=False,
        crit_employment=True)

    return dict(rs_fuel_disagg), dict(ss_fuel_disagg), dict(is_fuel_disagg)

def ss_disaggregate(
        ss_national_fuel,
        assumptions,
        scenario_data,
        base_yr,
        curr_yr,
        regions,
        reg_coord,
        temp_data,
        weather_stations,
        enduses,
        sectors,
        all_sectors,
        crit_limited_disagg_pop_hdd,
        crit_limited_disagg_pop,
        crit_full_disagg
    ):
    """Disaggregate fuel for service submodel (per enduse and sector)

    Outputs
    -------
    ss_fuel_disagg : dict
        region, Enduse, Sectors
    """
    logging.debug("... disaggregate service demand")
    ss_fuel_disagg = {}

    # ---------------------------------------
    # Calculate heating degree days for regions
    # ---------------------------------------
    ss_hdd_individ_region = hdd_cdd.get_hdd_country(
        base_yr,
        curr_yr,
        regions,
        temp_data,
        assumptions['base_temp_diff_params'],
        assumptions['strategy_variables']['ss_t_base_heating_future_yr'],
        assumptions['t_bases']['ss_t_heating_by'],
        reg_coord,
        weather_stations)

    ss_cdd_individ_region = hdd_cdd.get_cdd_country(
        base_yr,
        curr_yr,
        regions,
        temp_data,
        assumptions['base_temp_diff_params'],
        assumptions['strategy_variables']['ss_t_base_cooling_future_yr'],
        assumptions['t_bases']['ss_t_cooling_by'],
        reg_coord,
        weather_stations)

    # ---------------------------------------------
    # Get all regions with missing floor area data
    # ---------------------------------------------
    regions_without_floorarea = get_regions_missing_floor_area_sector(
        regions, scenario_data['floor_area']['ss_floorarea'], base_yr)
    regions_with_floorarea = list(regions)
    for reg in regions_without_floorarea:
        regions_with_floorarea.remove(reg)

    # ---------------------------------------
    # Overall disaggregation factors per enduse and sector
    # ---------------------------------------
    ss_fuel_disagg = disagg_ss_general(
        all_regions=regions,
        regions=regions_without_floorarea,
        sectors=sectors,
        enduses=enduses,
        all_sectors=all_sectors,
        base_yr=base_yr,
        scenario_data=scenario_data,
        ss_hdd_individ_region=ss_hdd_individ_region,
        ss_cdd_individ_region=ss_cdd_individ_region,
        ss_fuel_disagg=ss_fuel_disagg,
        ss_national_fuel=ss_national_fuel,
        crit_limited_disagg_pop=False,
        crit_limited_disagg_pop_hdd=True,
        crit_full_disagg=False)

    # Substract from national fuel already disaggregated fuel
    ss_national_fuel_remaining = copy.deepcopy(ss_national_fuel)
    for enduse in ss_national_fuel:
        for sector in ss_national_fuel[enduse]:
            for reg in ss_fuel_disagg:
                ss_national_fuel_remaining[enduse][sector] -= ss_fuel_disagg[reg][enduse][sector]

    # Disaggregate with floor area
    ss_fuel_disagg = disagg_ss_general(
        all_regions=regions_with_floorarea,
        regions=regions_with_floorarea,
        sectors=sectors,
        enduses=enduses,
        all_sectors=all_sectors,
        base_yr=base_yr,
        scenario_data=scenario_data,
        ss_hdd_individ_region=ss_hdd_individ_region,
        ss_cdd_individ_region=ss_cdd_individ_region,
        ss_fuel_disagg=ss_fuel_disagg,
        ss_national_fuel=ss_national_fuel_remaining,
        crit_limited_disagg_pop=crit_limited_disagg_pop,
        crit_limited_disagg_pop_hdd=crit_limited_disagg_pop_hdd,
        crit_full_disagg=crit_full_disagg)

    '''
    # Total floor area for every enduse per sector
    national_floorarea_by_sector = {}
    for sector in sectors:
        national_floorarea_by_sector[sector] = 0
        for region in regions:
            national_floorarea_by_sector[sector] += scenario_data['floor_area']['ss_floorarea'][base_yr][region][sector]

    tot_pop = 0
    tot_floor_area = {}
    tot_floor_area_pop = {}
    tot_pop_hdd = {}
    tot_pop_cdd = {}
    for sector in all_sectors:
        tot_floor_area[sector] = 0
        tot_floor_area_pop[sector] = 0
        tot_pop_hdd[sector] = 0
        tot_pop_cdd[sector] = 0

    for region in regions:
        reg_hdd = ss_hdd_individ_region[region]
        reg_cdd = ss_cdd_individ_region[region]

        # Population
        reg_pop = scenario_data['population'][base_yr][region]

        tot_pop += reg_pop

        for sector in all_sectors:

            # Floor Area of sector
            reg_floor_area = scenario_data['floor_area']['ss_floorarea'][base_yr][region][sector]

            # National disaggregation factors
            tot_floor_area[sector] += reg_floor_area
            tot_floor_area_pop[sector] += reg_floor_area * reg_pop
            tot_pop_hdd[sector] += reg_pop * reg_hdd
            tot_pop_cdd[sector] += reg_pop * reg_cdd

    # ---------------------------------------
    # Disaggregate according to enduse
    # ---------------------------------------
    for region in regions:
        #ss_fuel_disagg[region] = {}
        ss_fuel_disagg[region] = defaultdict(dict)

        # Regional factors
        reg_hdd = ss_hdd_individ_region[region]
        reg_cdd = ss_cdd_individ_region[region]

        reg_pop = scenario_data['population'][base_yr][region]

        reg_diasg_factor = reg_pop / tot_pop

        for enduse in enduses:
            #ss_fuel_disagg[region][enduse] = {}

            for sector in sectors:
                #print("reg_diasg_factor: {} {} {}".format(sector, enduse, reg_diasg_factor))
                reg_floor_area = scenario_data['floor_area']['ss_floorarea'][base_yr][region][sector]

                if crit_limited_disagg_pop and not crit_limited_disagg_pop_hdd:
                    #logging.debug(" ... Disaggregation ss: populaton")
                    # ----
                    # Only disaggregated with population
                    # ----
                    reg_diasg_factor = reg_pop / tot_pop

                elif crit_limited_disagg_pop_hdd and not crit_full_disagg:
                    #logging.debug(" ... Disaggregation ss: populaton, HDD")
                    # ----
                    # Only disaggregat with population and hdd and cdd
                    # ----
                    if enduse == 'ss_cooling_humidification':
                        reg_diasg_factor = (reg_pop * reg_cdd) / tot_pop_cdd[sector]
                    elif enduse == 'ss_space_heating':
                        reg_diasg_factor = (reg_pop * reg_hdd) / tot_pop_hdd[sector]
                    else:
                        reg_diasg_factor = reg_pop / tot_pop
                elif crit_full_disagg:
                    #logging.debug(" ... Disaggregation ss: populaton, HDD, floor_area")
                    # ----
                    # disaggregat with pop, hdd/cdd, floor area
                    # ----
                    if enduse == 'ss_cooling_humidification':
                        reg_diasg_factor = (reg_pop * reg_cdd) / tot_pop_cdd[sector]
                    elif enduse == 'ss_space_heating':
                        reg_diasg_factor = (reg_floor_area * reg_pop) / tot_floor_area_pop[sector]
                    elif enduse == 'ss_lighting':
                        reg_diasg_factor = reg_floor_area / tot_floor_area[sector]
                    else:
                        reg_diasg_factor = reg_pop / tot_pop

                ss_fuel_disagg[region][enduse][sector] = ss_national_fuel[enduse][sector] * reg_diasg_factor
    '''
    # -----------------
    # Check if total fuel is the
    # same before and after aggregation
    #------------------
    testing_functions.control_disaggregation(
        ss_fuel_disagg, ss_national_fuel, enduses, sectors)
    logging.debug("... finished disaggregation ss")
    return dict(ss_fuel_disagg)

def disagg_ss_general(
        all_regions,
        regions,
        sectors,
        enduses,
        all_sectors,
        base_yr,
        scenario_data,
        ss_hdd_individ_region,
        ss_cdd_individ_region,
        ss_fuel_disagg,
        ss_national_fuel,
        crit_limited_disagg_pop,
        crit_limited_disagg_pop_hdd,
        crit_full_disagg
    ):
    """
    """
    # Total floor area for every enduse per sector
    national_floorarea_by_sector = {}
    for sector in sectors:
        national_floorarea_by_sector[sector] = 0
        for region in regions:
            national_floorarea_by_sector[sector] += scenario_data['floor_area']['ss_floorarea'][base_yr][region][sector]

    tot_pop = 0
    tot_floor_area = {}
    tot_floor_area_pop = {}
    tot_pop_hdd = {}
    tot_pop_cdd = {}
    for sector in all_sectors:
        tot_floor_area[sector] = 0
        tot_floor_area_pop[sector] = 0
        tot_pop_hdd[sector] = 0
        tot_pop_cdd[sector] = 0

    for region in all_regions:
        reg_hdd = ss_hdd_individ_region[region]
        reg_cdd = ss_cdd_individ_region[region]

        # Population
        reg_pop = scenario_data['population'][base_yr][region]

        tot_pop += reg_pop

        for sector in all_sectors:

            # Floor Area of sector
            reg_floor_area = scenario_data['floor_area']['ss_floorarea'][base_yr][region][sector]

            # National disaggregation factors
            tot_floor_area[sector] += reg_floor_area
            tot_floor_area_pop[sector] += reg_floor_area * reg_pop
            tot_pop_hdd[sector] += reg_pop * reg_hdd
            tot_pop_cdd[sector] += reg_pop * reg_cdd

    # ---------------------------------------
    # Disaggregate according to enduse
    # ---------------------------------------
    for region in regions:
        #ss_fuel_disagg[region] = {}
        ss_fuel_disagg[region] = defaultdict(dict)

        # Regional factors
        reg_hdd = ss_hdd_individ_region[region]
        reg_cdd = ss_cdd_individ_region[region]

        reg_pop = scenario_data['population'][base_yr][region]

        reg_diasg_factor = reg_pop / tot_pop

        for enduse in enduses:
            #ss_fuel_disagg[region][enduse] = {}

            for sector in sectors:
                #print("reg_diasg_factor: {} {} {}".format(sector, enduse, reg_diasg_factor))
                reg_floor_area = scenario_data['floor_area']['ss_floorarea'][base_yr][region][sector]

                if crit_limited_disagg_pop and not crit_limited_disagg_pop_hdd:
                    #logging.debug(" ... Disaggregation ss: populaton")
                    # ----
                    # Only disaggregated with population
                    # ----
                    reg_diasg_factor = reg_pop / tot_pop

                elif crit_limited_disagg_pop_hdd and not crit_full_disagg:
                    #logging.debug(" ... Disaggregation ss: populaton, HDD")
                    # ----
                    # Only disaggregat with population and hdd and cdd
                    # ----
                    if enduse == 'ss_cooling_humidification':
                        reg_diasg_factor = (reg_pop * reg_cdd) / tot_pop_cdd[sector]
                    elif enduse == 'ss_space_heating':
                        reg_diasg_factor = (reg_pop * reg_hdd) / tot_pop_hdd[sector]
                    else:
                        reg_diasg_factor = reg_pop / tot_pop
                elif crit_full_disagg:
                    #logging.debug(" ... Disaggregation ss: populaton, HDD, floor_area")
                    # ----
                    # disaggregat with pop, hdd/cdd, floor area
                    # ----
                    if enduse == 'ss_cooling_humidification':
                        reg_diasg_factor = (reg_pop * reg_cdd) / tot_pop_cdd[sector]
                    elif enduse == 'ss_space_heating':
                        reg_diasg_factor = (reg_floor_area * reg_pop) / tot_floor_area_pop[sector]
                    elif enduse == 'ss_lighting':
                        reg_diasg_factor = reg_floor_area / tot_floor_area[sector]
                    else:
                        reg_diasg_factor = reg_pop / tot_pop

                ss_fuel_disagg[region][enduse][sector] = ss_national_fuel[enduse][sector] * reg_diasg_factor

    return ss_fuel_disagg

def is_disaggregate(
        base_yr,
        is_national_fuel,
        regions,
        enduses,
        sectors,
        employment_statistics,
        scenario_data,
        crit_limited_disagg_pop,
        crit_employment
    ):
    """Disaggregate industry related fuel for sector and enduses with
    employment statistics

    base_yr : int
        Base year
    is_national_fuel : 
    regions,
    enduses,
    sectors,
    employment_statistics,
    scenario_data,
    crit_limited_disagg_pop,
    crit_employment

    Returns
    ---------
    is_fuel_disagg : dict
        reg, enduse, sector
    """
    logging.debug("... disaggregate industry demand")

    is_fuel_disagg = {}
    if crit_limited_disagg_pop and not crit_employment:
        #logging.debug(" ... Disaggregation is: Population")
        # ---
        # Disaggregate only with population
        # ---
        tot_pop = 0
        for reg in regions:
            tot_pop += scenario_data['population'][base_yr][reg]

        for region in regions:
            is_fuel_disagg[region] = {}
            reg_pop = scenario_data['population'][base_yr][region]

            reg_disagg_f = reg_pop / tot_pop

            for enduse in enduses:
                is_fuel_disagg[region][enduse] = {}
                for sector in sectors:
                    is_fuel_disagg[region][enduse][sector] = is_national_fuel[enduse][sector] * reg_disagg_f

        return is_fuel_disagg

    elif crit_employment:
        #logging.debug(" ... Disaggregation is: Employment statistics")

        # Calculate total population
        tot_pop = 0
        for reg in regions:
            tot_pop += scenario_data['population'][base_yr][reg]

        # -----
        # Disaggregate with employment statistics
        # The BEIS sectors are matched with census data sectors {ECUK industry sectors: 'Emplyoment sectors'}
        '''sectormatch_ecuk_with_census = {
            'wood': 'C16,17',
            'textiles': 'C13-15',
            'chemicals': 'C19-22',
            'printing': 'C',
            'electrical_equipment':'C26-30',
            'paper': 'C16,17',
            'basic_metals': 'C',
            'beverages': 'C10-12',
            'pharmaceuticals': 'M',
            'machinery': 'C26-30',
            'water_collection_treatment': 'E',
            'food_production': 'C10-12',
            'rubber_plastics': 'C19-22',
            'wearing_appeal': 'C13-15',
            'other_transport_equipment': 'H',
            'leather': 'C13-15',
            'motor_vehicles': 'G',
            'waste_collection': 'E',
            'tobacco': 'C10-12',
            'mining': 'B',
            'other_manufacturing': 'C18,31,32',
            'furniture': 'C',
            'non_metallic_mineral_products': 'C',
            'computer': 'C26-30',
            'fabricated_metal_products': 'C'}'''

        sectormatch_ecuk_with_census = {
            'mining': 'B',                  # Improvement
            'food_production': 'C10-12',    # Improvement
            'pharmaceuticals': 'M',         # Improvements
            'computer': 'C26-30',           # Improvements
            'leather': 'C13-15',            # Gas improve, electrectiy same
            'wearing_appeal': 'C13-15',     # Improvements

            'electrical_equipment': None,   # 'C26-30', #Streuung besser
            'wood': None,                   #Worse
            'textiles': None,               #Worse
            'chemicals': None,              #Worse better streuung
            'printing': None,               #Streeung besser
            'paper': None,                  #WORSE
            'basic_metals': None,           #improve deviation
            'beverages': None,
            'fabricated_metal_products': None,
            'other_manufacturing': None,
            'furniture': None,
            'machinery': None,     # Improvements with M #BUT NOT REALLY CORRECT CLASSIFICATION
            'water_collection_treatment': None,
            'rubber_plastics': None, #not really, bessere Streeung
            'other_transport_equipment': None,
            'motor_vehicles': None,
            'waste_collection': None, #about the same with F
            'tobacco': None,
            'non_metallic_mineral_products': None  #Worsen
        }

        # ----------------------------------------
        # Summarise national employment per sector
        # ----------------------------------------
        # Initialise dict
        tot_national_sector_employment = {}
        for sectors_reg in employment_statistics.values():
            for sector in sectors_reg:
                tot_national_sector_employment[sector] = 0
            continue
        for reg in regions:
            for employment_sector, employment in employment_statistics[reg].items():
                tot_national_sector_employment[employment_sector] += employment

        # --------------------------------------------------
        # Disaggregate per region with employment statistics
        # --------------------------------------------------
        for region in regions:
            is_fuel_disagg[region] = {}

            # Iterate sector
            for enduse in enduses:
                is_fuel_disagg[region][enduse] = {}

                for sector in sectors:

                    # ---------------------------------
                    # Try to match  with sector, otherwise disaggregate with population
                    # ----------------------------------
                    matched_sector = sectormatch_ecuk_with_census[sector]

                    # Disaggregate with population
                    if matched_sector == None:
                        
                        reg_pop = scenario_data['population'][base_yr][region]
                        
                        reg_disag_factor = reg_pop / tot_pop

                        is_fuel_disagg[region][enduse][sector] = is_national_fuel[enduse][sector] * reg_disag_factor
                    else:
                        #for enduse in enduses['is_enduses']:
                        national_sector_employment = tot_national_sector_employment[matched_sector]
                        reg_sector_employment = employment_statistics[region][matched_sector]

                        try:
                            reg_disag_factor = reg_sector_employment / national_sector_employment
                        except ZeroDivisionError:
                            reg_disag_factor = 0 #No employment for this sector for this region

                        # Disaggregated national fuel
                        is_fuel_disagg[region][enduse][sector] = is_national_fuel[enduse][sector] * reg_disag_factor

    # -----------------
    # TESTING Check if total fuel is the same before and after aggregation
    #------------------
    testing_functions.control_disaggregation(
        is_fuel_disagg,
        is_national_fuel,
        enduses,
        sectors)

    logging.debug("... finished disaggregateing industry demand")
    return is_fuel_disagg

def rs_disaggregate(
        regions,
        base_yr,
        curr_yr,
        rs_national_fuel,
        scenario_data,
        assumptions,
        reg_coord,
        weather_stations,
        temp_data,
        enduses,
        crit_limited_disagg_pop_hdd,
        crit_limited_disagg_pop,
        crit_full_disagg
    ):
    """Disaggregate residential fuel demand

    Arguments
    ----------
    regions : dict
        Regions
    sim_param : dict
        Simulation parameters
    rs_national_fuel : dict
        Fuel per enduse for residential submodel

    Returns
    -------
    rs_fuel_disagg : dict
        Disaggregated fuel per enduse for every region (fuel[region][enduse])

    Note
    -----
    Used disaggregation factors for residential according
    to enduse (see Documentation)
    """
    logging.debug("... disagreggate residential demand")

    rs_fuel_disagg = defaultdict(dict)

    # ---------------------------------------
    # Calculate heating degree days for regions
    # ---------------------------------------
    rs_hdd_individ_region = hdd_cdd.get_hdd_country(
        base_yr,
        curr_yr,
        regions,
        temp_data,
        assumptions['base_temp_diff_params'],
        assumptions['strategy_variables']['rs_t_base_heating_future_yr'],
        assumptions['t_bases']['rs_t_heating_by'],
        reg_coord,
        weather_stations)

    # ---------------------------------------
    # Overall disaggregation factors per enduse
    # ---------------------------------------
    # HERE

    # Get all regions with missing floor area data
    regions_without_floorarea = get_regions_missing_floor_area(
        regions, scenario_data['floor_area']['rs_floorarea'], base_yr)
    regions_with_floorarea = list(regions)
    for reg in regions_without_floorarea:
        regions_with_floorarea.remove(reg)
    #print("regions_without_floorarea")
    #print(regions_without_floorarea)
    #prnt("")
    # ====================================
    # Disaggregate for region without floor area with population
    # ====================================
    rs_fuel_disagg = disagg_rs_general(
        all_regions=regions,
        regions=regions_without_floorarea,
        base_yr=base_yr,
        rs_hdd_individ_region=rs_hdd_individ_region,
        scenario_data=scenario_data,
        rs_fuel_disagg=rs_fuel_disagg,
        rs_national_fuel=rs_national_fuel,
        crit_limited_disagg_pop=False,
        crit_limited_disagg_pop_hdd=True,
        crit_full_disagg=False)

    # Substract from national fuel already disaggregated fuel
    rs_national_fuel_remaining = copy.deepcopy(rs_national_fuel)
    for enduse in rs_national_fuel:
        for reg in rs_fuel_disagg:
            rs_national_fuel_remaining[enduse] = rs_national_fuel_remaining[enduse] - rs_fuel_disagg[reg][enduse]

    # ====================================
    # Disaggregate for region with floor area
    # ====================================
    rs_fuel_disagg = disagg_rs_general(
        all_regions=regions_with_floorarea,
        regions=regions_with_floorarea,
        base_yr=base_yr,
        rs_hdd_individ_region=rs_hdd_individ_region,
        scenario_data=scenario_data,
        rs_fuel_disagg=rs_fuel_disagg,
        rs_national_fuel=rs_national_fuel_remaining,
        crit_limited_disagg_pop=crit_limited_disagg_pop,
        crit_limited_disagg_pop_hdd=crit_limited_disagg_pop_hdd,
        crit_full_disagg=crit_full_disagg)
    
    '''

    total_pop = 0
    total_hdd_floorarea = 0
    total_floor_area = 0

    for region in regions:

        # HDD
        reg_hdd = rs_hdd_individ_region[region]

        # Floor Area across all sectors
        reg_floor_area = scenario_data['floor_area']['rs_floorarea'][base_yr][region]

        # Population
        reg_pop = scenario_data['population'][base_yr][region]

        # National dissagregation factors
        total_pop += reg_pop
        total_hdd_floorarea += reg_hdd * reg_floor_area
        total_floor_area += reg_floor_area
        #TODO: GVA?

    # ---------------------------------------
    # Disaggregate according to enduse
    # ---------------------------------------
    for region in regions:
        reg_pop = scenario_data['population'][base_yr][region]
        reg_hdd = rs_hdd_individ_region[region]
        reg_floor_area = scenario_data['floor_area']['rs_floorarea'][base_yr][region]

        # Disaggregate fuel depending on end_use
        for enduse in rs_national_fuel:
            if crit_limited_disagg_pop and not crit_limited_disagg_pop_hdd and not crit_full_disagg:
                #logging.debug(" ... Disaggregation rss: populaton")
                # ----------------------------------
                # Only disaggregate with population
                # ----------------------------------
                reg_diasg_factor = reg_pop / total_pop

            elif crit_limited_disagg_pop_hdd and not crit_full_disagg:
                #logging.debug(" ... Disaggregation rss: populaton, hdd")
                # -------------------
                # Disaggregation with pop and hdd
                # -------------------
                if enduse == 're_space_heating':
                    reg_diasg_factor = (reg_hdd * reg_pop) / total_hdd_floorarea
                else:
                    reg_diasg_factor = reg_pop / total_pop
            elif crit_full_disagg:
                logging.warning(" ... Disaggregation rss: populaton, hdd, floor_area")
                # -------------------
                # Full disaggregation
                # -------------------
                if enduse == 'rs_space_heating':
                    reg_diasg_factor = (reg_hdd * reg_floor_area) / total_hdd_floorarea
                elif enduse == 'rs_lighting':
                    reg_diasg_factor = reg_floor_area / total_floor_area
                else:
                    reg_diasg_factor = reg_pop / total_pop

            # Disaggregate
            rs_fuel_disagg[region][enduse] = rs_national_fuel[enduse] * reg_diasg_factor
    # HERE
    '''
    # -----------------
    # Check if total fuel is the same before and after aggregation
    #------------------
    testing_functions.control_disaggregation(rs_fuel_disagg, rs_national_fuel, enduses)

    return rs_fuel_disagg

def disagg_rs_general(
        all_regions,
        regions,
        base_yr,
        rs_hdd_individ_region,
        scenario_data,
        rs_fuel_disagg,
        rs_national_fuel,
        crit_limited_disagg_pop,
        crit_limited_disagg_pop_hdd,
        crit_full_disagg
    ):
    """
    """
    total_pop = 0
    total_hdd_floorarea = 0
    total_floor_area = 0

    for region in all_regions:

        # HDD
        reg_hdd = rs_hdd_individ_region[region]

        # Floor Area across all sectors
        reg_floor_area = scenario_data['floor_area']['rs_floorarea'][base_yr][region]

        # Population
        reg_pop = scenario_data['population'][base_yr][region]

        # National dissagregation factors
        total_pop += reg_pop
        total_hdd_floorarea += reg_hdd * reg_floor_area
        total_floor_area += reg_floor_area
        #TODO: GVA?

    # ---------------------------------------
    # Disaggregate according to enduse
    # ---------------------------------------
    for region in regions:
        reg_pop = scenario_data['population'][base_yr][region]
        reg_hdd = rs_hdd_individ_region[region]
        reg_floor_area = scenario_data['floor_area']['rs_floorarea'][base_yr][region]

        # Disaggregate fuel depending on end_use
        for enduse in rs_national_fuel:
            if crit_limited_disagg_pop and not crit_limited_disagg_pop_hdd and not crit_full_disagg:
                #logging.debug(" ... Disaggregation rss: populaton")
                # ----------------------------------
                # Only disaggregate with population
                # ----------------------------------
                reg_diasg_factor = reg_pop / total_pop

            elif crit_limited_disagg_pop_hdd and not crit_full_disagg:
                #logging.debug(" ... Disaggregation rss: populaton, hdd")
                # -------------------
                # Disaggregation with pop and hdd
                # -------------------
                if enduse == 're_space_heating':
                    reg_diasg_factor = (reg_hdd * reg_pop) / total_hdd_floorarea
                else:
                    reg_diasg_factor = reg_pop / total_pop
            elif crit_full_disagg:
                logging.warning(" ... Disaggregation rss: populaton, hdd, floor_area")
                # -------------------
                # Full disaggregation
                # -------------------
                if enduse == 'rs_space_heating':
                    reg_diasg_factor = (reg_hdd * reg_floor_area) / total_hdd_floorarea
                elif enduse == 'rs_lighting':
                    reg_diasg_factor = reg_floor_area / total_floor_area
                else:
                    reg_diasg_factor = reg_pop / total_pop

            # Disaggregate
            rs_fuel_disagg[region][enduse] = rs_national_fuel[enduse] * reg_diasg_factor
    return rs_fuel_disagg

def write_disagg_fuel(path_to_txt, data):
    """Write out disaggregated fuel

    Arguments
    ----------
    path_to_txt : str
        Path to txt file
    data : dict
        Data to write out
    """
    file = open(path_to_txt, "w")
    file.write("{}, {}, {}, {}".format(
        'region', 'enduse', 'fueltypes', 'fuel') + '\n'
              )

    for region, enduses in data.items():
        for enduse, fuels in enduses.items():
            for fueltype, fuel in enumerate(fuels):
                file.write("{}, {}, {}, {}".format(
                    str.strip(region),
                    str.strip(enduse),
                    str(int(fueltype)),
                    str(float(fuel)) + '\n'))
    file.close()

    return

def write_disagg_fuel_ts(path_to_txt, data):
    """Write out disaggregated fuel

    Arguments
    ----------
    path_to_txt : str
        Path to txt file
    data : dict
        Data to write out
    """
    file = open(path_to_txt, "w")
    file.write("{}, {}, {}".format(
        'region', 'fueltypes', 'fuel') + '\n'
              )

    for region, fuels in data.items():
        for fueltype, fuel in enumerate(fuels):
            file.write("{}, {}, {}".format(
                str.strip(region), str(int(fueltype)), str(float(fuel)) + '\n')
                      )
    file.close()

    return

def write_disagg_fuel_sector(path_to_txt, data):
    """Write out disaggregated fuel

    Arguments
    ----------
    path_to_txt : str
        Path to txt file
    data : dict
        Data to write out
    """
    file = open(path_to_txt, "w")
    file.write("{}, {}, {}, {}, {}".format(
        'region', 'enduse', 'sector', 'fueltypes', 'fuel') + '\n')

    for region, sectors in data.items():
        for sector, enduses in sectors.items():
            for enduse, fuels in enduses.items():
                for fueltype, fuel in enumerate(fuels):
                    file.write("{}, {}, {}, {}, {}".format(
                        str.strip(region),
                        str.strip(enduse),
                        str.strip(sector),
                        str(int(fueltype)),
                        str(float(fuel)) + '\n')
                              )
    file.close()

    return

def run(data):
    """Function run script
    """
    logging.debug("... start script %s", os.path.basename(__file__))

    # Disaggregation
    rs_fuel_disagg, ss_fuel_disagg, is_fuel_disagg = disaggregate_base_demand(
        data['regions'],
        data['sim_param']['base_yr'],
        data['sim_param']['curr_yr'],
        data['fuels'],
        data['scenario_data'],
        data['assumptions'],
        data['reg_coord'],
        data['weather_stations'],
        data['temp_data'],
        data['sectors'],
        data['sectors']['all_sectors'],
        data['enduses'])

    #Write to csv file disaggregated demand
    write_disagg_fuel(
        os.path.join(data['local_paths']['dir_disaggregated'], 'rs_fuel_disagg.csv'),
        rs_fuel_disagg)
    write_disagg_fuel_sector(
        os.path.join(data['local_paths']['dir_disaggregated'], 'ss_fuel_disagg.csv'),
        ss_fuel_disagg)
    write_disagg_fuel_sector(
        os.path.join(data['local_paths']['dir_disaggregated'], 'is_fuel_disagg.csv'),
        is_fuel_disagg)

    logging.debug("... finished script %s", os.path.basename(__file__))
    return

def get_regions_missing_floor_area(regions, floor_area_data, base_yr):
    """Get all regions where floorarea cannot be used for disaggregation
    """
    regions_no_floor_area_data = []

    for region in regions:

        # Floor Area across all sectors
        reg_floor_area = floor_area_data[base_yr][region]

        if reg_floor_area == 1: #As dfined with 'null' in readigng in
            regions_no_floor_area_data.append(region)

    return regions_no_floor_area_data

def get_regions_missing_floor_area_sector(regions, floor_area_data, base_yr):
    """Get all regions where floorarea cannot be used for disaggregation
    """
    regions_no_floor_area_data = []

    for region in regions:

        # Floor Area across all sectors
        reg_floor_area_sectors = floor_area_data[base_yr][region]

        not_data = False
        for sector_data in reg_floor_area_sectors.values():
            if sector_data == 1: #As dfined with 'null' in readigng in
                not_data = True
        if not_data:
            regions_no_floor_area_data.append(region)

    return regions_no_floor_area_data