# Flusim Web Interface Application
# Developed by Reilly Evans

# WARNING: When running as a FastAPI app, make sure to
# add the --no-reload flag to avoid recursive logging

# Imports
import asyncio
import logging
import os
import uuid
import zipfile
from contextlib import asynccontextmanager
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

from ServerFiles.ModelSchema import communityOverride, modelGuideFile, overrideTemplate
from ServerFiles.R0Functions import (
    generateCalibrationConfig,
    runCalculation,
    runCalibration,
)
from ServerFiles.SharedResources import (
    activeTasks,
    clearFiles,
    deleteGeneratedFiles,
    executableLocation,
    toolboxLocation,
    updateStatus,
)
from ServerFiles.SimulationFunctions import (
    TaskData,
    asir,
    displayTime,
    epidemic,
    generateToolboxConfig,
    runSimulation,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function to cancel any remaining tasks when the app shuts down
    """
    yield
    # Cancel any remaining processes and delete remaining files
    tasksToClose = list(activeTasks.keys())
    for task in tasksToClose:
        # TODO: Is sending one last message before sockets disconnect possible?
        # await updateStatus(activeTasks[task], "shutdown")
        await closeTask(task)


# Logging config
# TODO: Try to fix the logging loop again without --no-reload
os.makedirs("tempFiles", exist_ok=True)
logging.basicConfig(
    filename="tempFiles/serverAppLogs.txt",
    filemode="a",
    format="%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

# Throw error if Flusim files aren't present
if not os.path.isfile(toolboxLocation):
    raise FileNotFoundError(f"""
        Flusim toolbox files not found. Ensure that this application is present
        in the same directory as the Flusim simulation files, such that the
        toolbox program is located at "{toolboxLocation}".
    """)
if not os.path.isfile(executableLocation):
    raise FileNotFoundError(f"""
        Flusim simulation engine executable not found. Ensure that the executable
        has been built (see the Flusim documentation for more info) and is located
        at "{executableLocation}".
    """)


# Define main Flusim app
flusimApp = FastAPI(lifespan=lifespan)

# CORS Middleware for ensuring only the web application can make requests
flusimApp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with production URLs
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


# Functions and routes for multiple tasks
async def closeTask(taskID: str):
    """
    Async wrapper to ensure TaskData objects are properly cleaned up
    and tasks are fully cancelled before files are deleted.

    Parameters:
        taskID (str): The ID distinguishing this server task.
    """
    TaskData = activeTasks.get(taskID)
    if TaskData is None:
        return

    # Cancel tasks, delete files and remove simulation data
    if TaskData.process is not None:
        TaskData.process.terminate()
    await TaskData.stopTasks()
    if deleteGeneratedFiles:
        clearFiles(TaskData.files)
    del activeTasks[taskID]
    print(f"[closeTask] Finished closing task with ID {taskID}\n\n")


@flusimApp.websocket("/status/{taskID}")
async def statusWebSocket(websocket: WebSocket, taskID: str):
    """
    Websocket route to deliver task status updates live

    Parameters:
        websocket (WebSocket): The websocket to send updates to.

        taskID (str): The ID distinguishing this server task.

    Raises:
        WebSocketException: If the specified ID does not exist (uses 1008 status code).
    """
    await websocket.accept()
    TaskData = activeTasks.get(taskID)
    if TaskData is None:
        raise WebSocketException(
            1008, "The task with the requested ID could not be found"
        )

    TaskData.websockets.append(websocket)

    try:
        # Send current status
        await websocket.send_json({"status": TaskData.status})

        # Keep connection open to send updates
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        TaskData.websockets.remove(websocket)


@flusimApp.delete("/cancel/{taskID}", status_code=204)
async def stopTaskRoute(taskID: str, cleanup: BackgroundTasks):
    """
    Async route function to stop a running task.

    Parameters:
        taskID (str): The ID distinguishing this server task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove excess files once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist (uses 404 status code).
    """
    TaskData = activeTasks.get(taskID)
    if TaskData is None:
        raise HTTPException(404, "The task with the requested ID could not be found")
    cleanup.add_task(closeTask, taskID)


# Running simulation experiments
async def runModel(taskID: str, config: modelGuideFile):
    """
    Async function to run a simulation experiment based on parameters
    from the dashboard, then zip the analysed statistics.

    Parameters:
        taskID (str): The ID distinguishing this simulation task.

        config (modelGuideFile): The parameters and other settings that
            will define the simulation experiment.
    """
    try:
        # Wait 1 second for the websocket to connect
        await asyncio.sleep(1)
        overallStartTime = datetime.now()

        # Get relevant attributes from config file and sim data
        TaskData = activeTasks.get(taskID)
        if TaskData is None:
            raise ValueError("The simulation with the requested ID could not be found")
        fileID = config.description
        community = config.community_used[0]
        middleJoint = config.middle_joint
        print(f"Simulation received; name = {config.name}, ID = {taskID}")

        # Log the files that will be created over the course of the simulation
        TaskData.files = set()
        analysisFiles = []

        # Generate toolbox config file
        await updateStatus(TaskData, "generatingConfig")
        toolboxPath = generateToolboxConfig(TaskData, fileID, middleJoint)
        print(f"Toolbox file located at {toolboxPath}")

        # Run the Flusim simulation experiment
        await runSimulation(TaskData, fileID, config, toolboxPath)

        # TODO: Use middle joint to determine analyses to run
        # (or find a way to send the data forms to the server directly)

        # for now, just get the standard analyses the dashboard uses

        # Daily infection epidemic curve
        await updateStatus(TaskData, "toolboxAnalysis0")
        analysisFiles += await asyncio.to_thread(
            epidemic,
            TaskData,
            fileID,
            community,
            cumulative=True,
            toolboxPath=toolboxPath,
        )

        # Cumulative infection epidemic curve
        await updateStatus(TaskData, "toolboxAnalysis1")
        analysisFiles += await asyncio.to_thread(
            epidemic,
            TaskData,
            fileID,
            community,
            cumulative=False,
            toolboxPath=toolboxPath,
        )

        # Age-separated infection rates
        await updateStatus(TaskData, "toolboxAnalysis2")
        analysisFiles += await asyncio.to_thread(
            asir,
            TaskData,
            fileID,
            community,
            middleJoint,
            toolboxPath=toolboxPath,
        )

        # Vaccinated age-separated infection rates
        if middleJoint and "+vaccine" in middleJoint:
            await updateStatus(TaskData, "toolboxAnalysis3")
            analysisFiles += await asyncio.to_thread(
                asir,
                TaskData,
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
                TaskData,
                fileID,
                community,
                toolboxPath=toolboxPath,
            )

        print("\nAnalysis files:")
        for file in analysisFiles:
            print("   ", file)

        # Zip together the analysis files
        await updateStatus(TaskData, "zippingAnalysis")
        zipPath = f"tempFiles/analysis_files_{fileID}_.zip"
        TaskData.files.add(zipPath)
        with zipfile.ZipFile(zipPath, mode="w") as analysis:
            for file in analysisFiles:
                analysis.write(file)

        TaskData.results = zipPath

        print(
            f"\nSimulation request for session {fileID} complete in "
            f"{displayTime(overallStartTime)}, ready to return data\n"
        )

        await updateStatus(TaskData, "completed")
    except Exception as e:
        # TODO: Add more info to errors like this
        print(f"Error while running simulation {taskID}:\n{e}")
        await updateStatus(activeTasks[taskID], "error")
        await closeTask(taskID)


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
    # TODO: Make taskID a cookie if it helps with reload preservation
    taskID = str(uuid.uuid4())
    activeTasks[taskID] = TaskData(taskID)

    runModelTask = asyncio.create_task(runModel(taskID, config))

    activeTasks[taskID].tasks.add(runModelTask)

    return {"taskID": taskID}


@flusimApp.get("/runModel/results/{taskID}")
async def downloadSimulationResults(taskID: str, cleanup: BackgroundTasks):
    """
    Async route function to obtain the results of a simulation experiment.

    Parameters:
        taskID (str): The ID distinguishing this simulation task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove simulation data once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist or has no results
            (uses 404 status code) or is still running (raises 503 status code).
    """
    TaskData = activeTasks.get(taskID)
    if TaskData is None:
        raise HTTPException(
            404, "The simulation with the requested ID could not be found"
        )

    currentStatus = TaskData.status
    if currentStatus != "completed":
        raise HTTPException(503, "The requested simulation is still ongoing")

    filePath = TaskData.results

    if not filePath or not os.path.exists(filePath):
        raise HTTPException(
            404,
            """
The analysis results for the simulation with the requested ID could not be found
            """,
        )

    cleanup.add_task(closeTask, taskID)

    return FileResponse(filePath, filename=os.path.basename(filePath))


# R0 analysis


# Calibration (receive r0, return beta)
# R0 analysis
async def calibrateR0(taskID: str, params: overrideTemplate):
    """
    Async function to calculate beta for a given basic reproduction number

    Parameters:
        taskID (str): The ID distinguishing this server task.

        params (overrideTemplate): The parameters to calculate beta for,
            including the target r0.
    """

    try:
        # Wait 1 second for the websocket to connect
        await asyncio.sleep(1)

        # Get relevant attributes from config file and sim data
        taskData = activeTasks.get(taskID)
        if taskData is None:
            raise ValueError("The task with the requested ID could not be found")
        community = params.name
        if params.description is None:
            raise ValueError("No target r0 was provided")
        r0 = float(params.description)
        print(f"R0 calibration to {r0} requested, ID = {taskID}")

        # Log the files that will be created over the course of the simulation
        taskData.files = set()

        # Generate config files
        await updateStatus(taskData, "generatingToolbox")
        toolboxPath = generateToolboxConfig(taskData, "500", "-r0Calibration")
        await updateStatus(taskData, "generatingConfig")
        paramPath = generateCalibrationConfig(taskData, params)
        print(
            f"Toolbox file located at {toolboxPath}; parameters located at {paramPath}"
        )

        # Run the Flusim simulation
        r0, interval, beta = await runCalibration(r0, community, paramPath, toolboxPath)
        print(
            f"Estimated beta: {beta} (achieves {r0} with CI [{interval[0]}, {interval[1]}])"
        )

        taskData.results = {"r0": r0, "interval": interval, "beta": beta}
        await updateStatus(taskData, "completed")
    except Exception as e:
        # TODO: Add more info to errors like this
        print(f"Error while calibrating r0 {taskID}:\n{e}")
        await updateStatus(activeTasks[taskID], "error")
        await closeTask(taskID)


@flusimApp.post("/r0/calibrate", status_code=202)
async def r0CalibrationRoute(config: overrideTemplate) -> dict[str, str]:
    """
    Async route function to calculate beta for a given basic reproduction number

    Parameters:
        config (overrideTemplate): The r0 and parameters to calculate beta with.

    Returns:
        dict: A dictionary containing the ID assigned to this particular
            simulation run. A dictionary is used rather than returning the ID
            directly as an int to ensure corrupted data is not read by the
            dashboard client.
    """

    # TODO: Make taskID a cookie if it helps with reload preservation
    taskID = str(uuid.uuid4())
    activeTasks[taskID] = TaskData(taskID)

    calculateTask = asyncio.create_task(calibrateR0(taskID, config))

    activeTasks[taskID].tasks.add(calculateTask)

    return {"taskID": taskID}


@flusimApp.get("/r0/calibrate/results/{taskID}")
async def r0CalibrationResults(taskID: str, cleanup: BackgroundTasks):
    """
    Async route function to obtain the results of r0 calibration.

    Parameters:
        taskID (str): The ID distinguishing this server task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove simulation data once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist or has no results
            (uses 404 status code) or is still running (raises 503 status code).
    """
    TaskData = activeTasks.get(taskID)
    if TaskData is None:
        raise HTTPException(404, "The task with the requested ID could not be found")

    currentStatus = TaskData.status
    if currentStatus != "completed":
        raise HTTPException(503, "The requested task is still ongoing")

    resultsDict = TaskData.results

    if not isinstance(resultsDict, dict):
        raise HTTPException(
            404,
            "The beta estimate for the task with the requested ID could not be found",
        )

    cleanup.add_task(closeTask, taskID)

    return resultsDict


# Calculation (receive beta, return r0)
async def calculateR0(taskID: str, params: communityOverride):
    """
    Async function to calculate the basic reproduction number for a given scenario

    Parameters:
        taskID (str): The ID distinguishing this server task.

        params (communityOverride): The parameters to calculate the reproduction
            number for.
    """

    try:
        # Wait 1 second for the websocket to connect
        await asyncio.sleep(1)

        # Get relevant attributes from config file and sim data
        taskData = activeTasks.get(taskID)
        if taskData is None:
            raise ValueError("The task with the requested ID could not be found")
        community = params.name
        print(f"R0 calculation requested, ID = {taskID}")

        # Log the files that will be created over the course of the simulation
        taskData.files = set()

        # Generate config files
        await updateStatus(taskData, "generatingToolbox")
        toolboxPath = generateToolboxConfig(taskData, "1000", "-r0Calculation")
        await updateStatus(taskData, "generatingConfig")
        paramPath = generateCalibrationConfig(taskData, params)
        print(
            f"Toolbox file located at {toolboxPath}; parameters located at {paramPath}"
        )

        # Run the Flusim simulation
        r0, interval = await runCalculation(community, paramPath, toolboxPath)
        print(f"Estimated R0: {r0} with CI of [{interval[0]}, {interval[1]}]")

        taskData.results = {"r0": r0, "interval": interval}
        await updateStatus(taskData, "completed")
    except Exception as e:
        # TODO: Add more info to errors like this
        print(f"Error while calculating r0 {taskID}:\n{e}")
        await updateStatus(activeTasks[taskID], "error")
        await closeTask(taskID)


@flusimApp.post("/r0/calculate", status_code=202)
async def r0CalculationRoute(config: communityOverride) -> dict[str, str]:
    """
    Async route function to calculate the basic reproduction number for a given scenario

    Parameters:
        config (communityOverride): The community and parameters
            to calculate r0 with.

    Returns:
        dict: A dictionary containing the ID assigned to this particular
            simulation run. A dictionary is used rather than returning the ID
            directly as an int to ensure corrupted data is not read by the
            dashboard client.
    """

    # TODO: Make taskID a cookie if it helps with reload preservation
    taskID = str(uuid.uuid4())
    activeTasks[taskID] = TaskData(taskID)

    calculateTask = asyncio.create_task(calculateR0(taskID, config))

    activeTasks[taskID].tasks.add(calculateTask)

    return {"taskID": taskID}


@flusimApp.get("/r0/calculate/results/{taskID}")
async def r0CalculationResults(taskID: str, cleanup: BackgroundTasks):
    """
    Async route function to obtain the results of r0 calculation.

    Parameters:
        taskID (str): The ID distinguishing this server task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove simulation data once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist or has no results
            (uses 404 status code) or is still running (raises 503 status code).
    """
    TaskData = activeTasks.get(taskID)
    if TaskData is None:
        raise HTTPException(404, "The task with the requested ID could not be found")

    currentStatus = TaskData.status
    if currentStatus != "completed":
        raise HTTPException(503, "The requested task is still ongoing")

    resultsDict = TaskData.results

    if not isinstance(resultsDict, dict):
        raise HTTPException(
            404,
            "The r0 estimate for the task with the requested ID could not be found",
        )

    cleanup.add_task(closeTask, taskID)

    return resultsDict
