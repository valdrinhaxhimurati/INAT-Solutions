from pathlib import Path
import os

APP_NAME = "INAT Solutions"

def program_data() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / APP_NAME

def data_dir() -> Path:
    base = program_data() / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base

def users_db_path() -> Path:
    return data_dir() / "users.db"

def local_db_path() -> Path:
    return data_dir() / "datenbank.sqlite"