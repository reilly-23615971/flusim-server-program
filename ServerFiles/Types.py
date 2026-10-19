# Flusim Web Interface Application
# Developed by Reilly Evans
# Types, classes and related objects used throughout the server's operations

# Imports
import asyncio
import logging
from asyncio import Task
from dataclasses import dataclass
from subprocess import Popen
from typing import Any, Literal, Sequence, get_args

from fastapi import WebSocket

# Logging
type_log = logging.getLogger(__name__)

# Simple type aliases

# Age groups
type AgeGroup = Literal[
    "Young Infant (0-6 Months)",
    "Infant (7-24 Months)",
    "Young Child (3-5 Years)",
    "Child (6-12 Years)",
    "Adolescent (13-17 Years)",
    "Young Adult (18-24 Years)",
    "Adult (25-44 Years)",
    "Older Adult (45-64 Years)",
    "Senior (65-79 Years)",
    "Older Senior (80+ Years)",
]
type AgeWithTotal = AgeGroup | Literal["Total"]
type AgeGroupKey = Literal[
    "young_infant",  # 0-6 months
    "infant",  # 7-24 months (0.5-2 years)
    "young_child",  # 3-5 years
    "child",  # 6-12 years
    "adolescent",  # 13-17 years
    "young_adult",  # 18-24 years
    "adult",  # 25-44 years
    "older_adult",  # 45-64 years
    "senior",  # 65-79 years
    "older_senior",  # 80+ years
]

# Communities that can be modelled
type CommunityName = Literal["albany", "cairns", "newcastle"]
COMMUNITY_NAMES: tuple[CommunityName] = get_args(CommunityName.__value__)

# Locations in the simulation
type AlbanyPatch = Literal[
    "Albany",
    "Kojonup",
    "Plantagenet",
    "Stirling Range National Park",
    "Denmark",
    "McKail - Willyung",
    "Gnowangerup",
    "Albany Region",
    "Little Grove - Elleker",
    "Bayonet Head - Lower King",
    "Katanning",
]
type CairnsPatch = Literal[
    "Westcourt - Bungalow",
    "Cairns City",
    "Redlynch",
    "White Rock",
    "Trinity Beach - Smithfield",
    "Earlville - Bayview Heights",
    "Clifton Beach - Kewarra Beach",
    "Freshwater - Stratford",
    "Woree",
    "Mount Sheridan",
    "Bentley Park",
    "Gordonvale - Trinity",
    "Whitfield - Edge Hill",
    "Brinsmead",
    "Lamb Range",
    "Kanimbla - Mooroobool",
    "Manunda",
    "Edmonton",
    "Manoora",
    "Yorkeys Knob - Machans Beach",
]
type NewcastlePatch = Literal[
    "Glendale - Cardiff - Hillsborough",
    "Maryland - Fletcher - Minmi",
    "Newcastle - Cooks Hill",
    "Newcastle Port - Kooragang",
    "Belmont - Bennetts Green",
    "Belmont South - Blacksmiths",
    "Shortland - Jesmond",
    "Redhead",
    "Wickham - Carrington - Tighes Hill",
    "Valentine - Eleebana",
    "Beresfield - Hexham",
    "Swansea - Caves Beach",
    "Hamilton - Broadmeadow",
    "Charlestown - Dudley",
    "Warners Bay - Boolaroo",
    "Merewether - The Junction",
    "Adamstown - Kotara",
    "Wallsend - Elermore Vale",
    "Stockton - Fullerton Cove",
    "Lambton - New Lambton",
    "Mayfield - Warabrook",
    "Mount Hutton - Windale",
    "Waratah - North Lambton",
]
ALBANY_PATCHES = get_args(AlbanyPatch.__value__)
CAIRNS_PATCHES = get_args(CairnsPatch.__value__)
NEWCASTLE_PATCHES = get_args(NewcastlePatch.__value__)
type CommunityPatch = AlbanyPatch | CairnsPatch | NewcastlePatch


@dataclass
class CommunityData:
    """
    Class for storing a given community's relevant data
    """

    name: str
    population: int
    age_pops: dict[AgeWithTotal, int]
    patches: Sequence[CommunityPatch]


# Data for communities that can be modelled by the simulation
ALBANY = CommunityData(
    name="Albany",
    population=55109,
    age_pops={
        "Young Infant (0-6 Months)": 669,
        "Infant (7-24 Months)": 1430,
        "Young Child (3-5 Years)": 2312,
        "Child (6-12 Years)": 4782,
        "Adolescent (13-17 Years)": 4126,
        "Young Adult (18-24 Years)": 4061,
        "Adult (25-44 Years)": 12841,
        "Older Adult (45-64 Years)": 15668,
        "Senior (65-79 Years)": 6806,
        "Older Senior (80+ Years)": 2414,
        "Total": 55109,
    },
    patches=ALBANY_PATCHES,
)
CAIRNS = CommunityData(
    name="Cairns",
    population=140402,
    age_pops={
        "Young Infant (0-6 Months)": 1837,
        "Infant (7-24 Months)": 4277,
        "Young Child (3-5 Years)": 6381,
        "Child (6-12 Years)": 12650,
        "Adolescent (13-17 Years)": 10432,
        "Young Adult (18-24 Years)": 12074,
        "Adult (25-44 Years)": 42394,
        "Older Adult (45-64 Years)": 36541,
        "Senior (65-79 Years)": 10675,
        "Older Senior (80+ Years)": 3141,
        "Total": 140402,
    },
    patches=CAIRNS_PATCHES,
)
NEWCASTLE = CommunityData(
    name="Newcastle",
    population=272407,
    age_pops={
        "Young Infant (0-6 Months)": 2742,
        "Infant (7-24 Months)": 6641,
        "Young Child (3-5 Years)": 10242,
        "Child (6-12 Years)": 20603,
        "Adolescent (13-17 Years)": 18513,
        "Young Adult (18-24 Years)": 27015,
        "Adult (25-44 Years)": 71299,
        "Older Adult (45-64 Years)": 69949,
        "Senior (65-79 Years)": 31384,
        "Older Senior (80+ Years)": 14019,
        "Total": 272407,
    },
    patches=NEWCASTLE_PATCHES,
)
COMMUNITIES: dict[CommunityName, CommunityData] = {
    "albany": ALBANY,
    "cairns": CAIRNS,
    "newcastle": NEWCASTLE,
}


class TaskData:
    """
    Class for information regarding a server task
    """

    def __init__(self, taskID):
        self._taskID = taskID
        self._websockets = []
        self._tasks = set()
        self._process = None
        self._status = "start"
        self._files = set()
        self._results = None

    @property
    def taskID(self):
        """ID associated with this simulation"""
        return self._taskID

    @property
    def websockets(self):
        """Websockets tied to the client that requested this simulation"""
        # TODO: Does this need to be a list? 1 websocket per sim is normal
        return self._websockets

    @websockets.setter
    def websockets(self, value: list[WebSocket]):
        self._websockets = value

    @websockets.deleter
    def websockets(self):
        # TODO: Should websockets be closed in this case?
        del self._websockets

    @property
    def tasks(self):
        """Set of asyncio tasks that relate to this simulation"""
        return self._tasks

    @tasks.setter
    def tasks(self, value: set[Task]):
        self._tasks = value

    @property
    def process(self):
        """C++ subprocess currently running for this simulation"""
        return self._process

    @process.setter
    def process(self, value: Popen):
        self._process = value

    @process.deleter
    def process(self):
        if self._process is not None:
            self._process.terminate()
        del self._process

    @property
    def status(self):
        """String indicating the simulation's current progress"""
        return self._status

    @status.setter
    def status(self, value: str):
        self._status = value

    @property
    def files(self):
        """Set of file paths for files that will be created for this simulation"""
        return self._files

    @files.setter
    def files(self, value: set[str]):
        self._files = value

    @property
    def results(self):
        """Either the results to be returned, or the path to the returned file"""
        return self._results

    @results.setter
    def results(self, value: Any):
        self._results = value

    async def stopTasks(self):
        """Stop any currently running tasks for this simulation"""

        for task in self.tasks:
            # Naming tasks for logging would require Python 3.12
            # We'll at least print them for debugging
            type_log.info(f"Cancelling task {task}...")
            task.cancel()

        # Wait for all tasks to finish cancelling
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)


# Dict to store active tasks
active_tasks: dict[str, TaskData] = dict()
