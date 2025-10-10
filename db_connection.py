# -*- coding: utf-8 -*-
import os
import re
import json
import sqlite3
import traceback

ROOT = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(ROOT, "config.json")
_SQLITE_PATH = os.path.join(ROOT, "db", "datenbank.sqlite")

# --- Config helpers -------------------------------------------------------
def _read_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _write_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        pass

# --- SQL adaptation ------------------------------------------------------
_RE_SQLITE_PLACEHOLDER = re.compile(r'(?<!%)%s')         # %s -> ?
_RE_SCHEMA_QUAL = re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\.')  # public. -> ''
_RE_NAMED = re.compile(r'%\(([^)]+)\)s')                 # %(name)s

def _adapt_sql_for_sqlite(sql: str) -> str:
    if not sql:
        return sql
    sql = _RE_SCHEMA_QUAL.sub('', sql)
    sql = _RE_SQLITE_PLACEHOLDER.sub('?', sql)
    return sql

# --- Wrappers ------------------------------------------------------------
class CursorWrapper:
    def __init__(self, cur, is_sqlite: bool):
        self._cur = cur
        self._is_sqlite = is_sqlite

    def execute(self, sql, params=None):
        if self._is_sqlite:
            # named params: %(name)s -> ? und dict -> tuple in Reihenfolge
            if isinstance(params, dict):
                keys = _RE_NAMED.findall(sql)
                sql = _RE_SCHEMA_QUAL.sub('', sql)
                sql = _RE_NAMED.sub('?', sql)
                params = tuple(params[k] for k in keys)
            else:
                sql = _adapt_sql_for_sqlite(sql)
        if params is None:
            return self._cur.execute(sql)
        return self._cur.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        if self._is_sqlite:
            if seq_of_params and isinstance(next(iter(seq_of_params)), dict):
                keys = _RE_NAMED.findall(sql)
                sql = _RE_SCHEMA_QUAL.sub('', sql)
                sql = _RE_NAMED.sub('?', sql)
                seq_of_params = [tuple(p[k] for k in keys) for p in seq_of_params]
            else:
                sql = _adapt_sql_for_sqlite(sql)
        return self._cur.executemany(sql, seq_of_params)

    def fetchall(self):
        return self._cur.fetchall()

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall_dict(self):
        rows = self._cur.fetchall()
        try:
            return [dict(r) for r in rows]
        except Exception:
            return [{i: v for i, v in enumerate(r)} for r in rows]

    def fetchone_dict(self):
        r = self._cur.fetchone()
        if r is None:
            return None
        try:
            return dict(r)
        except Exception:
            return {i: v for i, v in enumerate(r)}

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass

    # Context manager support so "with conn.cursor() as cur:" works
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.close()
        except Exception:
            pass
        # don't suppress exceptions
        return False

    # proxy any other attributes
    def __getattr__(self, name):
        return getattr(self._cur, name)

class ConnectionWrapper:
    def __init__(self, conn, is_sqlite: bool):
        self._conn = conn
        self._is_sqlite = is_sqlite
        self.is_sqlite = is_sqlite
        # ensure sqlite returns Row objects for easy dict conversion
        if self._is_sqlite:
            try:
                self._conn.row_factory = sqlite3.Row
            except Exception:
                pass

    def cursor(self, *args, **kwargs):
        """
        Akzeptiert beliebige Argumente (z.B. cursor_factory) und erstellt
        einen echten Cursor der zugrundeliegenden Connection. Falls
        cursor_factory übergeben wird, wird dieser Key stillschweigend ignoriert,
        damit bestehender Code (der oft inkorrekt ein generator-Objekt übergibt)
        nicht scheitert.
        """
        # entferne cursor_factory falls vorhanden (psycopg2 kann ihn verarbeiten,
        # sqlite3 nicht; wir vereinheitlichen, indem wir ihn ignorieren)
        kwargs.pop("cursor_factory", None)
        cur = self._conn.cursor(*args, **kwargs)
        return CursorWrapper(cur, self._is_sqlite)
    @property
    def is_sqlite_conn(self):
        """Kompatibler Property-Name, falls anderer Code is_sqlite erwartet."""
        return self._is_sqlite

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql, seq_of_params):
        cur = self.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self):
        try:
            return self._conn.commit()
        except Exception:
            pass

    def rollback(self):
        try:
            return self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            return self._conn.close()
        except Exception:
            pass

    # expose real connection for advanced usage
    @property
    def raw(self):
        return self._conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.commit()
        finally:
            self.close()

# --- DB connect / policy -------------------------------------------------
def _sqlite_connect():
    os.makedirs(os.path.dirname(_SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(_SQLITE_PATH)
    return ConnectionWrapper(conn, is_sqlite=True)

def _try_postgres_connect(dsn):
    import psycopg2
    conn = psycopg2.connect(dsn)
    return ConnectionWrapper(conn, is_sqlite=False)

def get_db():
    """
    Liefert ConnectionWrapper:
     - Standard: lokale SQLite
     - falls in config.json use_remote True und db_url gesetzt -> versucht Postgres, sonst SQLite
    """
    cfg = _read_config()
    use_remote = cfg.get("use_remote", False)
    remote_url = cfg.get("db_url") or os.environ.get("INAT_DB_URL")

    if use_remote and remote_url:
        try:
            return _try_postgres_connect(remote_url)
        except Exception:
            # Fallback auf SQLite und Logging
            try:
                with open(os.path.join(ROOT, "error.log"), "a", encoding="utf-8") as ef:
                    ef.write("Postgres connect failed, falling back to SQLite:\n")
                    ef.write(traceback.format_exc())
            except Exception:
                pass
            return _sqlite_connect()
    return _sqlite_connect()

def get_local_db():
    """
    Erzwingt lokale SQLite, unabhängig von config/Remote.
    """
    return _sqlite_connect()

def get_local_db_path():
    """Gibt den Pfad zur lokalen SQLite-DB zurück (die auch get_local_db nutzt)."""
    return _SQLITE_PATH

# --- Settings helpers ----------------------------------------------------
def enable_remote(db_url):
    cfg = _read_config()
    cfg["use_remote"] = True
    cfg["db_url"] = db_url
    _write_config(cfg)

def disable_remote():
    cfg = _read_config()
    cfg["use_remote"] = False
    cfg.pop("db_url", None)
    _write_config(cfg)

def get_remote_status():
    cfg = _read_config()
    return {"use_remote": cfg.get("use_remote", False), "db_url": cfg.get("db_url")}

def test_remote_connection(db_url):
    try:
        conn = _try_postgres_connect(db_url)
        try:
            conn.close()
        except Exception:
            pass
        return True, None
    except Exception as e:
        return False, str(e)

# --- Compatibility helper -----------------------------------------------
def dict_cursor_factory(cursor):
    """
    Alte Aufrufe erwarten oft einen Iterator über dicts.
    Nutze so: for row in dict_cursor_factory(cur): ...
    """
    try:
        rows = cursor.fetchall()
    except Exception:
        return
    for r in rows:
        try:
            yield dict(r)
        except Exception:
            yield {i: v for i, v in enumerate(r)}

def connect_sqlite_at(path: str):
    if not path:
        raise ValueError("connect_sqlite_at: db_path ist None/leer. Übergib den Login-DB-Pfad.")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
    except Exception:
        pass
    return ConnectionWrapper(conn, is_sqlite=True)
