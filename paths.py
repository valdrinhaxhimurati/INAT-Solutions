from pathlib import Path
import os

APP_NAME = "INAT Solutions"

def program_data() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / APP_NAME

def local_data() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_NAME

def data_dir() -> Path:
    base = program_data() / "data"
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base
    except PermissionError:
        alt = local_data() / "data"
        alt.mkdir(parents=True, exist_ok=True)
        return alt

def logs_dir() -> Path:
    base = program_data() / "logs"
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base
    except PermissionError:
        alt = local_data() / "logs"
        alt.mkdir(parents=True, exist_ok=True)
        return alt