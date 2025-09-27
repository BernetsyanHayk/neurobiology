"""
This is the main file of the backend system, connect all files and microservices here
"""
import asyncio, json, os, logging, time, importlib, sys
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from time import monotonic
from starlette.responses import JSONResponse
from backend.limiter import (limiter, suspend_ip, suspended_ips, globalTasks, remove_suspended_ip, whitelisted_ips)
import backend.global_variables as configs

load_dotenv()
configs.load_configs()
configName = os.getenv('SERVER_CONFIG')
MICROSERVICES_FILE = "./configs/microservices.json"
ROUTES_FILE = "./configs/routes.json"
ORIGINS_FILE = "./configs/origins.json"
MAX_CONNECTION_AGE = 600
SUSPENSION_PERIOD = 200
# Set a static token needed for the cronjobs
RUN_QUEUE_TOKEN = os.getenv("RUN_QUEUE_TOKEN")
VALID_MICROSERVICE_TOKEN = os.getenv("VALID_MICROSERVICE_TOKEN")
CLEAN_TEMP_FOLDER_TOKEN = os.getenv("CLEAN_TEMP_FOLDER_TOKEN")

routes_modules = []
try:
    with open(ROUTES_FILE) as f:
        routes_modules = json.load(f)["routes"]

    routes = []
    for module in routes_modules:
        try:
            routes.append(importlib.import_module(module).router)
        except Exception as e:
            logging.error(f"Failed to import {module}: {e}")
except Exception as e:
    logging.exception(f"Error loading routers: {e}")

################################################
# end configure cron jobs
################################################

app = FastAPI(
    debug=configs.MISC_CONFIG.get("debug_mode", "false")=="true",
    docs_url=None, # disables Swagger UI at /docs
    openapi_url=None # disables OpenAPI JSON at /openapi.json
    )

app.state.limiter = limiter

# Define global log format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Remove all existing handlers (important!)
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Apply new logging configuration globally
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Apply the same format to Uvicorn logs
for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

################################################
# Array of allowed origins
################################################
origins = []
try:
    with open(ORIGINS_FILE) as f:
        origins = json.load(f)["origins"]
    logging.info("Allowed origins loaded successfully.")
except Exception as e:
    logging.exception(f"Error loading allowed origins: {e}")


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )
################################################
# Function for IP suspension
################################################
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    start_time4 = time.time()
    ip = get_remote_address(request)
    if ip in suspended_ips and ip not in whitelisted_ips:
        logging.info("Suspended IP: ", ip)
        response = JSONResponse(
            content={
                "message": "IP is suspended. Try again later."
            },
            status_code=429)
    else:
        await suspend_ip(ip, SUSPENSION_PERIOD)
        response = JSONResponse(
            content={
                "message": "Rate limit exceeded. Try again later."
            },
            status_code=429)

    end_time4 = time.time()
    total_time4 = end_time4 - start_time4
    logging.info(f"RateLimitExceededChecking took {total_time4:.2f} seconds to process")
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


async def close_session(session):
    session.close()

################################################
# Function for blocking requests and setting a limit on the number of requests per server
################################################
@app.middleware("http")
async def check_ip(request: Request, call_next):
    http_method = request.method
    request_url = str(request.url)
    logging.info(f"client URL - {request_url}, method - {http_method}")
    if ".env" in request_url and "assets/environment" not in request_url:
        return JSONResponse(content={"error": "You are not allowed to see this page"}, status_code=405)
    if ".git" in request_url:
        return JSONResponse(content={"error": "You are not allowed to see this page"}, status_code=405)
    if "configs" in request_url:
        return JSONResponse(content={"error": "You are not allowed to see this page"}, status_code=405)
    if "DB_connection" in request_url:
        return JSONResponse(content={"error": "You are not allowed to see this page"}, status_code=405)

    ip = get_remote_address(request)

    # Check if the IP is suspended
    if ip in suspended_ips and ip not in whitelisted_ips:
        # IP is suspended, return a custom response
        task = asyncio.create_task(remove_suspended_ip(ip, SUSPENSION_PERIOD))
        globalTasks.append(task)

        response = JSONResponse(
            content={"message": "IP is suspended. Try again later."},
            status_code=429)
    else:
        # Cancel global tasks
        for task in globalTasks:
            task.cancel()
        start_time = monotonic()  # Record the start time
        elapsed_time = monotonic() - start_time  # Calculate elapsed time
        response = await call_next(request)
        delta = elapsed_time
        if delta > MAX_CONNECTION_AGE:
            await close_session(request.state.db)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_microservices(file_path):
    """
    Reads microservices information from a file.
    Each line in the file should follow the format:
    service_name,router_variable
    """
    microservices = []
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        for key, value in data.items():
            microservices.append({"name": key, "router_variable": value})
    except FileNotFoundError:
        logging.error(f"Microservices file not found: {file_path}")
    return microservices

def mount_microservices():
    """
    Mounts microservices defined in the microservices configuration file.
    """

    microservices = fetch_microservices(MICROSERVICES_FILE)

    for service in microservices:
        try:
            # Dynamically import the router variable
            module = importlib.import_module(f"backend.services.{service['name']}.main")
            router: APIRouter = getattr(module, service['router_variable'])
            app.include_router(
                router,
                prefix=f"/{{client_name}}/microservices/{service['name']}",
                tags=[f"microservice:{service['name']}"]
            )
        except Exception as e:
            logging.error(f"Failed to mount microservice {service['name']}: {e}")

###################################
# Mount microservices
###################################
try:
    mount_microservices()
    logging.info("Microservices mounted successfully.")

except Exception as e:
    logging.error(f"Error during microservice mounting: {e}")

###################################
# Mount routers
###################################
try:
    for router in routes:
        app.include_router(router)
    logging.info("Routes attached successfully.")
except Exception as e:
    logging.error(f"Error during router fetching: {e}")

