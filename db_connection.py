# -*- coding: utf-8 -*-
import os, json, sqlite3
import psycopg2, psycopg2.extras

# Reihenfolge: Arbeitsverzeichnis -> Script-Verzeichnis (für PyInstaller)
CFG_PATHS = [
    os.path.join(os.getcwd(), "config.json"),
    os.path.join(os.path.dirname(__file__), "config.json"),
]

# -------------------- Konfig laden --------------------
def _load_cfg() -> dict:
    for p in CFG_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

# -------------------- Postgres Verbindung --------------------
def get_db():
    """
    Liefert die Hauptdatenbank-Verbindung (PostgreSQL).
    Erwartet in config.json:
    {
        "db_backend": "postgres",
        "postgres_url": "postgresql://user:pass@host:port/dbname?...",
        ...
    }
    """
    cfg = _load_cfg()
    pg_url = (cfg.get("postgres_url") or os.environ.get("POSTGRES_URL") or "").strip()
    if not pg_url:
        raise RuntimeError("Keine PostgreSQL-URL in config.json gefunden!")

    conn = psycopg2.connect(pg_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
    conn.autocommit = False
    return conn

def dict_cursor_factory(conn):
    """liefert passende Dict-Cursor-Fabrik für psycopg2"""
    return psycopg2.extras.RealDictCursor


# -------------------- Benutzerverwaltung (SQLite) --------------------
class _SqliteCompatConnection:
    def __init__(self, inner: sqlite3.Connection):
        self._inner = inner
    def cursor(self, *a, **kw): return self._inner.cursor()
    def __getattr__(self, x): return getattr(self._inner, x)
    def __enter__(self): return self
    def __exit__(self, et, ex, tb):
        try:
            if et: self._inner.rollback()
        finally:
            self._inner.close()

def get_users_db():
    """Separate SQLite für Benutzerverwaltung"""
    cfg = _load_cfg()
    path = cfg.get("users_sqlite_path", os.path.join("db", "users.db"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return _SqliteCompatConnection(con)
