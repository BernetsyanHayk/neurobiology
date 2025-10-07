"""This FastAPI file defines the "do-html-action" endpoints, for various pages like - web pages, dashboards and etc. executing dynamic SQL queries based on client-provided
action keys and JSON data, with database interaction, HTTP client requests, and rate limiting. """

import logging, os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import select, insert, update
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from backend.limiter import limiter
from backend.global_functions import get_jinja_env

from backend.database.db_pool_manager import get_session_for_database
from backend.database.models import users
from backend.database.auth import hash_password, verify_password, create_access_token, create_email_token, decode_token

import smtplib
from email.message import EmailMessage
import asyncio

from backend.global_variables import RATE_LIMITER_CONFIG

RATE_LIMIT = RATE_LIMITER_CONFIG["general_rl"]

env = get_jinja_env()

load_dotenv()

REDIS_SERVER_PASSWORD = os.getenv("REDIS_SERVER_PASSWORD")
VALID_MICROSERVICE_TOKEN = os.getenv("VALID_MICROSERVICE_TOKEN")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
FRONTEND_VERIFY_URL = os.getenv("FRONTEND_VERIFY_URL", "/verify-email")

class SessionData(BaseModel):
    username: str


router = APIRouter()

# Log config
logging.basicConfig(level=logging.INFO)


def split_string_by_specific_word(input_string, delimiter):
    # Split the input string by the specific word delimiter
    split_parts = input_string.split(delimiter)
    return split_parts

# Pydantic schemas
class SignupIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginIn(BaseModel):
    email: EmailStr
    password: str

# helper: send email (runs in background)
def send_email_sync(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)

async def send_email_background(to_email: str, subject: str, body: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_email_sync, to_email, subject, body)

# Signup endpoint
@router.post("/users/signup")
async def signup(payload: SignupIn, background_tasks: BackgroundTasks):
    session_maker = await get_session_for_database()
    async with session_maker() as session:

        # check if user exists
        get_user_query = select(users.c.id).where(users.c.email == payload.email)
        get_user_query_response = await session.execute(get_user_query)

        return get_user_query_response
        if r.first():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(payload.password)
        stmt = insert(users).values(email=payload.email, hashed_password=hashed, full_name=payload.full_name)
        result = await session.execute(stmt)
        # build verification token
        user_id = (await session.execute(select(users.c.id).where(users.c.email == payload.email))).scalar_one()
        token = create_email_token({"sub": str(user_id), "email": payload.email})
        verify_link = f"{FRONTEND_VERIFY_URL}?token={token}"

        subject = "Verify your email"
        body = f"Hi,\n\nPlease verify your email by clicking the link below:\n{verify_link}\n\nIf you didn't create an account, ignore this email.\n"
        # send in background
        background_tasks.add_task(asyncio.create_task, send_email_background(payload.email, subject, body))
        return {"msg": "User created. Check your email to verify account."}