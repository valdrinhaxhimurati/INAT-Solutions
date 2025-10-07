# -*- coding: utf-8 -*-
import json, os, sqlite3
try:
    import psycopg2, psycopg2.extras
except Exception:
    psycopg2 = None

CFG_PATHS = [os.path.join(os.getcwd(), "config.json"), os.path.join(os.path.dirname(__file__), "config.json")]
def _load_cfg():
    for p in CFG_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

def dict_cursor(conn):
    if psycopg2 and isinstance(conn, psycopg2.extensions.connection):
        return psycopg2.extras.DictCursor
    return None

class _SqliteCompatConnection:
    def __init__(self, inner: sqlite3.Connection):
        self._inner = inner
    def cursor(self, *args, **kwargs):
        return self._inner.cursor()
    def __getattr__(self, item):
        return getattr(self._inner, item)
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        try:
            self._inner.__exit__(exc_type, exc, tb)
        except AttributeError:
            self._inner.close()

def get_db():
    cfg = _load_cfg()
    backend = (cfg.get("db_backend") or "").lower()
    pg_url = cfg.get("postgres_url") or os.environ.get("POSTGRES_URL")
    if backend == "postgres" or pg_url:
        if not pg_url:
            raise RuntimeError("db_backend=postgres, aber keine postgres_url gesetzt.")
        if not psycopg2:
            raise RuntimeError("psycopg2 ist nicht installiert. Bitte 'pip install psycopg2-binary'.")
        conn = psycopg2.connect(pg_url); conn.autocommit = False; return conn
    db_path = cfg.get("db_pfad", "datenbank.sqlite")
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;"); conn.execute("PRAGMA foreign_keys=ON;"); conn.execute("PRAGMA busy_timeout=5000;")
    except Exception: pass
    return _SqliteCompatConnection(conn)
