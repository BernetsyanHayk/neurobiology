# models.py
from sqlalchemy import Table, Column, BigInteger, Text, Boolean, TIMESTAMP, func
from database import metadata

users = Table(
    "users",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("email", Text, nullable=False, unique=True),
    Column("hashed_password", Text, nullable=False),
    Column("full_name", Text),
    Column("is_active", Boolean, nullable=False, server_default="false"),
    Column("created_at", TIMESTAMP(timezone=True), server_default=func.now()),
)
