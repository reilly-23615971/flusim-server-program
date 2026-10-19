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

from ServerFiles.ModelSchema import CommunityOverride, ModelGuideFile, OverrideTemplate
from ServerFiles.R0Functions import (
    generate_calibration_config,
    run_calculation,
    run_calibration,
)
from ServerFiles.SharedResources import (
    DELETE_GENERATED_FILES,
    EXECUTABLE_LOCATION,
    TOOLBOX_LOCATION,
    clear_files,
    update_status,
)
from ServerFiles.SimulationFunctions import (
    asir,
    display_time,
    epidemic,
    generate_toolbox_config,
    run_simulation,
)
from ServerFiles.Types import COMMUNITY_NAMES, TaskData, active_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function to cancel any remaining tasks when the app shuts down
    """
    yield
    # Cancel any remaining processes and delete remaining files
    tasks_to_close = list(active_tasks.keys())
    for task in tasks_to_close:
        # TODO: Is sending one last message before sockets disconnect possible?
        # await update_status(active_tasks[task], "shutdown")
        await close_task(task)


# Logging config
# TODO: Try to fix the logging loop again without --no-reload
os.makedirs("temp-files", exist_ok=True)
logging.basicConfig(
    filename="temp-files/server-app-logs.txt",
    filemode="a",
    format="%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

# Throw error if Flusim files aren't present
if not os.path.isfile(TOOLBOX_LOCATION):
    raise FileNotFoundError(f"""
Flusim toolbox files not found. Ensure that this application is present in the
same directory as the Flusim simulation files, such that the toolbox program is
located at "{TOOLBOX_LOCATION}".
    """)
if not os.path.isfile(EXECUTABLE_LOCATION):
    raise FileNotFoundError(f"""
Flusim simulation engine executable not found. Ensure that the executable has
been built (see the Flusim documentation for more info) and is located at
"{EXECUTABLE_LOCATION}".
    """)


# Define main Flusim app
flusim_server_app = FastAPI(lifespan=lifespan)

# CORS Middleware for ensuring only the web application can make requests
flusim_server_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with production URLs
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


# Functions and routes for multiple tasks
async def close_task(task_id: str):
    """
    Async wrapper to ensure TaskData objects are properly cleaned up
    and tasks are fully cancelled before files are deleted.

    Parameters:
        task_id (str): The ID distinguishing this server task.
    """
    task_data = active_tasks.get(task_id)
    if task_data is None:
        return

    # Cancel tasks, delete files and remove simulation data
    if task_data.process is not None:
        task_data.process.terminate()
    await task_data.stop_tasks()
    if DELETE_GENERATED_FILES:
        clear_files(task_data.files)
    del active_tasks[task_id]
    print(f"[close_task] Finished closing task with ID {task_id}\n\n")


@flusim_server_app.websocket("/status/{task_id}")
async def status_websocket(websocket: WebSocket, task_id: str):
    """
    Websocket route to deliver task status updates live

    Parameters:
        websocket (WebSocket): The websocket to send updates to.

        task_id (str): The ID distinguishing this server task.

    Raises:
        WebSocketException: If the specified ID does not exist (uses
            1008 status code).
    """
    await websocket.accept()
    task_data = active_tasks.get(task_id)
    if task_data is None:
        raise WebSocketException(
            1008, "The task with the requested ID could not be found"
        )

    task_data.websockets.append(websocket)

    try:
        # Send current status
        await websocket.send_json({"status": task_data.status})

        # Keep connection open to send updates
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        task_data.websockets.remove(websocket)


@flusim_server_app.delete("/cancel/{task_id}", status_code=204)
async def stop_task_route(task_id: str, cleanup: BackgroundTasks):
    """
    Async route function to stop a running task.

    Parameters:
        task_id (str): The ID distinguishing this server task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove excess files once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist (uses 404 status
            code).
    """
    task_data = active_tasks.get(task_id)
    if task_data is None:
        raise HTTPException(404, "The task with the requested ID could not be found")
    cleanup.add_task(close_task, task_id)


# Running simulation experiments
async def run_model(task_id: str, config: ModelGuideFile):
    """
    Async function to run a simulation experiment based on parameters
    from the dashboard, then zip the analysed statistics.

    Parameters:
        task_id (str): The ID distinguishing this simulation task.

        config (ModelGuideFile): The parameters and other settings that
            will define the simulation experiment.
    """
    try:
        # Wait 1 second for the websocket to connect
        await asyncio.sleep(1)
        overall_start_time = datetime.now()

        # Get relevant attributes from config file and sim data
        task_data = active_tasks.get(task_id)
        if task_data is None:
            raise ValueError("The simulation with the requested ID could not be found")
        file_id = config.description
        community = config.community_used[0]
        middle_joint = config.middle_joint
        print(f"Simulation received; name = {config.name}, ID = {task_id}")

        # Log the files that will be created over the course of the simulation
        task_data.files = set()
        analysis_files = []

        # Generate toolbox config file
        await update_status(task_data, "generating_config")
        toolbox_path = generate_toolbox_config(task_data, file_id, middle_joint)
        print(f"Toolbox file located at {toolbox_path}")

        # Run the Flusim simulation experiment
        await run_simulation(task_data, file_id, config, toolbox_path)

        # TODO: Use middle joint to determine analyses to run
        # (or find a way to send the data forms to the server directly)

        # for now, just get the standard analyses the dashboard uses

        # Daily infection epidemic curve
        await update_status(task_data, "toolbox_analysis0")
        analysis_files += await asyncio.to_thread(
            epidemic,
            task_data,
            file_id,
            community,
            cumulative=True,
            toolbox_path=toolbox_path,
        )

        # Cumulative infection epidemic curve
        await update_status(task_data, "toolbox_analysis1")
        analysis_files += await asyncio.to_thread(
            epidemic,
            task_data,
            file_id,
            community,
            cumulative=False,
            toolbox_path=toolbox_path,
        )

        # Age-separated infection rates
        await update_status(task_data, "toolbox_analysis2")
        analysis_files += await asyncio.to_thread(
            asir,
            task_data,
            file_id,
            community,
            middle_joint,
            toolbox_path=toolbox_path,
        )

        # Vaccinated age-separated infection rates
        if middle_joint and "+vaccine" in middle_joint:
            await update_status(task_data, "toolbox_analysis3")
            analysis_files += await asyncio.to_thread(
                asir,
                task_data,
                file_id,
                community,
                middle_joint,
                vaccinated_only=True,
                toolbox_path=toolbox_path,
            )

        # If all else fails and no analyses were specified, run epidemic
        if not analysis_files:
            print("No analyses specified; defaulting to epidemic")
            analysis_files += await asyncio.to_thread(
                epidemic,
                task_data,
                file_id,
                community,
                toolbox_path=toolbox_path,
            )

        print("\nAnalysis files:")
        for file in analysis_files:
            print("   ", file)

        # Zip together the analysis files
        await update_status(task_data, "zipping_analysis")
        zip_path = f"temp-files/analysis_files_{file_id}_.zip"
        task_data.files.add(zip_path)
        with zipfile.ZipFile(zip_path, mode="w") as analysis:
            for file in analysis_files:
                analysis.write(file)

        task_data.results = zip_path

        print(
            f"\nSimulation request for session {file_id} complete in "
            f"{display_time(overall_start_time)}, ready to return data\n"
        )

        await update_status(task_data, "completed")
    except Exception as e:
        # TODO: Add more info to errors like this
        print(f"Error while running simulation {task_id}:\n{e}")
        await update_status(active_tasks[task_id], "error")
        await close_task(task_id)


# TODO: run_model_task might sometimes become its own child and cause
# recursion errors when cancelling it? Investigate
@flusim_server_app.post("/run_model", status_code=202)
async def run_model_route(config: ModelGuideFile) -> dict[str, str]:
    """
    Async route function to begin a simulation experiment and give the
    dashboard an ID to poll for status updates.

    Parameters:
        config (ModelGuideFile): The parameters and other settings that
            will define the simulation experiment.

    Returns:
        dict: A dictionary containing the ID assigned to this particular
            simulation run. A dictionary is used rather than returning the ID
            directly as an int to ensure corrupted data is not read by the
            dashboard client.
    """
    # TODO: Make task_id a cookie if it helps with reload preservation
    task_id = str(uuid.uuid4())
    active_tasks[task_id] = TaskData(task_id)

    run_model_task = asyncio.create_task(run_model(task_id, config))

    active_tasks[task_id].tasks.add(run_model_task)

    return {"task_id": task_id}


@flusim_server_app.get("/run_model/results/{task_id}")
async def download_simulation_results(task_id: str, cleanup: BackgroundTasks):
    """
    Async route function to obtain the results of a simulation experiment.

    Parameters:
        task_id (str): The ID distinguishing this simulation task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove simulation data once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist or has no results
            (uses 404 status code) or is still running (raises 503 status code).
    """
    task_data = active_tasks.get(task_id)
    if task_data is None:
        raise HTTPException(
            404, "The simulation with the requested ID could not be found"
        )

    current_status = task_data.status
    if current_status != "completed":
        raise HTTPException(503, "The requested simulation is still ongoing")

    file_path = task_data.results

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            404,
            """
The analysis results for the simulation with the requested ID could not be found
            """,
        )

    cleanup.add_task(close_task, task_id)

    return FileResponse(file_path, filename=os.path.basename(file_path))


# R0 analysis


# Calibration (receive r0, return beta)
# R0 analysis
async def calibrate_r0(task_id: str, params: OverrideTemplate):
    """
    Async function to calculate beta for a given basic reproduction number

    Parameters:
        task_id (str): The ID distinguishing this server task.

        params (OverrideTemplate): The parameters to calculate beta for,
            including the target r0.
    """

    try:
        # Wait 1 second for the websocket to connect
        await asyncio.sleep(1)

        # Get relevant attributes from config file and sim data
        task_data = active_tasks.get(task_id)
        if task_data is None:
            raise ValueError("The task with the requested ID could not be found")
        community = params.name
        assert community in COMMUNITY_NAMES
        if params.description is None:
            raise ValueError("No target r0 was provided")
        r0 = float(params.description)
        print(f"R0 calibration to {r0} requested, ID = {task_id}")

        # Log the files that will be created over the course of the simulation
        task_data.files = set()

        # Generate config files
        await update_status(task_data, "generatingToolbox")
        toolbox_path = generate_toolbox_config(task_data, "500", "-r0Calibration")
        await update_status(task_data, "generating_config")
        parameter_path = generate_calibration_config(task_data, params)
        print(
            f"Toolbox file located at {toolbox_path}; "
            f"parameters located at {parameter_path}"
        )

        # Run the Flusim simulation
        r0, interval, beta = await run_calibration(
            r0, community, parameter_path, toolbox_path
        )
        print(
            f"Estimated beta: {beta} (achieves {r0} "
            f"with CI [{interval[0]}, {interval[1]}])"
        )

        task_data.results = {"r0": r0, "interval": interval, "beta": beta}
        await update_status(task_data, "completed")
    except Exception as e:
        # TODO: Add more info to errors like this
        print(f"Error while calibrating r0 {task_id}:\n{e}")
        await update_status(active_tasks[task_id], "error")
        await close_task(task_id)


@flusim_server_app.post("/r0/calibrate", status_code=202)
async def r0_calibration_route(config: OverrideTemplate) -> dict[str, str]:
    """
    Async route function to calculate beta for a given basic reproduction number

    Parameters:
        config (OverrideTemplate): The r0 and parameters to calculate beta with.

    Returns:
        dict: A dictionary containing the ID assigned to this particular
            simulation run. A dictionary is used rather than returning the ID
            directly as an int to ensure corrupted data is not read by the
            dashboard client.
    """

    # TODO: Make task_id a cookie if it helps with reload preservation
    task_id = str(uuid.uuid4())
    active_tasks[task_id] = TaskData(task_id)

    calculate_task = asyncio.create_task(calibrate_r0(task_id, config))

    active_tasks[task_id].tasks.add(calculate_task)

    return {"task_id": task_id}


@flusim_server_app.get("/r0/calibrate/results/{task_id}")
async def r0_calibration_results(task_id: str, cleanup: BackgroundTasks):
    """
    Async route function to obtain the results of r0 calibration.

    Parameters:
        task_id (str): The ID distinguishing this server task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove simulation data once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist or has no results
            (uses 404 status code) or is still running (raises 503 status code).
    """
    task_data = active_tasks.get(task_id)
    if task_data is None:
        raise HTTPException(404, "The task with the requested ID could not be found")

    current_status = task_data.status
    if current_status != "completed":
        raise HTTPException(503, "The requested task is still ongoing")

    results_dict = task_data.results

    if not isinstance(results_dict, dict):
        raise HTTPException(
            404,
            "The beta estimate for the task with "
            "the requested ID could not be found",
        )

    cleanup.add_task(close_task, task_id)

    return results_dict


# Calculation (receive beta, return r0)
async def calculate_r0(task_id: str, params: CommunityOverride):
    """
    Async function to calculate the basic reproduction number for a given
    scenario

    Parameters:
        task_id (str): The ID distinguishing this server task.

        params (CommunityOverride): The parameters to calculate the
            reproduction number for.
    """

    try:
        # Wait 1 second for the websocket to connect
        await asyncio.sleep(1)

        # Get relevant attributes from config file and sim data
        task_data = active_tasks.get(task_id)
        if task_data is None:
            raise ValueError("The task with the requested ID could not be found")
        community = params.name
        print(f"R0 calculation requested, ID = {task_id}")

        # Log the files that will be created over the course of the simulation
        task_data.files = set()

        # Generate config files
        await update_status(task_data, "generatingToolbox")
        toolbox_path = generate_toolbox_config(task_data, "1000", "-r0_calculation")
        await update_status(task_data, "generating_config")
        parameter_path = generate_calibration_config(task_data, params)
        print(
            f"Toolbox file located at {toolbox_path}; "
            f"parameters located at {parameter_path}"
        )

        # Run the Flusim simulation
        r0, interval = await run_calculation(community, parameter_path, toolbox_path)
        print(f"Estimated R0: {r0} with CI of [{interval[0]}, {interval[1]}]")

        task_data.results = {"r0": r0, "interval": interval}
        await update_status(task_data, "completed")
    except Exception as e:
        # TODO: Add more info to errors like this
        print(f"Error while calculating r0 {task_id}:\n{e}")
        await update_status(active_tasks[task_id], "error")
        await close_task(task_id)


@flusim_server_app.post("/r0/calculate", status_code=202)
async def r0_calculation_route(config: CommunityOverride) -> dict[str, str]:
    """
    Async route function to calculate the basic reproduction number for a given
    scenario

    Parameters:
        config (CommunityOverride): The community and parameters
            to calculate r0 with.

    Returns:
        dict: A dictionary containing the ID assigned to this particular
            simulation run. A dictionary is used rather than returning the ID
            directly as an int to ensure corrupted data is not read by the
            dashboard client.
    """

    # TODO: Make task_id a cookie if it helps with reload preservation
    task_id = str(uuid.uuid4())
    active_tasks[task_id] = TaskData(task_id)

    calculate_task = asyncio.create_task(calculate_r0(task_id, config))

    active_tasks[task_id].tasks.add(calculate_task)

    return {"task_id": task_id}


@flusim_server_app.get("/r0/calculate/results/{task_id}")
async def r0_calculation_results(task_id: str, cleanup: BackgroundTasks):
    """
    Async route function to obtain the results of r0 calculation.

    Parameters:
        task_id (str): The ID distinguishing this server task.

        cleanup (BackgroundTasks): An object that will have file removal
            functions attached to it to remove simulation data once this
            function finishes running.

    Raises:
        HTTPException: If the specified ID does not exist or has no results
            (uses 404 status code) or is still running (raises 503 status code).
    """
    task_data = active_tasks.get(task_id)
    if task_data is None:
        raise HTTPException(404, "The task with the requested ID could not be found")

    current_status = task_data.status
    if current_status != "completed":
        raise HTTPException(503, "The requested task is still ongoing")

    results_dict = task_data.results

    if not isinstance(results_dict, dict):
        raise HTTPException(
            404,
            "The r0 estimate for the task with the requested ID could not be found",
        )

    cleanup.add_task(close_task, task_id)

    return results_dict
