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


class RunCommand:
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
            await asyncio.to_thread(scenario.run)
        duration = time.monotonic() - startTime
        formattedDuration = str(datetime.timedelta(seconds=round(duration)))
        overrideLog.info("All simulations completed in " + formattedDuration)
