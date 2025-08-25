# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import time
import os
import sys
import json
import zipfile
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from serverFiles.ModelSchema import modelGuideFile
from serverFiles.simulationFunctions import (
    runSimulation, generateToolboxConfig, epidemic, asir, simLocation
)

# Ensure Flusim imports work properly when called outside of toolbox
sys.path.append(os.path.join(os.getcwd(), simLocation, 'src/toolbox'))
from analysis.AnalysisStat import AnalysisStat


# Logging config
logging.basicConfig(
    filename = 'serverFiles/serverAppLogs.txt', filemode = 'a', 
    format = '%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s', 
    datefmt = '%Y-%m-%d %H:%M:%S', level = logging.DEBUG
)

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
    allow_origins = ['*'], # replace with Azure SWA URLs
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

    # Run the Flusim simulation
    simFiles = runSimulation(config)
    print('Simulation complete\n')
    
    returnFiles = []
    # Use middle joint to determine analyses to run
    if requiredData:
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
                cumulative = epiCumulative, byAge = epiAge
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
                onlyVaccinated = asirVaccinated
            ))
    # If all else fails, run epidemic
    if not returnFiles: 
        print('No analyses specified; defaulting to epidemic')
        returnFiles.append(epidemic(community, requiredData, sessionID))

    print(f'\nAnalysis files:')
    for file in returnFiles: print('   ', file)

    # Zip together the analysis files if necessary
    if len(returnFiles) != 1:
        zipPath = f'serverFiles/{id}_analysis.zip'
        with zipfile.ZipFile(zipPath, mode = 'w') as analysis:
            for file in returnFiles: analysis.write(file)
        returnFiles.append(zipPath)
        finalPath = zipPath
    # Just return lone CSV if only one analysis needed
    else: finalPath = returnFiles[0]
    
    # Schedule files created here to be removed
    cleanup.add_task(clearFiles, simFiles + returnFiles + [toolboxPath])

    print(f'\nSimulation for session {sessionID} complete, returning data')
    return FileResponse(finalPath)
