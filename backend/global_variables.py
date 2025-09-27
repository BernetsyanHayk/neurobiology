"""
This file contains global variables to use in the project
"""
import json, logging


JINJA_FOLDER_NAME = "jinja_files"
TEMPLATES_FOLDER_NAME = "backend/templates"
STATIC_FOLDER_NAME = "backend/static"

DBCONFIG = {}
RATE_LIMITER_CONFIG = {}
MISC_CONFIG = {}

def load_configs():
    global RATE_LIMITER_CONFIG, MISC_CONFIG
    try:
        with open("./configs/rate_limiter.json") as f:
            RATE_LIMITER_CONFIG = json.load(f)
    except Exception as e:
        logging.exception(f"Error loading rate limiter config: {e}")
        RATE_LIMITER_CONFIG = {}

    try:
        with open('./configs/misc.json') as f:
            MISC_CONFIG = json.load(f)
    except Exception as e:
        logging.exception(f"Error loading misc config: {e}")
        MISC_CONFIG = {}