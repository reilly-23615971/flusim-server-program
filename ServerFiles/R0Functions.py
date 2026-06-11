# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions for calibrating or calculating basic reproduction numbers

# Imports
import logging
import os
import re
import sys
from argparse import Namespace
from datetime import datetime

import pandas as pd

from ServerFiles.ModelSchema import communityOverride, overrideTemplate
from ServerFiles.SharedResources import (
    TaskData,
    displayTime,
    simLocation,
    toolboxLocation,
)

# Logging
r0Log = logging.getLogger(__name__)

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(
    os.path.join(os.getcwd(), simLocation, os.path.dirname(toolboxLocation))
)


def generateCalibrationConfig(
    task: TaskData, params: communityOverride | overrideTemplate
) -> str:
    """
    Function to generate the required parameter config file for r0 calibration

    Parameters:
        task (TaskData): The object containing the data used for this task.

        params (communityOverride or overrideTemplate): The parameters to
            save to the config.

    Returns:
        str: The file path for the newly created configuration file.
    """
    # Log filename preemptively in case of cancellation
    r0ConfigPath = f"tempFiles/r0_config_{task.taskID}.json"
    task.files.add(r0ConfigPath)
    print(
        (
            "[generateCalibrationConfig] Generating r0 "
            f"configuration file {r0ConfigPath}"
        )
    )

    # Exclude unused parameters
    excludedParams = {
        "parameters": {
            "Scenario_Parameter": {
                "start_day_of_week",
                "kappa_adult_education",
                "kappa_child_care",
                "kappa_hospital",
                "withdrawal_period",
                "hospitalisation_rate",
                "max_adult_class_size",
                "max_neighbourgroup_size",
                "max_churchgroup_size",
                "max_class_count",
                "pandemic_alert",
                "close_childcare",
                "close_child_education",
                "close_adult_education",
                "prob_work_nonattendance",
                "work_nonattendance_trigger",
                "work_nonattendance_relaxation",
                "work_nonattendance_delay",
                "work_nonattendance_duration",
                "vaccination_priority",
                "withdrawal_period",
            },
        }
    }
    with open(r0ConfigPath, "w") as file:
        file.write(
            params.model_dump_json(indent=2, exclude_none=True, exclude=excludedParams)
        )
    return r0ConfigPath


async def runCalibration(
    r0: float, communityName: str, configPath: str, toolboxPath: str
):
    """
    Function to determine what value of beta is needed to achieve the desired
    basic reproduction number with the provided config parameters.

    Parameters:
        r0 (float): The desired basic reproduction number (i.e. how many new
            infections should be caused by a single infected individual over the
            pathogen's lifespan).

        communityName (str): The name of the community being simulated (e.g. Newcastle).

        configPath (str): The path to the file containing the parameters to
            estimate r0 for.

        toolboxPath (str): The path to the file containing settings for the
            toolbox commands.
    """

    # from commands.Run.RunCommand import RunCommand
    from logger import LogLevel
    from ToolboxConfiguration import ToolboxConfiguration

    from ServerFiles.ToolboxOverrides import R0CalibrationWithData

    runStartTime = datetime.now()
    toolboxConfig = ToolboxConfiguration(toolboxPath)

    # Calculate R0
    commandOutput = await R0CalibrationWithData().run_command_async(
        Namespace(
            community=communityName,
            scenario=configPath,
            use_baseline=True,
            sample_size=2000,
            target_r0=r0,
            max_r0_diff=0.005,
            log_level=LogLevel.WARNING,
        ),
        config=toolboxConfig,
    )
    if commandOutput is not None:
        results = commandOutput[-2]
        resultMatches = re.search(
            r"An R0 of (.*?) \(95% CI \[(.*?), (.*?)\]\) calculated for a beta of (.*?)",
            results,
        )
        if resultMatches:
            r0 = float(resultMatches.group(1))
            lowerBound = float(resultMatches.group(2))
            upperBound = float(resultMatches.group(3))
            finalBeta = float(resultMatches.group(4))
            print(f"""
[runCalibration] Finished calibrating r0 in {displayTime(runStartTime)}\n
            """)
            return r0, (lowerBound, upperBound), finalBeta

    print(f"""
[runCalibration] Failed to calibrate r0 after {displayTime(runStartTime)}\n
    """)
    return None, (None, None), None


async def runCalculation(communityName: str, configPath: str, toolboxPath: str):
    """
    Function to use the provided config parameters to estimate the basic
    reproduction number.

    Parameters:
        communityName (str): The name of the community being simulated (e.g. Newcastle).

        configPath (str): The path to the file containing the parameters to
            estimate r0 for.

        toolboxPath (str): The path to the file containing settings for the
            toolbox commands.
    """

    # from commands.Run.RunCommand import RunCommand
    from logger import LogLevel
    from ToolboxConfiguration import ToolboxConfiguration

    from ServerFiles.ToolboxOverrides import R0CalculationWithData

    runStartTime = datetime.now()
    toolboxConfig = ToolboxConfiguration(toolboxPath)

    # Calculate R0
    commandOutput = await R0CalculationWithData().run_command_async(
        Namespace(
            community=communityName,
            scenario=configPath,
            use_baseline=True,
            sample_size=2000,
            log_level=LogLevel.DEBUG,
        ),
        config=toolboxConfig,
    )
    if commandOutput is not None:
        results = commandOutput[-1]
        resultMatches = re.search(
            r"R0 calculated to be (.*?) with 95% confidence interval of \[(.*?), (.*?)\]",
            results,
        )
        if resultMatches:
            r0 = float(resultMatches.group(1))
            lowerBound = float(resultMatches.group(2))
            upperBound = float(resultMatches.group(3))
            print(f"""
[runCalculation] Finished calculating r0 in {displayTime(runStartTime)}\n
            """)
            return r0, (lowerBound, upperBound)

    print(f"""
[runCalculation] Failed to calculate r0 after {displayTime(runStartTime)}\n
    """)
    return None, (None, None)
