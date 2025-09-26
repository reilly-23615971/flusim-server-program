# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import os
import sys
import zipfile
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from serverFiles.ModelSchema import modelGuideFile
from serverFiles.simulationFunctions import (
    runSimulation, generateToolboxConfig, epidemic, asir, simLocation
)

from logger import Logger, LogLevel

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(os.path.join(os.getcwd(), simLocation, 'src/toolbox'))
from analysis.AnalysisStat import AnalysisStat

# Logging config (create log folder outside of project dir to avoid 
# watchfiles getting into an endless update loop)
os.makedirs('../Logs', exist_ok = True)
logging.basicConfig(
    filename = '../Logs/serverAppLogs.txt', filemode = 'a', 
    format = '%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s', 
    datefmt = '%Y-%m-%d %H:%M:%S', level = logging.WARN
)



# Set this to False to preserve files after running sim
deleteFiles = True

# Throw error if Flusim files aren't present
if not os.path.isfile('src/toolbox/toolbox.py'): raise FileNotFoundError((
    'Flusim files not found. Ensure that this application is '
    'present in the same directory as the Flusim simulation files.'
))

# Function to remove excess files
def clearFiles(files): 
    print(f'[clearFiles] Deleting the following files for cleanup purposes:')
    for f in files: print('   ', f)
    for f in files: os.remove(f)


# Define main Flusim app
flusimApp = FastAPI()

# CORS Middleware for ensuring only the web application can make requests
flusimApp.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'], # replace with production URLs
    allow_credentials = True,
    allow_methods = ['POST'],
    allow_headers = ["*"],
)

# Define route for receiving model parameters
@flusimApp.post('/runModel')
async def runModel(config: modelGuideFile, cleanup: BackgroundTasks):
    # Get relevant attributes from config file
    sessionID = config.description
    community = config.community_used[0]
    requiredData = config.middle_joint
    #simCount = len(config.simulation_sets[0].simulations)
    print(f'Simulation received; name = {config.name}, ID = {sessionID}')

    # Generate toolbox config file
    toolboxPath = generateToolboxConfig(sessionID, requiredData)
    print(f'Toolbox file located at {toolboxPath}')

    # Run the Flusim simulation
    simFiles = runSimulation(config, toolboxPath)
    print('Simulation complete\n')
    
    returnFiles = []
    # TODO: Use middle joint to determine analyses to run 
    middleCheck = """if requiredData:
        # Epidemic tool
        if 'usingEpidemic' in requiredData: 
            sumStat = (
                AnalysisStat.MEAN if 'EMean' in requiredData 
                else AnalysisStat.MEDIAN
            )
            epiCumulative = 'ECumulative' in requiredData
            epiAge = 'EAgeBased' in requiredData
            returnFiles.append(epidemic(
                community, requiredData, sessionID, summaryStat = sumStat, 
                cumulative = epiCumulative, byAge = epiAge, 
                toolboxPath = toolboxPath
            ))
        # Asir tool
        if 'usingAsir' in requiredData:
            sumStat = (
                AnalysisStat.MEAN if 'AMean' in requiredData 
                else AnalysisStat.MEDIAN
            )
            asirProportion = 'AProportion' in requiredData
            asirIndigenous = 'AIndigenous' in requiredData
            asirPregnant = 'APregnant' in requiredData
            asirVaccinated = 'AVaccinated' in requiredData
            returnFiles.append(asir(
                community, requiredData, sessionID, 
                summaryStat = sumStat, getProportion = asirProportion, 
                onlyIndigenous = asirIndigenous, onlyPregnant = asirPregnant, 
                onlyVaccinated = asirVaccinated, toolboxPath = toolboxPath
            ))"""
    # for now, just get the 3 analyses the dashboard uses
    returnFiles.append(epidemic(
        community, requiredData, sessionID, 
        cumulative = True, toolboxPath = toolboxPath
    ))
    returnFiles.append(epidemic(
        community, requiredData, sessionID, 
        cumulative = False, toolboxPath = toolboxPath
    ))
    returnFiles.append(asir(
        community, requiredData, sessionID, toolboxPath = toolboxPath
    ))
    # If all else fails and no analyses were specified, run epidemic
    if not returnFiles: 
        print('No analyses specified; defaulting to epidemic')
        returnFiles.append(epidemic(
            community, requiredData, sessionID, toolboxPath = toolboxPath
        ))

    print(f'\nAnalysis files:')
    for file in returnFiles: print('   ', file)

    # Zip together the analysis files if necessary
    if len(returnFiles) != 1:
        zipPath = f'serverFiles/{sessionID}_analysis.zip'
        with zipfile.ZipFile(zipPath, mode = 'w') as analysis:
            for file in returnFiles: analysis.write(file)
        returnFiles.append(zipPath)
        finalPath = zipPath
    # Just return lone CSV if only one analysis needed
    else: finalPath = returnFiles[0]
    
    # Schedule files created here to be removed
    if deleteFiles: cleanup.add_task(
        clearFiles, simFiles + returnFiles + [toolboxPath]
    )

    print(f'\nSimulation for session {sessionID} complete, returning data')
    return FileResponse(finalPath)
