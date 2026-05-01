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

from serverFiles.simulationFunctions import SimData, simLocation, updateStatus

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(os.path.join(os.getcwd(), simLocation, "src/toolbox"))

# Logging
overrideLog = logging.getLogger(__name__)

# TODO: Just modify the toolbox repo itself rather than using these workarounds


class RunCommandWithData:
    """
    Modified version of the toolbox's RunCommand that contains a SimData object,
    allowing for updates to its status and mid-simulation termination
    """
    from ToolboxConfiguration import ToolboxConfiguration

    name = "run"
    description = "Run simulation sets"
    sim = None

    def __init__(self, sim: Optional[SimData] = None) -> None:
        super().__init__()
        self.sim = sim

    def configure_parser_options(self, parser: ArgumentParser) -> None:
        parser.add_argument("guide", type=str, help="the guide file")

    async def run_command(self, args: Namespace, config: ToolboxConfiguration) -> None:
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
            await asyncio.to_thread(runScenario, scenario, self.sim)
        duration = time.monotonic() - startTime
        formattedDuration = str(datetime.timedelta(seconds=round(duration)))
        overrideLog.info("All simulations completed in " + formattedDuration)


def runScenario(scenario, sim):
    """
    Modified version of ScenarioRunner's run function that
    stores the simulation engine's process so it can be terminated if necessary
    """
    import shutil
    import sqlite3
    import subprocess
    from commands.Run.ScenarioRunner import ScenarioRunner

    if not isinstance(scenario, ScenarioRunner):
        overrideLog.error(f"runScenario called on non-scenario object {scenario}")
        return
    if not isinstance(sim, SimData):
        overrideLog.error(f"runScenario called with non-SimData {scenario}")
        return
    
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
    simProcess = subprocess.Popen(command)
    sim.process = simProcess
    simProcess.wait()
