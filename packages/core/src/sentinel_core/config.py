import os


APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./sentinel.db",
)

# Cookies carrying session tokens must use the Secure flag in any
# non-development environment so they are never transmitted over plain HTTP.
COOKIE_SECURE: bool = APP_ENV != "development"

