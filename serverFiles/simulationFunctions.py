# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions for running the Flusim simulation

# Note that this file assumes it's just outside the smrg-flusim folder

# Imports
import time
import datetime
import os
import sys
from argparse import Namespace
import json
import logging
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from serverFiles.ModelSchema import modelGuideFile

# Change this if file location relative to Flusim changes
simLocation = ''

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(os.path.join(os.getcwd(), simLocation, 'src/toolbox'))

# Flusim Simulation Imports
from ToolboxConfiguration import ToolboxConfiguration
from commands.Run.RunCommand import RunCommand
from commands.epidemic import EpidemicCurveCommand
from commands.ASIRAnalysis import AsirCommand
from analysis.AnalysisStat import AnalysisStat

# Logging
functionLog = logging.getLogger(__name__)

# Define config early
toolboxConfig = ToolboxConfiguration('conf/toolbox_config.json')





# Function to generate the required toolbox config file
def generateToolboxConfig(id, joint):
    toolboxConfigSettings = {
        "simulator_executable": "src/simulator/build/src/simulator",
        "baseline_file": "conf/simulation.baseline.json",
        "middle_joint": joint,
        "set_id_joint": "-",
        "event_suffix": ".sqlite",
        "input_directory": "results/",
        "output_directory": "post-analysis",
        "communities": [
            {
                "name": "newcastle",
                "path": "communities/newcastle2011"
            },
            {
                "name": "cairns",
                "path": "communities/cairns2011"
            },
            {
                "name": "integration",
                "path": "integration/community"
            }
        ]
    }
    toolboxConfigPath = f'serverFiles/toolbox_config_{id}.json'
    print((
        '[generateToolboxConfig] Generating toolbox '
        f'configuration file {toolboxConfigPath}'
    ))
    with open(toolboxConfigPath, 'w') as file: json.dump(
        toolboxConfigSettings, file
    )
    return toolboxConfigPath


# Function to run the simulation using the given config files
def runSimulation(configData: modelGuideFile):
    # Save guide file to JSON
    sessionID = configData.description
    guidePath = f'serverFiles/flusim-{sessionID}.guide.json'
    with open(guidePath, 'w') as file: file.write(
        configData.model_dump_json(indent = 4, exclude_unset = True)
    )
    
    # Run the simulation
    RunCommand().run_command(Namespace(guide = guidePath), toolboxConfig)

    """# Modified toolbox function code for running the model
    startTime = time.monotonic()

    # C++ code is multithreaded, so we don't need extra threading here
    # TODO: Use toolbox config with updated middle joint, if necessary
    queueBuilder = ScenarioBuilder(toolboxConfig, guidePath)
    for scenario in queueBuilder.generateScenarios(): scenario.run()

    duration = time.monotonic() - startTime
    formattedDuration = str(datetime.timedelta(seconds = round(duration)))
    functionLog.info(
        f'[runSimulation] All simulations completed in {formattedDuration}'
    )"""

    # Get list of sim files so they can be deleted once the 
    # simulation and analysis are complete
    simFiles = [
        os.path.join(simLocation, 'results', ((
            f'{configData.community_used[0]}{configData.middle_joint}'
            f'{configData.simulation_sets[0].version}-0{i + 1}.sqlite'
        ))) 
        for i in range(len(configData.simulation_sets[0].simulations))
    ]

    # Return required files so they can be deleted later
    return simFiles + [guidePath]



# Function for epidemic toolbox function
def epidemic(
    communityName, joint, id, summaryStat = AnalysisStat.MEDIAN, 
    cumulative = False, byAge = False
):
    # Run epidemic analysis
    epidemicArgs = Namespace(
        community = communityName, set = id, 
        calculate_stat = summaryStat, 
        cumulative_sum = cumulative, by_age = byAge, 
        moving_average_window = 7, scale = 1, by_strain = False, 
        age_adjusted = None, split_output = False, filenames = []
    )
    print(
        f'[epidemic] Running "epidemic" analysis for set {id} [{summaryStat}]', 
        '[cumulative]' if cumulative else '[individual]', 
        '[age-separated]' if byAge else '[age-combined]'
    )
    EpidemicCurveCommand().run_command(epidemicArgs, toolboxConfig)

    # Return the name of the newly processed file
    filename = ((
        f'{communityName}{joint}-epidemic-'
        f'{'cumulative-' if cumulative else ''}{summaryStat}.csv'
    ))
    return os.path.join(simLocation, f'post-analysis/{filename}')

# Function for asir toolbox function
def asir(
    communityName, joint, id, summaryStat = AnalysisStat.MEDIAN, 
    getProportion = False, onlyIndigenous = False, onlyPregnant = False, 
    onlyVaccinated = False
):
    # Run epidemic analysis
    asirArgs = Namespace(
        community = communityName, set = id, calculate_stat = summaryStat, 
        proportion = getProportion, indigenous = onlyIndigenous, 
        pregnant = onlyPregnant, vaccinated = onlyVaccinated, filenames = []
    )
    print(
        f'[asir] Running "asir" analysis for set {id} [{summaryStat}]', 
        '[proportionate]' if getProportion else '[discrete]', 
        '[indigenous only]' if onlyIndigenous else '[all demographics]', 
        '[pregnant only]' if onlyIndigenous else '[all pregnant status]', 
        '[vaccinated only]' if onlyIndigenous else '[all vaccine status]', 
    )
    AsirCommand().run_command(asirArgs, toolboxConfig)

    # Return the name of the newly processed file
    filename = f'{communityName}{joint}-asir-{summaryStat}.csv'
    return os.path.join(simLocation, f'post-analysis/{filename}')