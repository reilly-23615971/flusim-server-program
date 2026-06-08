# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions for calibrating or calculating basic reproduction numbers

# Imports
import json
import logging
import os
import sys
from argparse import Namespace
from datetime import datetime
from typing import Optional

import pandas as pd

from ServerFiles.ModelSchema import communityOverride, modelGuideFile
from ServerFiles.SharedResources import (
    SimData,
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


def generateCalibrationConfig(task: SimData, params: communityOverride) -> str:
    """
    Function to generate the required parameter config file for r0 calibration

    Parameters:
        task (SimData): The object containing the data used for this task.

        params (communityOverride): The parameters to save to the config.

    Returns:
        str: The file path for the newly created configuration file.
    """
    # Log filename preemptively in case of cancellation
    r0ConfigPath = f"tempFiles/r0_config_{task.simulationID}.json"
    task.files.add(r0ConfigPath)
    print(f"""
        [generateToolboxConfig] Generating r0 configuration file {r0ConfigPath}...
    """)
    with open(r0ConfigPath, "w") as file:
        file.write(params.model_dump_json(indent=2, exclude={"name"}))
    return r0ConfigPath


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

    from commands.R0Calculation import R0CalculationCommand

    runStartTime = datetime.now()
    toolboxConfig = ToolboxConfiguration(toolboxPath)

    # Calculate R0
    R0CalculationCommand().run_command(
        Namespace(scenario=configPath, log_level=LogLevel.DEBUG), config=toolboxConfig
    )

    # TODO: Find a way to read the value of R0 from the C++ command

    print(f"""
        [runCalculation] Finished calculating r0 in {displayTime(runStartTime)}\n
    """)
