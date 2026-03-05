# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions for running the Flusim simulation

# Note that this file assumes it's just outside the smrg-flusim folder

# Imports
import json
import logging
import os
import sys
from argparse import Namespace

import pandas as pd
from logger import LogLevel

from serverFiles.ModelSchema import modelGuideFile

# Change this if file location relative to Flusim changes
simLocation = ""

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(os.path.join(os.getcwd(), simLocation, "src/toolbox"))

# Logging
functionLog = logging.getLogger(__name__)


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
            {"name": "newcastle", "path": "communities/newcastle2011"},
            {"name": "cairns", "path": "communities/cairns2011"},
            {"name": "integration", "path": "integration/community"},
        ],
    }
    toolboxConfigPath = f"serverFiles/toolbox_config_{id}.json"
    print(
        (
            "[generateToolboxConfig] Generating toolbox "
            f"configuration file {toolboxConfigPath}"
        )
    )
    with open(toolboxConfigPath, "w") as file:
        json.dump(toolboxConfigSettings, file, indent=2)
    return toolboxConfigPath


# Function to run the simulation using the given config files
def runSimulation(configData: modelGuideFile, toolboxPath):
    from commands.Run.RunCommand import RunCommand
    from ToolboxConfiguration import ToolboxConfiguration

    # Get toolbox config
    toolboxConfig = ToolboxConfiguration(toolboxPath)

    # Save guide file to JSON
    sessionID = configData.description
    guidePath = f"serverFiles/flusim-{sessionID}.guide.json"
    with open(guidePath, "w") as file:
        file.write(configData.model_dump_json(indent=2, exclude_unset=True))

    # Run the simulation
    RunCommand().run_command(
        Namespace(guide=guidePath, log_level=LogLevel.DEBUG), toolboxConfig
    )

    # Get list of sim files so they can be deleted once the
    # simulation and analysis are complete
    simFiles = [
        os.path.join(
            simLocation,
            "results",
            (
                (
                    f"{configData.community_used[0]}{configData.middle_joint}"
                    f"{configData.simulation_sets[0].version}-0{i}.sqlite"
                )
            ),
        )
        for i in range(len(configData.simulation_sets[0].simulations))
    ]

    # Return required files so they can be deleted later
    return simFiles + [guidePath]


# Function for epidemic toolbox function
def epidemic(
    communityName,
    joint,
    id,
    summaryStat=None,
    cumulative=False,
    byAge=False,
    toolboxPath=None,
):
    from analysis.AnalysisStat import AnalysisStat
    from commands.epidemic import EpidemicCurveCommand
    from ToolboxConfiguration import ToolboxConfiguration

    # Get toolbox config
    if summaryStat is None:
        summaryStat = AnalysisStat.MEDIAN
    validPath = toolboxPath if toolboxPath else f"serverFiles/toolbox_config_{id}.json"
    toolboxConfig = ToolboxConfiguration(validPath)

    # Run epidemic analysis
    epidemicArgs = Namespace(
        community=[communityName],
        set=[id],
        calculate_stat=summaryStat,
        cumulative_sum=cumulative,
        by_age=byAge,
        moving_average_window=7,
        scale=1,
        by_strain=False,
        age_adjusted=None,
        split_output=False,
        filenames=[],
        log_level=LogLevel.DEBUG,
    )
    print(
        f'[epidemic] Running "epidemic" analysis for set {id} [{summaryStat}]',
        "[cumulative]" if cumulative else "[individual]",
        "[age-separated]" if byAge else "[age-combined]",
    )
    EpidemicCurveCommand().run_command(epidemicArgs, toolboxConfig)

    # Return the name of the newly processed file
    filename = os.path.join(
        simLocation,
        "post-analysis",
        (
            (
                f"{communityName}{joint}{id}-epidemic-"
                f"{'cumulative-' if cumulative else ''}{summaryStat}.csv"
            )
        ),
    )

    orderedEpidemic = pd.read_csv(filename, header=0).sort_index(axis=1)
    orderedEpidemic.set_index("day").to_csv(filename, na_rep="0.0")
    return filename


# Function for asir toolbox function
def asir(
    communityName,
    joint,
    id,
    summaryStat=None,
    getProportion=False,
    onlyIndigenous=False,
    onlyPregnant=False,
    onlyVaccinated=False,
    toolboxPath=None,
):
    from analysis.AnalysisStat import AnalysisStat
    from commands.ASIRAnalysis import AsirCommand
    from ToolboxConfiguration import ToolboxConfiguration

    # Get toolbox config
    if summaryStat is None:
        summaryStat = AnalysisStat.MEDIAN
    validPath = toolboxPath if toolboxPath else f"serverFiles/toolbox_config_{id}.json"
    toolboxConfig = ToolboxConfiguration(validPath)

    # Run epidemic analysis
    asirArgs = Namespace(
        community=[communityName],
        set=[id],
        calculate_stat=summaryStat,
        proportion=getProportion,
        indigenous=onlyIndigenous,
        pregnant=onlyPregnant,
        vaccinated=onlyVaccinated,
        filenames=[],
        log_level=LogLevel.DEBUG,
    )
    print(
        f'[asir] Running "asir" analysis for set {id} on community '
        f"{communityName} [{summaryStat}]",
        "[proportionate]" if getProportion else "[discrete]",
        "[indigenous only]" if onlyIndigenous else "[all demographics]",
        "[pregnant only]" if onlyIndigenous else "[all pregnant status]",
        "[vaccinated only]" if onlyIndigenous else "[all vaccine status]",
    )
    AsirCommand().run_command(asirArgs, toolboxConfig)
    filename = os.path.join(
        simLocation, f"post-analysis/{communityName}{joint}{id}-asir-{summaryStat}.csv"
    )

    # Order the scenarios correctly
    orderedAsir = pd.read_csv(filename, header=0, index_col=0).sort_index()
    orderedAsir.to_csv(filename, na_rep="0.0")

    # Return the name of the newly processed file

    return filename
