import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.sqlite")

    # Secret Key
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")

    # Debug Mode
    DEBUG = os.getenv("DEBUG", "True") == "True"

    # Networking
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = os.getenv("PORT", "5000")