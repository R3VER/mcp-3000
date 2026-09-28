from pathlib import Path

# Project root folder
BASE_DIR = Path(__file__).resolve().parent

# Data folders
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "output"

# Database
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "opinions.db"