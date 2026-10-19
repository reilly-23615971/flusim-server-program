# Flusim Web Interface Application
# Developed by Reilly Evans
# Replacements for Flusim toolbox modules that integrate the dashboard better

# Imports
import asyncio
import datetime
import logging
import os
import sys
import time
from argparse import ArgumentParser, Namespace
from typing import Optional

from server_files.shared_resources import SIMULATOR_LOCATION, update_status
from server_files.types import TaskData

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(os.path.join(os.getcwd(), SIMULATOR_LOCATION, "src/toolbox"))

# Logging
override_log = logging.getLogger(__name__)

# TODO: Just modify the toolbox repo itself rather than using these workarounds

from commands.Run.RunCommand import RunCommand
from ToolboxConfiguration import ToolboxConfiguration


class RunCommandWithTask(RunCommand):
    """
    Modified version of the toolbox's RunCommand that contains a TaskData
    object, allowing for updates to its status and mid-simulation termination
    """

    name = "run"
    description = "Run simulation sets"
    sim = None

    def __init__(self, sim: Optional[TaskData] = None) -> None:
        super().__init__()
        self.sim = sim

    async def run_command_async(
        self, args: Namespace, config: ToolboxConfiguration
    ) -> None:
        from commands.Run.ScenarioBuilder import ScenarioBuilder

        start_time = time.monotonic()

        # Since the C++ code is multithreaded now, we don't need to multithread here!
        queue_builder = ScenarioBuilder(config, args.guide)
        for index, scenario in enumerate(queue_builder.generateScenarios()):
            # Update status for dashboard
            if self.sim is not None:
                override_log.info(f"\n\nAbout to run simulation number {index}\n\n")
                await update_status(self.sim, f"running_sim{index}")
            # Note that the progress bar generated in the terminal is part of
            # the simulator's C++ code, so using it for dashboard progress
            # would be difficult
            await asyncio.to_thread(run_scenario, scenario, self.sim, False)
        duration = time.monotonic() - start_time
        formatted_duration = str(datetime.timedelta(seconds=round(duration)))
        override_log.info("All simulations completed in " + formatted_duration)


from commands.StandaloneRun import StandaloneRunCommand


class StandaloneRunWithTask(StandaloneRunCommand):
    """
    Modified version of the toolbox's StandaloneRunCommand that contains a
    TaskData object, allowing for status updates and reading the output
    directly rather than printing it to the terminal
    """

    from ToolboxConfiguration import ToolboxConfiguration

    def __init__(self, task: Optional[TaskData] = None) -> None:
        super().__init__()
        self.task = task

    async def run_command_async(
        self, args: Namespace, config: ToolboxConfiguration
    ) -> Optional[list]:
        import json

        from commands.Run.ScenarioRunner import ScenarioParameters, ScenarioRunner
        from JsonWithCommentsDecoder import JsonWithCommentsDecoder

        start_time = time.monotonic()
        community = config.get_community_config(args.community)
        parameters = ScenarioParameters()

        with open(args.scenario) as scenario_file:
            scenario_json = json.load(scenario_file, cls=JsonWithCommentsDecoder)
            parameters.merge(scenario_json)

        parameters.commandArguments.merge(self.getCommandArguments(args))

        # Update status for dashboard
        if self.task is not None:
            override_log.info(f"\n\nAbout to calculate r0\n\n")
            await update_status(self.task, f"running")

        try:
            runner = ScenarioRunner(
                config,
                self.getCommand(),
                community,
                parameters,
                self.getDbPath(args),
            )
            output = await asyncio.to_thread(run_scenario, runner, self.task, True)
        finally:
            self.cleanup()

        duration = time.monotonic() - start_time
        formatted_duration = str(datetime.timedelta(seconds=round(duration)))
        override_log.info("R0 calculation completed in " + formatted_duration)
        return output


class R0CalibrationWithTask(StandaloneRunWithTask):
    """
    R0Calibration command that inherits status and asynchronicity
    """

    name = "r0calibration"
    description = "Calibrate the beta of strain 0 for a target r0"

    def configure_parser_options(self, parser: ArgumentParser) -> None:
        super().configure_parser_options(parser)

        parser.add_argument(
            "-s",
            "--sample_size",
            default=2000,
            help="The size of the r0 sample to generate, which influences how accurate the calculation is",
        )
        parser.add_argument(
            "-t",
            "--target_r0",
            type=float,
            help="The target r0 that you want to calibrate to",
        )
        parser.add_argument(
            "-m",
            "--max_r0_diff",
            type=float,
            help="Stop calibrating once the calculated r0 is less than this value away from the target",
        )

    def getCommand(self) -> str:
        return "r0calibration"

    def getCommandArguments(self, args: Namespace) -> dict:
        return {
            "n_runs": args.sample_size,
            "target_r0": args.target_r0,
            "max_r0_differential": args.max_r0_diff,
        }

    def getDbPath(self, args: Namespace) -> str:
        import tempfile

        self.db = tempfile.NamedTemporaryFile(delete=False)
        self.db.close()
        return self.db.name

    def cleanup(self) -> None:
        os.remove(self.db.name)


class R0CalculationWithTask(StandaloneRunWithTask):
    """
    R0Calculation command that inherits status and asynchronicity
    """

    name = "r0calculation"
    description = "Calculate the reproduction value of a specific scenario"

    def configure_parser_options(self, parser: ArgumentParser) -> None:
        super().configure_parser_options(parser)

        parser.add_argument(
            "-s",
            "--sample_size",
            default=2000,
            help="The size of the r0 sample to generate, which influences how accurate the calculation is",
        )

    def getCommand(self) -> str:
        return "r0calculation"

    def getCommandArguments(self, args: Namespace) -> dict:
        return {"n_runs": args.sample_size}

    def getDbPath(self, args: Namespace) -> str:
        import tempfile

        self.db = tempfile.NamedTemporaryFile(delete=False)
        self.db.close()
        return self.db.name

    def cleanup(self) -> None:
        os.remove(self.db.name)


from commands.Run.ScenarioRunner import ScenarioRunner


def run_scenario(
    scenario: ScenarioRunner, sim: Optional[TaskData], capture_output: bool = False
):
    """
    Modified version of ScenarioRunner's run function that
    stores the simulation engine's process so it can be terminated if necessary
    """
    import shutil
    import sqlite3
    import subprocess

    # Parameter validation
    if not isinstance(scenario, ScenarioRunner):
        override_log.error(f"run_scenario called on non-scenario object {scenario}")
        return
    if not isinstance(sim, TaskData) and sim is not None:
        override_log.error(f"run_scenario called with non-TaskData {scenario}")
        return

    # Construct SQLite database
    shutil.copy(scenario.community.population_model, scenario.scenarioDb)
    override_log.debug(
        f"Created {scenario.scenarioDb} from community {scenario.community.name}"
    )

    connection = sqlite3.connect(scenario.scenarioDb)

    with open(scenario.config.sql_path / "scenario_parameters.sql") as ddl_file:
        connection.executescript(ddl_file.read())

    scenario.parameters.setInSqlite(connection)

    with open(scenario.config.sql_path / "event_log.sql") as ddl_file:
        connection.executescript(ddl_file.read())

    connection.commit()

    command = scenario.getCommand()
    override_log.info(f"Running {scenario.command} {scenario.scenarioDb}")
    override_log.debug(f"With command-line invocation: {command}")
    override_log.debug(f"Output is {'' if capture_output else 'not '}being captured")
    sim_process = subprocess.Popen(
        command, stdout=subprocess.PIPE if capture_output else None, text=True
    )
    if sim is not None:
        sim.process = sim_process
    # TODO: Is list the best container for this output?
    output_lines = []
    if capture_output:
        if sim_process.stdout is None:
            raise AssertionError("Failed to capture scenario process output")
        # TODO: See if captured output can make dashboard progress bars more dynamic
        for line in sim_process.stdout:
            print(line, end="")
            output_lines.append(line)
    sim_process.wait()
    if capture_output:
        return output_lines
