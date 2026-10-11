import os
from dotenv import load_dotenv

load_dotenv(override=True)


APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.startswith("postgresql"):
    if APP_ENV in ("production", "staging"):
        raise RuntimeError("FATAL: DATABASE_URL must be a valid PostgreSQL connection in production/staging. SQLite is strictly forbidden.")
    # In local testing without env, mandate postgresql
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required and must target PostgreSQL.")

# Cookies carrying session tokens must use the Secure flag in any
# non-development environment so they are never transmitted over plain HTTP.
COOKIE_SECURE: bool = APP_ENV != "development"

