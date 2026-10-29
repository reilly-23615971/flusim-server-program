# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions for calibrating or calculating basic reproduction numbers

# Imports
import re
from argparse import Namespace
from datetime import datetime
from tempfile import NamedTemporaryFile

from ToolboxConfiguration import ToolboxConfiguration

from server_files.model_schema import CommunityOverride, OverrideTemplate
from server_files.shared_resources import EXCLUDED_PARAMS, display_time
from server_files.types import CommunityName


async def run_calibration(
    r0: float,
    community_name: CommunityName,
    params: CommunityOverride | OverrideTemplate,
    toolbox_config: ToolboxConfiguration,
):
    """
    Function to determine what value of beta is needed to achieve the desired
    basic reproduction number with the provided config parameters.

    Parameters:
        r0 (float): The desired basic reproduction number (i.e. how many new
            infections should be caused by a single infected individual over the
            pathogen's lifespan).

        community_name (str): The name of the community being simulated (e.g. Newcastle).

        params (CommunityOverride or OverrideTemplate): The parameters to
            use for the calibrating simulations.

        toolbox_config (ToolboxConfiguration): The object containing settings
            for the toolbox commands.
    """

    # from commands.Run.RunCommand import RunCommand
    from logger import LogLevel

    from server_files.toolbox_overrides import R0CalibrationWithTask

    run_start_time = datetime.now()

    with NamedTemporaryFile(suffix=".json", delete_on_close=False) as params_file:
        # Save parameters to tempfile
        params_file.write(
            params.model_dump_json(
                indent=2,
                exclude_none=True,
                exclude={
                    "parameters": {
                        "Scenario_Parameter": EXCLUDED_PARAMS,
                    }
                },
            ).encode()
        )
        params_file.close()
        print(f"Parameters located at {params_file.name}")
        # Calibrate R0
        # TODO: Better status logging (can you send over the current candidate R0?)
        command_output = await R0CalibrationWithTask().run_command_async(
            Namespace(
                community=community_name,
                scenario=params_file.name,
                use_baseline=True,
                sample_size=2000,
                target_r0=r0,
                max_r0_diff=0.005,
                log_level=LogLevel.WARNING,
            ),
            config=toolbox_config,
        )
    if command_output is not None:
        results = command_output[-2]
        result_matches = re.search(
            r"A R0 of (.*?) \(95% CI \[(.*?), (.*?)\]\) "
            r"calculated for a beta of (.*?)$",
            results,
        )
        if result_matches:
            r0 = float(result_matches.group(1))
            lower_bound = float(result_matches.group(2))
            upper_bound = float(result_matches.group(3))
            final_beta = float(result_matches.group(4))
            print(
                "[run_calibration] Finished calibrating r0 "
                f"in {display_time(run_start_time)}\n"
            )
            return r0, (lower_bound, upper_bound), final_beta

    print(
        "[run_calibration] Failed to calibrate r0"
        f"after {display_time(run_start_time)}\n"
    )
    return None, (None, None), None


async def run_calculation(
    community_name: CommunityName,
    params: CommunityOverride | OverrideTemplate,
    toolbox_config: ToolboxConfiguration,
):
    """
    Function to use the provided config parameters to estimate the basic
    reproduction number.

    Parameters:
        community_name (str): The name of the community being simulated (e.g. Newcastle).

        params (CommunityOverride or OverrideTemplate): The parameters to
            use for the calculating simulations.

        toolbox_config (ToolboxConfiguration): The object containing settings
            for the toolbox commands.
    """

    # from commands.Run.RunCommand import RunCommand
    from logger import LogLevel

    from server_files.toolbox_overrides import R0CalculationWithTask

    run_start_time = datetime.now()

    with NamedTemporaryFile(suffix=".json", delete_on_close=False) as params_file:
        # Save parameters to tempfile
        params_file.write(
            params.model_dump_json(
                indent=2,
                exclude_none=True,
                exclude={
                    "parameters": {
                        "Scenario_Parameter": EXCLUDED_PARAMS,
                    }
                },
            ).encode()
        )
        params_file.close()
        print(f"Parameters located at {params_file.name}")
        # Calculate R0
        command_output = await R0CalculationWithTask().run_command_async(
            Namespace(
                community=community_name,
                scenario=params_file.name,
                use_baseline=True,
                sample_size=2000,
                log_level=LogLevel.DEBUG,
            ),
            config=toolbox_config,
        )
    if command_output is not None:
        results = command_output[-1]
        result_matches = re.search(
            r"R0 calculated to be (.*?) with 95% confidence interval of \[(.*?), (.*?)\]",
            results,
        )
        if result_matches:
            r0 = float(result_matches.group(1))
            lower_bound = float(result_matches.group(2))
            upper_bound = float(result_matches.group(3))
            print(
                "[run_calculation] Finished calculating r0 "
                f"in {display_time(run_start_time)}\n"
            )
            return r0, (lower_bound, upper_bound)

    print(
        "[run_calculation] Failed to calculate r0 "
        f"after {display_time(run_start_time)}\n"
    )
    return None, (None, None)
