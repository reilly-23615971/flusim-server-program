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

from ServerFiles.SharedResources import updateStatus
from ServerFiles.SimulationFunctions import TaskData, simLocation

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(os.path.join(os.getcwd(), simLocation, "src/toolbox"))

# Logging
overrideLog = logging.getLogger(__name__)

# TODO: Just modify the toolbox repo itself rather than using these workarounds

from commands.Run.RunCommand import RunCommand
from ToolboxConfiguration import ToolboxConfiguration


class RunCommandWithData(RunCommand):
    """
    Modified version of the toolbox's RunCommand that contains a TaskData object,
    allowing for updates to its status and mid-simulation termination
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

        startTime = time.monotonic()

        # Since the C++ code is multithreaded now, we don't need to multithread here!
        queue_builder = ScenarioBuilder(config, args.guide)
        for index, scenario in enumerate(queue_builder.generateScenarios()):
            # Update status for dashboard
            if self.sim is not None:
                overrideLog.info(f"\n\nAbout to run simulation number {index}\n\n")
                await updateStatus(self.sim, f"runningSim{index}")
            # Note that the progress bar generated in the terminal is part of
            # the simulator's C++ code, so using it for dashboard progress
            # would be difficult
            await asyncio.to_thread(runScenario, scenario, self.sim, False)
        duration = time.monotonic() - startTime
        formattedDuration = str(datetime.timedelta(seconds=round(duration)))
        overrideLog.info("All simulations completed in " + formattedDuration)


from commands.StandaloneRun import StandaloneRunCommand


class StandaloneRunWithData(StandaloneRunCommand):
    """
    Modified version of the toolbox's StandaloneRunCommand that contains a
    TaskData object, allowing for status updates and reading the output directly
    rather than printing it to the terminal
    """

    from ToolboxConfiguration import ToolboxConfiguration

    def __init__(self, task: Optional[TaskData] = None) -> None:
        super().__init__()
        self.task = task

    async def run_command_async(
        self, args: Namespace, config: ToolboxConfiguration
    ) -> Optional[bytes]:
        import json

        from commands.Run.ScenarioRunner import ScenarioParameters, ScenarioRunner
        from JsonWithCommentsDecoder import JsonWithCommentsDecoder

        startTime = time.monotonic()
        community = config.get_community_config(args.community)
        parameters = ScenarioParameters()

        with open(args.scenario) as scenarioFile:
            scenarioJson = json.load(scenarioFile, cls=JsonWithCommentsDecoder)
            parameters.merge(scenarioJson)

        parameters.commandArguments.merge(self.getCommandArguments(args))

        # Update status for dashboard
        if self.task is not None:
            overrideLog.info(f"\n\nAbout to calculate r0\n\n")
            await updateStatus(self.task, f"running")

        try:
            runner = ScenarioRunner(
                config,
                self.getCommand(),
                community,
                parameters,
                self.getDbPath(args),
            )
            output = await asyncio.to_thread(runScenario, runner, self.task, True)
        finally:
            self.cleanup()

        duration = time.monotonic() - startTime
        formattedDuration = str(datetime.timedelta(seconds=round(duration)))
        overrideLog.info("R0 calculation completed in " + formattedDuration)
        return output


class R0CalculationWithData(StandaloneRunWithData):
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


def runScenario(
    scenario: ScenarioRunner, sim: Optional[TaskData], captureOutput: bool = False
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
        overrideLog.error(f"runScenario called on non-scenario object {scenario}")
        return
    if not isinstance(sim, TaskData) and sim is not None:
        overrideLog.error(f"runScenario called with non-TaskData {scenario}")
        return

    # Construct SQLite database
    shutil.copy(scenario.community.population_model, scenario.scenarioDb)
    overrideLog.debug(
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
    overrideLog.info(f"Running {scenario.command} {scenario.scenarioDb}")
    overrideLog.debug(f"With command-line invocation: {command}")
    simProcess = subprocess.Popen(
        command, stdout=subprocess.PIPE if captureOutput else None
    )
    if sim is not None:
        sim.process = simProcess
    simProcess.wait()
    if captureOutput:
        output = simProcess.stdout.read() if simProcess.stdout is not None else None
        return output
