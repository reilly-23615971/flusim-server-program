# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import time
import json
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from modelSchema import modelGuideFile



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
async def runModel(config: modelGuideFile):
    modelConfiguration = config.model_dump(exclude_unset = True)
    print(f'Simulation received; name = {modelConfiguration["name"]}')
    # TODO: run flusim simulation and analysis tools
    # Ensure middle joint is consistent with toolbox_config.json
    time.sleep(3) # Simulate long running time
    print('Simulation complete, sending response')
    # For now this'll just send over the existing CSV file
    return FileResponse('./newcastle-coronaV96-epidemic-mean.csv')
