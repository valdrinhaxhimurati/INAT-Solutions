# -*- coding: utf-8 -*-
import os
import re
import json
import sqlite3
import traceback
from typing import Iterable, List
import psycopg2
from paths import data_dir, local_db_path

CONFIG_PATH = str(data_dir() / "config.json")

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

import re, sqlite3

def _is_sqlite(conn) -> bool:
    return isinstance(getattr(conn, "_con", conn), sqlite3.Connection)

# Dialekterkennung und -Normalisierung nur für SQLite
def _is_sqlite_cursor(cur) -> bool:
    try:
        return cur.__class__.__module__.split('.', 1)[0] == 'sqlite3'
    except Exception:
        return False

def _normalize_sql_for_sqlite(sql: str) -> str:
    # Entfernt Postgres-Details
    sql = re.sub(r"::[A-Za-z_][A-Za-z0-9_]*", "", sql)  # ::int, ::numeric, ::text ...
    sql = sql.replace(" ILIKE ", " LIKE ")
    sql = sql.replace("public.", "")
    return sql

# --- Wrappers ------------------------------------------------------------
class CursorWrapper:
    def __init__(self, cur, is_sqlite: bool):
        self._cur = cur
        self._is_sqlite = is_sqlite

    def execute(self, sql, params=None):
        if _is_sqlite_cursor(self._cur):
            sql = _normalize_sql_for_sqlite(sql)
            if params is not None:
                sql = sql.replace("%s", "?")  # Platzhalter an SQLite anpassen
        return self._cur.execute(sql, params or ())


    def executemany(self, sql, seq_of_params):
        if _is_sqlite_cursor(self._cur):
            sql = _normalize_sql_for_sqlite(sql).replace("%s", "?")
        return self._cur.executemany(sql, seq_of_params or [])

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
def _sqlite_connect(path=None):
    db_path = str(local_db_path())
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return ConnectionWrapper(conn, is_sqlite=True)

def get_configured_url() -> str | None:
    """
    Lies config.json und gib die PostgreSQL-URL zurück.
    Unterstützt neue (db_backend/postgres_url) und alte Keys (use_remote/db_url).
    """
    cfg = _read_config() or {}
    # Neu
    if str(cfg.get("db_backend", "")).lower() == "postgres" and cfg.get("postgres_url"):
        return cfg.get("postgres_url")
    # Legacy
    if cfg.get("use_remote") and cfg.get("db_url"):
        return cfg.get("db_url")
    return None

def _try_postgres_connect(dsn):
    import psycopg2
    conn = psycopg2.connect(dsn, connect_timeout=8)
    return ConnectionWrapper(conn, is_sqlite=False)

def _open_sqlite():
    # Nutzt deine lokale App-DB unter ProgramData
    db_path = str(local_db_path())
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    return ConnectionWrapper(conn, is_sqlite=True)

def get_db():
    url = get_configured_url()
    if url:
        try:
            return _try_postgres_connect(url)
        except Exception:
            # Bei Fehler still auf SQLite zurückfallen
            return _open_sqlite()
    # Keine URL konfiguriert -> SQLite
    return _open_sqlite()

def get_local_db():
    """
    Erzwingt lokale SQLite, unabhängig von config/Remote.
    """
    return _sqlite_connect()

def get_local_db_path():
    return str(local_db_path())

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

def clear_business_database():
    """
    Löscht alle Daten aus der aktiven Business-DB (SQLite/PostgreSQL).
    - SQLite: DELETE aus allen Tabellen außer internen und 'users', reset AUTOINCREMENT.
    - PostgreSQL: TRUNCATE aller Tabellen im current_schema() RESTART IDENTITY CASCADE.
    """
    conn = get_db()
    try:
        if getattr(conn, "is_sqlite", False):
            with conn.cursor() as cur:
                cur.execute("PRAGMA foreign_keys=OFF")
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                rows = cur.fetchall()
                def _val(r): 
                    try: return r["name"]
                    except Exception: return r[0]
                tables = [str(_val(r)) for r in rows]
                # Sicherheits-Exclude: 'users' nicht leeren, falls versehentlich in derselben Datei
                tables = [t for t in tables if t.lower() != "users"]
                for t in tables:
                    cur.execute(f"DELETE FROM {t}")
                # Autoincrement zurücksetzen (falls vorhanden)
                try:
                    cur.execute("DELETE FROM sqlite_sequence")
                except Exception:
                    pass
                cur.execute("PRAGMA foreign_keys=ON")
            conn.commit()
        else:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type='BASE TABLE' AND table_schema = current_schema()
                """)
                rows = cur.fetchall()
                def _schema(r): 
                    try: return r["table_schema"]
                    except Exception: return r[0]
                def _name(r): 
                    try: return r["table_name"]
                    except Exception: return r[1]
                tbls = []
                for r in rows:
                    schema = _schema(r)
                    name = _name(r)
                    # 'users' vorsorglich ausnehmen
                    if name.lower() == "users":
                        continue
                    tbls.append(f'{schema}."{name}"')
                if tbls:
                    sql = "TRUNCATE TABLE " + ", ".join(tbls) + " RESTART IDENTITY CASCADE"
                    cur.execute(sql)
            conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def list_business_tables(exclude: Iterable[str] = ("users",)) -> List[str]:
    """
    Liefert alle 'Business'-Tabellen der aktiven DB (aktuelles Schema bei PG, alle User-Tabellen bei SQLite).
    'users' wird standardmäßig ausgeschlossen.
    """
    ex = {str(x).lower() for x in (exclude or [])}
    conn = get_db()
    try:
        names = []
        with conn.cursor() as cur:
            if getattr(conn, "is_sqlite", False):
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                rows = cur.fetchall()
                for r in rows:
                    name = (r["name"] if isinstance(r, dict) else r[0])
                    if str(name).lower() not in ex:
                        names.append(str(name))
            else:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = current_schema() AND table_type='BASE TABLE'
                """)
                rows = cur.fetchall()
                for r in rows:
                    name = (r["table_name"] if isinstance(r, dict) else r[0])
                    if str(name).lower() not in ex:
                        names.append(str(name))
        return sorted(names, key=lambda x: x.lower())
    finally:
        try: conn.close()
        except Exception: pass

def clear_selected_tables(tables: Iterable[str]) -> None:
    """
    Löscht Inhalte der angegebenen Tabellen.
    - SQLite: DELETE FROM "t"; sqlite_sequence für diese Tabellen zurücksetzen (falls vorhanden).
    - PostgreSQL: TRUNCATE schema."t" ... RESTART IDENTITY CASCADE im current_schema().
    """
    to_clear = [t for t in (tables or []) if t]
    if not to_clear:
        return
    conn = get_db()
    try:
        if getattr(conn, "is_sqlite", False):
            with conn.cursor() as cur:
                cur.execute("PRAGMA foreign_keys=OFF")
                for t in to_clear:
                    qt = '"' + str(t).replace('"', '""') + '"'
                    cur.execute(f"DELETE FROM {qt}")
                # ggf. Autoincrement zurücksetzen
                try:
                    for t in to_clear:
                        cur.execute("DELETE FROM sqlite_sequence WHERE name=%s", (t,))
                except Exception:
                    pass
                cur.execute("PRAGMA foreign_keys=ON")
            conn.commit()
        else:
            # aktuelles Schema ermitteln
            with conn.cursor() as cur:
                cur.execute("SELECT current_schema()")
                schema_row = cur.fetchone()
                schema = (schema_row[0] if isinstance(schema_row, tuple) else (schema_row.get(0) if isinstance(schema_row, dict) else None)) or "public"
                idents = [f'{schema}."{str(t).replace(chr(34), chr(34)*2)}"' for t in to_clear]
                sql = "TRUNCATE TABLE " + ", ".join(idents) + " RESTART IDENTITY CASCADE"
                cur.execute(sql)
            conn.commit()
    finally:
        try: conn.close()
        except Exception: pass

import json

# Helper für config.json (DB-Backend, postgres_url, etc.)
def get_config_value(key: str) -> str | None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_config_value(key: str, value: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# Helper für rechnung_layout.json
def get_rechnung_layout() -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT layout_data FROM rechnung_layout WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return json.loads(row[0]) if row and row[0] else {}

def set_rechnung_layout(data: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO rechnung_layout (id, layout_data) VALUES (1, ?)", (json.dumps(data),))
    conn.commit()
    conn.close()

# Helper für einstellungen.json
def get_einstellungen() -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT data FROM einstellungen WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return json.loads(row[0]) if row and row[0] else {}

def set_einstellungen(data: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO einstellungen (id, data) VALUES (1, ?)", (json.dumps(data),))
    conn.commit()
    conn.close()

# Helper für qr_daten.json
def get_qr_daten() -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT data FROM qr_daten WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return json.loads(row[0]) if row and row[0] else {}

def set_qr_daten(data: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO qr_daten (id, data) VALUES (1, ?)", (json.dumps(data),))
    conn.commit()
    conn.close()
