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
def get_config_value(key, default=None):
    conn = get_db()
    try:
        cur = conn.cursor()
        # use %s placeholder so the project's SQL-adapter/wrapper kann es für SQLite anpassen
        cur.execute("SELECT value FROM config WHERE key = %s", (key,))
        row = cur.fetchone()
        if row:
            return row[0]
        return default
    finally:
        try:
            conn.close()
        except Exception:
            pass

def set_config_value(key, value):
    conn = get_db()
    try:
        cur = conn.cursor()
        # erkennen, ob es sich um eine SQLite-Verbindung handelt
        is_sqlite = getattr(conn, "is_sqlite", False) or "sqlite" in conn.__class__.__module__.lower()
        if is_sqlite:
            # Wrapper erwartet %s - wird intern zu ? konvertiert
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES (%s, %s)", (key, value))
        else:
            # Postgres: ON CONFLICT verwenden
            cur.execute(
                "INSERT INTO config (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, value)
            )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

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
    cur.execute("INSERT OR REPLACE INTO rechnung_layout (id, layout_data) VALUES (1, %s)", (json.dumps(data),))
    conn.commit()
    conn.close()

# Helper für einstellungen.json
def get_einstellungen(id=1):
    """
    Liefert Einstellungen als dict.
    Versucht DB (SELECT data FROM einstellungen WHERE id=%s), fällt bei Fehlern / fehlender Tabelle
    auf config/einstellungen.json oder leeres dict zurück.
    """
    # 1) Versuch DB
    try:
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT data FROM einstellungen WHERE id = %s", (id,))
            row = cur.fetchone()
            if row and row[0]:
                # falls jsonb in DB, row[0] ist bereits dict
                data = row[0]
                try:
                    # sicherstellen, dass dict zurückkommt
                    return dict(data) if isinstance(data, dict) else json.loads(data)
                except Exception:
                    return data
        except Exception:
            # Tabelle fehlt oder andere DB-Fehler -> fallback unten
            pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        # kein DB-Zugriff möglich -> fallback
        pass

    # 2) Fallback auf Datei config/einstellungen.json (falls vorhanden)
    cfg_path = os.path.join(os.path.dirname(__file__), "config", "einstellungen.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    # 3) letzter Fallback: leeres dict
    return {}

def set_einstellungen(data: dict):
    conn = get_db()
    try:
        cur = conn.cursor()
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False) or ("sqlite" in conn.__class__.__module__.lower())
        payload = json.dumps(data)
        if is_sqlite:
            # Wrapper wandelt %s -> ? für SQLite
            cur.execute("INSERT OR REPLACE INTO einstellungen (id, data) VALUES (1, %s)", (payload,))
        else:
            cur.execute(
                "INSERT INTO public.einstellungen (id, data) VALUES (1, %s) "
                "ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
                (payload,)
            )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def set_rechnung_layout(data: dict):
    conn = get_db()
    try:
        cur = conn.cursor()
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False) or ("sqlite" in conn.__class__.__module__.lower())
        payload = json.dumps(data)
        if is_sqlite:
            cur.execute("INSERT OR REPLACE INTO rechnung_layout (id, layout_data) VALUES (1, %s)", (payload,))
        else:
            cur.execute(
                "INSERT INTO public.rechnung_layout (id, layout_data) VALUES (1, %s) "
                "ON CONFLICT (id) DO UPDATE SET layout_data = EXCLUDED.layout_data",
                (payload,)
            )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def set_qr_daten(data: dict):
    conn = get_db()
    try:
        cur = conn.cursor()
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False) or ("sqlite" in conn.__class__.__module__.lower())
        payload = json.dumps(data)
        if is_sqlite:
            cur.execute("INSERT OR REPLACE INTO qr_daten (id, data) VALUES (1, %s)", (payload,))
        else:
            cur.execute(
                "INSERT INTO public.qr_daten (id, data) VALUES (1, %s) "
                "ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
                (payload,)
            )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def ensure_app_schema():
    """
    Idempotent: legt Kern‑Tabellen an. Für SQLite werden Postgres‑Typen
    normalisiert, damit sqlite_master keine BIGSERIAL-Literale behält.
    """
    schema = {
        "config": [
            ("key", "TEXT PRIMARY KEY"),
            ("value", "TEXT")
        ],
        "buchhaltung": [
            ("id", "BIGSERIAL PRIMARY KEY"),
            ("datum", "TIMESTAMP"),
            ("typ", "TEXT"),
            ("kategorie", "TEXT"),
            ("betrag", "NUMERIC"),
            ("beschreibung", "TEXT")
        ],
        "lieferanten": [
            ("id", "BIGSERIAL PRIMARY KEY"),
            ("lieferantnr", "INTEGER"),
            ("name", "TEXT"),
            ("firma", "TEXT"),
            ("strasse", "TEXT"),
            ("plz", "TEXT"),
            ("stadt", "TEXT"),
            ("telefon", "TEXT"),
            ("email", "TEXT"),
            ("kommentare", "TEXT"),
            ("portal_link", "TEXT"),
            ("login", "TEXT"),
            ("passwort", "TEXT"),
        ],
        "kunden": [
            ("id", "BIGSERIAL PRIMARY KEY"),
            ("kundennr", "BIGINT"),
            ("anrede", "TEXT"),
            ("name", "TEXT"),
            ("firma", "TEXT"),
            ("strasse", "TEXT"),
            ("plz", "TEXT"),
            ("stadt", "TEXT"),
            ("telefon", "TEXT"),
            ("email", "TEXT"),
            ("bemerkung", "TEXT")
        ],
        "artikellager": [
            ("artikel_id", "BIGSERIAL PRIMARY KEY"),
            ("artikelnummer", "TEXT"),
            ("bezeichnung", "TEXT"),
            ("bestand", "INTEGER"),
            ("lagerort", "TEXT")
        ],
        "reifenlager": [
            ("reifen_id", "BIGSERIAL PRIMARY KEY"),
            ("kundennr", "INTEGER"),
            ("kunde_anzeige", "TEXT"),
            ("fahrzeug", "TEXT"),
            ("dimension", "TEXT"),
            ("typ", "TEXT"),
            ("dot", "TEXT"),
            ("lagerort", "TEXT"),
            ("eingelagert_am", "TEXT"),
            ("ausgelagert_am", "TEXT"),
            ("bemerkung", "TEXT")
        ],
        "rechnung_layout": [
            ("id", "BIGSERIAL PRIMARY KEY"),
            ("name", "TEXT"),
            ("layout_data", "TEXT"),
            ("layout", "JSONB"),
            ("kopfzeile", "TEXT"),
            ("einleitung", "TEXT"),
            ("fusszeile", "TEXT"),
            ("logo", "BYTEA"),
            ("logo_mime", "TEXT"),
            ("logo_skala", "REAL"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ],
        "materiallager": [
            ("material_id", "BIGSERIAL PRIMARY KEY"),
            ("materialnummer", "TEXT"),
            ("bezeichnung", "TEXT"),
            ("menge", "INTEGER"),
            ("einheit", "TEXT"),
            ("lagerort", "TEXT"),
            ("lieferantnr", "INTEGER"),
            ("bemerkung", "TEXT")
        ],
        # Einstellungen (App-Settings) — wichtig für get_einstellungen / set_einstellungen
        "einstellungen": [
            ("id", "BIGSERIAL PRIMARY KEY"),
            ("data", "JSONB")
        ],
        "qr_daten": [
            ("id", "BIGSERIAL PRIMARY KEY"),
            ("data", "JSONB")
        ],
    }

    conn = get_db()
    try:
        is_sqlite = getattr(conn, "is_sqlite", False)

        for table, cols in schema.items():
            # build SQL appropriate for backend
            if is_sqlite:
                col_defs = []
                for name, typ in cols:
                    t = typ
                    # convert PK bigserial -> sqlite integer autoincrement
                    if "PRIMARY KEY" in t and "BIGSERIAL" in t:
                        t = "INTEGER PRIMARY KEY AUTOINCREMENT"
                    else:
                        t = t.replace("BIGSERIAL", "INTEGER").replace("SERIAL", "INTEGER") \
                             .replace("BYTEA", "BLOB").replace("JSONB", "TEXT")
                    col_defs.append(f"{name} {t}")
                create_sql = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(col_defs)})"
            else:
                col_defs = [f"{name} {typ}" for name, typ in cols]
                create_sql = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(col_defs)})"

            try:
                with conn.cursor() as cur:
                    cur.execute(create_sql)
            except Exception:
                # defensive: ignore/create attempts failing due to subtle sqlite versions
                try:
                    conn.rollback()
                except Exception:
                    pass

        # ensure missing columns added (ALTER TABLE ADD COLUMN)
        with conn.cursor() as cur:
            if is_sqlite:
                for table, cols in schema.items():
                    try:
                        cur.execute(f"PRAGMA table_info({table})")
                        existing = [r[1] for r in cur.fetchall()]
                    except Exception:
                        existing = []
                    for name, typ in cols:
                        if name not in existing:
                            t = typ.replace("BIGSERIAL", "INTEGER").replace("SERIAL", "INTEGER") \
                                   .replace("BYTEA", "BLOB").replace("JSONB", "TEXT")
                            try:
                                cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {t}")
                            except Exception:
                                pass
                # optional: fill kundennr from rowid if missing
                try:
                    cur.execute("UPDATE kunden SET kundennr = COALESCE(kundennr, rowid) WHERE kundennr IS NULL")
                except Exception:
                    pass
            else:
                for table, cols in schema.items():
                    for name, typ in cols:
                        try:
                            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {typ}")
                        except Exception:
                            pass
                # Postgres sequences fallback
                try:
                    cur.execute("CREATE SEQUENCE IF NOT EXISTS kunden_kundennr_seq")
                    cur.execute("ALTER TABLE kunden ALTER COLUMN kundennr SET DEFAULT nextval('kunden_kundennr_seq')")
                    cur.execute("UPDATE kunden SET kundennr = nextval('kunden_kundennr_seq') WHERE kundennr IS NULL")
                except Exception:
                    pass

        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

# keep existing helper name for backward compatibility
def ensure_database_and_tables():
    ensure_app_schema()

def get_qr_daten():
    """
    Liefert QR-Daten als dict.
    Versucht DB (SELECT data FROM qr_daten WHERE id=1), fällt bei Fehlern auf config/qr_daten.json zurück.
    """
    # 1) Versuch DB
    try:
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT data FROM qr_daten WHERE id = %s", (1,))
            row = cur.fetchone()
            if row and row[0]:
                data = row[0]
                try:
                    return dict(data) if isinstance(data, dict) else json.loads(data)
                except Exception:
                    return data
        except Exception:
            pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass

    # 2) Fallback auf Datei config/qr_daten.json
    cfg_path = os.path.join(os.path.dirname(__file__), "config", "qr_daten.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    # 3) letzter Fallback: leeres dict
    return {}

