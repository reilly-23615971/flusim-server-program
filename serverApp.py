# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import asyncio
import logging
import os
import uuid
import zipfile
from datetime import datetime

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from serverFiles.ModelSchema import modelGuideFile
from serverFiles.simulationFunctions import (
    SimData,
    activeSimulations,
    asir,
    clearFiles,
    # deleteFiles,
    displayTime,
    epidemic,
    generateToolboxConfig,
    runSimulation,
    updateStatus,
)

# Ensure Flusim imports work properly when called outside of toolbox
# TODO: Uncomment if AnalysisStat is used in the main function
# sys.path.append(os.path.join(os.getcwd(), simLocation, "src/toolbox"))
# from analysis.AnalysisStat import AnalysisStat

# Logging config
os.makedirs("tempFiles", exist_ok=True)
logging.basicConfig(
    filename="tempFiles/serverAppLogs.txt",
    filemode="a",
    format="%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

# Throw error if Flusim files aren't present
# TODO: Check for the simulator and not just the toolbox
# (protect against running without building the executable first)
if not os.path.isfile("src/toolbox/toolbox.py"):
    raise FileNotFoundError(
        (
            "Flusim files not found. Ensure that this application is "
            "present in the same directory as the Flusim simulation files."
        )
    )


# Define main Flusim app and dictionary for
flusimApp = FastAPI()

# CORS Middleware for ensuring only the web application can make requests
flusimApp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with production URLs
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


async def closeSimulation(simulationID: str):
    """
    Async wrapper to ensure SimData objects are properly cleaned up
    and tasks are fully cancelled before files are deleted.

    Parameters:
        simulationID (str): The ID distinguishing this simulation task.
    """
    simData = activeSimulations.get(simulationID)
    if simData is None:
        return

    # Cancel tasks, delete files and remove the simulation data
    await simData.stopTasks()
    clearFiles(simData.files)
    del activeSimulations[simulationID]


async def runModel(simulationID: str, config: modelGuideFile):
    """
    Async function to run a simulation experiment based on parameters
    from the dashboard, then zip the analysed statistics.

    Parameters:
        simulationID (str): The ID distinguishing this simulation task.

        config (modelGuideFile): The parameters and other settings that
            will define the simulation experiment.
    """
    try:
        # Wait 1 second for the websocket to connect
        await asyncio.sleep(1)
        overallStartTime = datetime.now()

        # Get relevant attributes from config file and sim data
        # TODO: See if fileID can be replaced with simulationID
        simData = activeSimulations.get(simulationID)
        if simData is None:
            raise ValueError("The simulation with the requested ID could not be found")
        fileID = config.description
        community = config.community_used[0]
        middleJoint = config.middle_joint
        print(f"Simulation received; name = {config.name}, ID = {simulationID}")

        # Log the files that will be created over the course of the simulation
        simData.files = set()
        analysisFiles = []

        # Generate toolbox config file
        await updateStatus(simData, "generatingConfig")
        toolboxPath = generateToolboxConfig(simData, fileID, middleJoint)
        print(f"Toolbox file located at {toolboxPath}")

        # Run the Flusim simulation
        await runSimulation(simData, fileID, config, toolboxPath)

        # TODO: Use middle joint to determine analyses to run
        # (or find a way to send the data forms to the server directly)

        # for now, just get the standard analyses the dashboard uses

        # Daily infection epidemic curve
        await updateStatus(simData, "toolboxAnalysis0")
        analysisFiles += await asyncio.to_thread(
            epidemic,
            simData,
            fileID,
            community,
            middleJoint,
            cumulative=True,
            toolboxPath=toolboxPath,
        )

        # Cumulative infection epidemic curve
        await updateStatus(simData, "toolboxAnalysis1")
        analysisFiles += await asyncio.to_thread(
            epidemic,
            simData,
            fileID,
            community,
            middleJoint,
            cumulative=False,
            toolboxPath=toolboxPath,
        )

        # Age-separated infection rates
        await updateStatus(simData, "toolboxAnalysis2")
        analysisFiles += await asyncio.to_thread(
            asir,
            simData,
            fileID,
            community,
            middleJoint,
            toolboxPath=toolboxPath,
        )

        # Vaccinated age-separated infection rates
        if middleJoint and "+vaccine" in middleJoint:
            await updateStatus(simData, "toolboxAnalysis3")
            analysisFiles += await asyncio.to_thread(
                asir,
                simData,
                fileID,
                community,
                middleJoint,
                onlyVaccinated=True,
                toolboxPath=toolboxPath,
            )

        # If all else fails and no analyses were specified, run epidemic
        if not analysisFiles:
            print("No analyses specified; defaulting to epidemic")
            analysisFiles += await asyncio.to_thread(
                epidemic,
                simData,
                fileID,
                community,
                middleJoint,
                toolboxPath=toolboxPath,
            )

        print("\nAnalysis files:")
        for file in analysisFiles:
            print("   ", file)

        # Zip together the analysis files if necessary
        # TODO: See if simplifying to always return zip is OK
        await updateStatus(simData, "zippingAnalysis")
        if len(analysisFiles) != 1:
            zipPath = f"tempFiles/{fileID}_analysis.zip"
            simData.files.add(zipPath)
            with zipfile.ZipFile(zipPath, mode="w") as analysis:
                for file in analysisFiles:
                    analysis.write(file)
            finalPath = zipPath
        # Just return lone CSV if only one analysis needed
        else:
            (finalPath,) = analysisFiles

        simData.results = finalPath

        print(
            f"\nSimulation request for session {fileID} complete in "
            f"{displayTime(overallStartTime)}, ready to return data\n"
        )

        await updateStatus(simData, "completed")
    except Exception as e:
        # TODO: Add more info to errors like this
        await updateStatus(activeSimulations[simulationID], "error")
        print(f"Error while running simulation {simulationID}:\n{e}")


@flusimApp.post("/runModel", status_code=202)
async def runModelRoute(config: modelGuideFile) -> dict[str, str]:
    """
    Async route function to begin a simulation experiment and give the
    dashboard an ID to poll for status updates.

    Parameters:
        config (modelGuideFile): The parameters and other settings that
            will define the simulation experiment.

    Returns:
        dict: A dictionary containing the ID assigned to this particular
            simulation run. A dictionary is used rather than returning the ID
            directly as an int to ensure corrupted data is not read by the
            dashboard client.
    """
    # TODO: Make simulationID a cookie if it helps with reload preservation
    simulationID = str(uuid.uuid4())
    activeSimulations[simulationID] = SimData(simulationID)

    runModelTask = asyncio.create_task(runModel(simulationID, config))

    activeSimulations[simulationID].tasks.add(runModelTask)

    return {"simulationID": simulationID}


@flusimApp.websocket("/runModel/status/{simulationID}")
async def statusWebSocket(websocket: WebSocket, simulationID: str):
    """
    Websocket route to deliver simulation status updates live

    Parameters:
        websocket (WebSocket): The websocket to send updates to.

        simulationID (str): The ID distinguishing this simulation task.

    Raises:
        WebSocketException: If the specified ID does not exist (uses 1008 status code).
    """
    await websocket.accept()
    simData = activeSimulations.get(simulationID)
    if simData is None:
        raise WebSocketException(
            1008, "The simulation with the requested ID could not be found"
        )

    simData.websockets.append(websocket)

    try:
        # Send current status
        await websocket.send_json({"status": simData.status})

        # Keep connection open to send updates
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        simData.websockets.remove(websocket)


@flusimApp.get("/runModel/download/{simulationID}")
async def downloadSimulationResults(simulationID: str, cleanup: BackgroundTasks):
    """
    Async route function to obtain the results of a simulation experiment.

    Parameters:
        simulationID (str): The ID distinguishing this simulation task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove simulation data once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist or has no results
            (uses 404 status code) or is still running (raises 503 status code).
    """
    simData = activeSimulations.get(simulationID)
    if simData is None:
        raise HTTPException(
            404, "The simulation with the requested ID could not be found"
        )

    currentStatus = simData.status
    if currentStatus != "completed":
        raise HTTPException(503, "The requested simulation is still ongoing")

    filePath = simData.results

    if not filePath or not os.path.exists(filePath):
        raise HTTPException(
            404,
            """
The analysis results for the simulation with the requested ID could not be found
            """,
        )

    cleanup.add_task(closeSimulation, simulationID)

    return FileResponse(filePath, filename=os.path.basename(filePath))


@flusimApp.delete("/runModel/cancel/{simulationID}", status_code=204)
async def stopSimulation(simulationID: str, cleanup: BackgroundTasks):
    """
    Async route function to stop a running simulation.

    Parameters:
        simulationID (str): The ID distinguishing this simulation task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove excess files once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist (uses 404 status code).
    """
    simData = activeSimulations.get(simulationID)
    if simData is None:
        raise HTTPException(
            404, "The simulation with the requested ID could not be found"
        )
    cleanup.add_task(closeSimulation, simulationID)
