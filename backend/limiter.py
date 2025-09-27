"""
This file contains function to suspect IP's and remove suspected IP's
"""
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime, timedelta

limiter = Limiter(key_func=get_remote_address)

# Create a dictionary to track suspended IPs and the suspension end time.
suspended_ips = {}

# Whitelisted IPs (example, add your own IPs)
whitelisted_ips = {"127.0.0.1", "178.135.15.119", "18.133.195.17"}

# A list to keep track of global tasks
globalTasks = []
MAX_CONNECTION_AGE = 600  # 10 minutes


################################################
# Function to suspend ip
################################################
async def suspend_ip(ip, suspension_period):
    suspended_ips[ip] = datetime.now() + timedelta(seconds=suspension_period)


################################################
# Function to remove suspended ip
################################################
async def remove_suspended_ip(ip, suspension_period):
    await asyncio.sleep(suspension_period)
    suspended_ips.pop(ip, None)
