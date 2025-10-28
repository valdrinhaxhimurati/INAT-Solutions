from pathlib import Path
import os

APP_NAME = "INAT Solutions"

def program_data() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / APP_NAME

def data_dir() -> Path:
    p = program_data() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p

def logs_dir() -> Path:
    p = program_data() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

def users_db_path() -> Path:
    return data_dir() / "users.db"

def local_db_path() -> Path:
    return data_dir() / "datenbank.sqlite"

def get_app_data_dir() -> Path:
    return program_data()
