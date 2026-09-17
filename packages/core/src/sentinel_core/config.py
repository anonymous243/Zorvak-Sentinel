import os


APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./sentinel.db",
)
