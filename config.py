import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Base directories
ROOT_DIR = Path(__file__).resolve().parent

# Required configurations
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_NAME = os.getenv("BOT_NAME", "Dark-Matter")

# Local AI (Ollama) configurations
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2")

# Optional configurations
DB_PATH_ENV = os.getenv("DB_PATH", "data/database.db")
DB_PATH = ROOT_DIR / DB_PATH_ENV
LOG_LEVEL_ENV = os.getenv("LOG_LEVEL", "INFO").upper()

# Ensure directories exist
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging() -> None:
    """Configures global logging to stream console and file loggers."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    level = getattr(logging, LOG_LEVEL_ENV, logging.INFO)
    
    # Set up basic configuration
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOGS_DIR / "bot.log", encoding="utf-8")
        ]
    )
    
    # Silence chatty libraries
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

def validate_config() -> None:
    """Validates that all critical settings are loaded; throws ValueError otherwise."""
    missing = []
    if not DISCORD_TOKEN:
        missing.append("DISCORD_TOKEN")
        
    if missing:
        raise ValueError(
            f"Missing required configurations: {', '.join(missing)}. "
            f"Ensure these are specified in your .env file."
        )

# Perform validation on load
validate_config()
