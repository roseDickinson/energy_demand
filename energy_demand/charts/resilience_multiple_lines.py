"""Plot min and max days from reading in multiple days of different scenario
"""
import csv
import os
from collections import defaultdict
import matplotlib.pyplot as plt
from energy_demand.plotting import plotting_styles
from energy_demand.plotting import plotting_results
from energy_demand.plotting import plotting_program
from energy_demand.read_write import write_data
from energy_demand.basic import basic_functions

def read_csv_max_min(path_to_csv):
    out_dict = {}
    with open(path_to_csv, 'r') as csvfile:
        rows = csv.reader(csvfile, delimiter=',')

        for row in rows:
            out_dict["yearday"] = row
            break
        for row in rows:
            out_dict["date"] = row
            break

        values_list = []
        for line_nr, row in enumerate(rows):
            values_list.append(float(row[0]))

        out_dict["values_list"] = values_list

    return out_dict

def read_csv_average(path_to_csv):
    """read average value from csv
    """
    out_dict = {}
    with open(path_to_csv, 'r') as csvfile:
        rows = csv.reader(csvfile, delimiter=',')
        
        for row in rows:
            out_dict["name"] = row
            break
        for row in rows:
            out_dict["average_value"] = row[0]
            break

    return out_dict

def generate_min_max_resilience_plot(path_to_scenarios):
    # Iterate result folder


    # Get all folders with scenario run results (name of folder is scenario)
    scenarios = os.listdir(path_to_scenarios)

    data_container = {}
    statistics_to_print = ["scenario \tmin \tmax \tdiff \tDate maximum day \tDate minimum day \tMax hour \tMin hour", "=============================", " "]

    for scenario in scenarios:
        if scenario == '__results_resilience':
            pass
        else:

            # ----
            # Read in min and max day
            # ----
            path_fist_scenario = os.path.join(path_to_scenarios, scenario)

            data_container[scenario] = defaultdict(dict)

            # Folders with Resilience min and max day
            result_folder = os.path.join(path_fist_scenario, "model_run_results_txt", "resilience_paper")

            result_files = os.listdir(result_folder)

            # Get all max day files
            for result_file in result_files:

                if result_file.split("__")[0] != 'result_day':
                    
                    # Get average value from file
                    if result_file == 'average_nr.csv':
                        average_demands_dict = read_csv_average(os.path.join(result_folder, result_file))
                        average_demands_by = float(average_demands_dict['average_value'])
                    else:
                        pass
                else:
                    if result_file.split("__")[0] == 'result_day' and result_file.split("__")[1] == 'max':
                        dict_values = read_csv_max_min(os.path.join(result_folder, result_file))
                        year = int(result_file.split("__")[2])
                        data_container[scenario][year]['max_values'] = dict_values['values_list']
                        data_container[scenario][year]['max_yearday'] = dict_values['yearday']
                        data_container[scenario][year]['max_date'] = dict_values['date']

                        # Get position in list (hour) of maximum value
                        data_container[scenario][year]['max_h'] = dict_values['values_list'].index(max(dict_values['values_list']))

                    elif result_file.split("__")[0] == 'result_day' and result_file.split("__")[1] == 'min':
                        dict_values = read_csv_max_min(os.path.join(result_folder, result_file))
                        year = int(result_file.split("__")[2])
                        data_container[scenario][year]['min_values'] = dict_values['values_list']
                        data_container[scenario][year]['min_yearday'] = dict_values['yearday']
                        data_container[scenario][year]['min_date'] = dict_values['date']
                        
                        # Get position in list (hour) of min value
                        data_container[scenario][year]['min_h'] = dict_values['values_list'].index(min(dict_values['values_list']))

    # ------------------
    # Calculate statistics
    # --------------------
    for scenario in data_container.keys():
        statistics_to_print.append("{} \t{} \t{} \t{} \t{} \t{} \t{} \t{}".format(
            scenario,
            round(min(data_container[scenario][year]['min_values']), 2),
            round(max(data_container[scenario][year]['max_values']), 2),
            round(max(data_container[scenario][year]['max_values']) - min(data_container[scenario][year]['min_values']), 2),
            data_container[scenario][year]['max_date'],
            data_container[scenario][year]['min_date'],
            data_container[scenario][year]['max_h'],
            data_container[scenario][year]['min_h'],
            ))

    # Average demand of base year
    flat_y_data = 24 * [average_demands_by]

    # ------------------
    # Write statiscs to txt
    # --------------------
    basic_functions.create_folder(path_to_scenarios, "__results_resilience")

    write_data.write_list_to_txt(
        os.path.join(path_to_scenarios, "__results_resilience", "statistics.txt"),
        statistics_to_print)

    # ------------------------------------------------
    # Create maximum plot
    # ------------------------------------------------
    ymax = 60
    line_width = 1.0
    color_flat_line = 'red' #darkkhaki'
    fig_name = os.path.join(path_to_scenarios, "__results_resilience", "max_days.pdf")

    colors = plotting_styles.color_list_resilience()
    fig = plt.figure(
        figsize=plotting_program.cm2inch(8, 8)) #width, height

    for counter, (scenario, scenario_data) in enumerate(data_container.items()):
        x_data = range(24)
    
        # Take last simluated year
        plot_yr = list(scenario_data.keys())[-1]

        # Plot base year line
        if counter == 0:
            x_data_smoothed, y_data_smoothed = plotting_results.smooth_data(x_data, scenario_data[2015]['max_values'], num=40000)
            plt.plot(
                x_data_smoothed,
                list(y_data_smoothed),
                color='black',
                linestyle='-',
                linewidth=1.5,
                label='{}__{}'.format(scenario, plot_yr))

            # Add flat line
            plt.plot(
                x_data,
                list(flat_y_data),
                color=color_flat_line,
                linestyle='--',
                linewidth=0.5,
                label='{}__{}'.format("flat", 2015))


        y_data = scenario_data[plot_yr]['max_values']

        # smooth line
        x_data_smoothed, y_data_smoothed = plotting_results.smooth_data(x_data, y_data, num=40000)
        plt.plot(
            x_data_smoothed,
            list(y_data_smoothed),
            color=colors[counter],
            linestyle='--',
            linewidth=line_width,
            label='{}__{}'.format(scenario, plot_yr))

    plt.tight_layout()
    plt.ylim(ymin=0, ymax=ymax)
    plt.xlim(xmin=0, xmax=23)

    # Legend #https://stackoverflow.com/questions/4700614/how-to-put-the-legend-out-of-the-plot
    ax = plt.subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9])

    # Put a legend below current axis
    ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, -0.1),
        fancybox=False,
        shadow=False,
        ncol=2,
        prop={
            'family': 'arial',
            'size': 4})

    plt.savefig(fig_name)

    # ------------------------------------------------
    # Create minimum plot
    # ------------------------------------------------
    fig_name = os.path.join(path_to_scenarios, "__results_resilience", "min_days.pdf")

    colors = plotting_styles.color_list_resilience()
    fig = plt.figure(
        figsize=plotting_program.cm2inch(8, 8)) #width, height

    for counter, (scenario, scenario_data) in enumerate(data_container.items()):
        x_data = range(24)

        # Take last simluated year
        plot_yr = list(scenario_data.keys())[-1]
    
        # Plot base year line
        if counter == 0:
            x_data_smoothed, y_data_smoothed = plotting_results.smooth_data(x_data, scenario_data[2015]['min_values'], num=40000)
            plt.plot(
                x_data_smoothed,
                list(y_data_smoothed),
                color='black',
                linestyle='-',
                linewidth=1.5,
                label='{}__{}'.format(scenario, plot_yr))

            # Add flat line
            plt.plot(
                x_data,
                list(flat_y_data),
                color=color_flat_line,
                linestyle='--',
                linewidth=0.5,
                label='{}__{}'.format("flat", 2015))

        y_data = scenario_data[plot_yr]['min_values']

        # smooth line
        x_data_smoothed, y_data_smoothed = plotting_results.smooth_data(x_data, y_data, num=40000)
        plt.plot(
            x_data_smoothed,
            list(y_data_smoothed),
            color=colors[counter],
            linestyle='--',
            linewidth=line_width,
            label='{}__{}'.format(scenario, plot_yr))

    plt.tight_layout()
    plt.ylim(ymin=0, ymax=ymax)
    plt.xlim(xmin=0, xmax=23)

    # Legend #https://stackoverflow.com/questions/4700614/how-to-put-the-legend-out-of-the-plot
    ax = plt.subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9])

    # Put a legend below current axis
    ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, -0.1),
        fancybox=False,
        shadow=False,
        ncol=2,
        prop={
            'family': 'arial',
            'size': 4})

    plt.savefig(fig_name)

    print("---------------------------------")
    print("Finished resilience_multiple_lines")
    print("---------------------------------")

# Execute script
generate_min_max_resilience_plot(
    path_to_scenarios="C://Users//cenv0553//ED//results//_resilience_paper_results")
