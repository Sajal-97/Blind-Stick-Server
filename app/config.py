import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

API_KEY = os.getenv("API_KEY", "change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gps.sqlite3")

# SQLite needs this arg; Postgres doesn't.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
