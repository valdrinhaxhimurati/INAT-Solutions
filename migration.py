# -*- coding: utf-8 -*-
"""
SQLite-DB initialisieren/migrieren (App) und optionale CLI für SQLite -> PostgreSQL.
"""
import argparse, os, json, re, sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from paths import data_dir  # schreibt in %ProgramData%\INAT Solutions\data

# App-DB Pfad (beschreibbar für normale Nutzer)
DB_DIR = data_dir()
DB_PATH = DB_DIR / "app.sqlite"

# Heuristiken/Patterns für Datennormalisierung (PG-Migration)
DATE_COL_HINTS = {"datum", "date", "created_at", "updated_at", "geburtsdatum"}
BOOL_COL_HINTS = {"ist_aktiv", "active", "enabled", "visible"}
DATE_PATTERNS = [
    "%d.%m.%Y", "%d.%m.%y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d-%m-%Y", "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"
]
NUMERIC_LIKE = re.compile(r"^-?[\d\.]+(,\d+)?$")

# -------------------- App-DB (SQLite) --------------------

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def _init_schema(conn: sqlite3.Connection) -> None:
    # Basis-Schema; hier deine Tabellen ergänzen
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS schema_version (
      id INTEGER PRIMARY KEY CHECK (id=1),
      version INTEGER NOT NULL
    );
    INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 1);
    """)
    conn.commit()

def _apply_app_migrations(conn: sqlite3.Connection) -> None:
    # Platz für spätere Migrationen (CREATE/ALTER/INDEX ...)
    # Beispiel:
    # conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);")
    conn.commit()

def ensure_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not DB_PATH.exists()
    with _connect() as conn:
        if is_new:
            _init_schema(conn)
        _apply_app_migrations(conn)

def migration_ausfuehren(sqlite_path: str | None = None, pg_url: str | None = None) -> None:
    """
    App-Start: ohne Parameter aufrufen.
    - Erstellt/aktualisiert lokale SQLite-DB in ProgramData automatisch.
    Optional: Wenn pg_url gesetzt ist, migriert von SQLite nach PostgreSQL.
    """
    if not pg_url:
        ensure_database()
        return
    if not sqlite_path:
        sqlite_path = str(DB_PATH)
    migrate_sqlite_to_postgres(sqlite_path, pg_url)

# -------------------- Hilfen (für PG-Migration) --------------------

def read_config() -> Dict[str, Any]:
    # Sucht eine config.json im CWD oder im Modulverzeichnis
    candidates = [
        Path(os.getcwd()) / "config.json",
        Path(__file__).resolve().parent / "config.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

def list_sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    return [r[0] for r in cur.fetchall()]

def sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    return [r[1] for r in cur.fetchall()]

def normalize_value(table: str, col: str, val):
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        if col.lower() in DATE_COL_HINTS or re.match(r"^\d{1,2}\.\d{1,2}\.\d{2,4}", s) or re.match(r"^\d{4}-\d{2}-\d{2}", s):
            for fmt in DATE_PATTERNS:
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            return s
        if col.lower() in BOOL_COL_HINTS:
            sl = s.lower()
            if sl in {"true", "t", "ja", "yes", "y", "1"}:
                return True
            if sl in {"false", "f", "nein", "no", "n", "0"}:
                return False
        if NUMERIC_LIKE.match(s):
            s2 = s.replace(".", "").replace(",", ".")
            try:
                return int(s2) if re.match(r"^-?\d+$", s2) else float(s2)
            except ValueError:
                return s
        return s
    if isinstance(val, (int, float, bool)):
        return val
    return val

# -------------------- SQLite -> PostgreSQL --------------------

def migrate_sqlite_to_postgres(sqlite_path: str, pg_url: str) -> None:
    # Import nur hier (optional)
    try:
        import psycopg2
    except ImportError:
        raise SystemExit("psycopg2 fehlt: pip install psycopg2-binary")

    if not os.path.exists(sqlite_path):
        raise SystemExit(f"SQLite not found: {sqlite_path}")

    s = sqlite3.connect(sqlite_path)
    s.row_factory = sqlite3.Row

    pg = psycopg2.connect(pg_url)
    pg.autocommit = False

    def pg_columns(pgconn, table: str) -> list[str]:
        with pgconn.cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position
            """, (table,))
            return [r[0] for r in cur.fetchall()]

    def table_exists_pg(pgconn, table: str) -> bool:
        with pgconn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.tables
                  WHERE table_schema='public' AND table_name=%s
                )
            """, (table,))
            return cur.fetchone()[0]

    def set_serial_sequence(pgconn, table: str, pk_col: str) -> None:
        with pgconn.cursor() as cur:
            cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (table, pk_col))
            row = cur.fetchone()
            seqname = row[0] if row else None
            if not seqname:
                return
            cur.execute(f"SELECT COALESCE(MAX({pk_col}), 0) FROM {table}")
            mx = cur.fetchone()[0] or 0
            if mx < 1:
                cur.execute("SELECT setval(%s, %s, %s)", (seqname, 1, False))
            else:
                cur.execute("SELECT setval(%s, %s, %s)", (seqname, int(mx), True))

    try:
        tables = list_sqlite_tables(s)

        # Zieltabellen prüfen
        for t in tables:
            if not table_exists_pg(pg, t):
                raise SystemExit(f"Zieltabelle fehlt in PostgreSQL: {t} (Schema vorher anlegen)")

        # Daten übertragen
        for t in tables:
            s_cols = sqlite_columns(s, t)
            p_cols = pg_columns(pg, t)
            cols = [c for c in p_cols if c in s_cols]
            if not cols:
                print(f"[{t}] keine gemeinsamen Spalten, übersprungen")
                continue

            placeholders = ", ".join(["%s"] * len(cols))
            col_list = ", ".join(cols)
            if "id" in cols:
                updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols if c != "id"])
                ins = f"INSERT INTO {t} ({col_list}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {updates}"
            else:
                ins = f"INSERT INTO {t} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

            cur = s.cursor()
            cur.execute(f"SELECT {col_list} FROM {t}")
            rows = cur.fetchall()
            if not rows:
                print(f"[{t}] (keine Zeilen)")
                continue

            norm_rows = [tuple(normalize_value(t, c, r[c]) for c in cols) for r in rows]
            with pg.cursor() as curp:
                curp.executemany(ins, norm_rows)
            pg.commit()
            print(f"[{t}] eingefügt: {len(rows)}")

        # Sequenzen korrigieren
        for t in tables:
            p_cols = pg_columns(pg, t)
            if "id" in p_cols:
                set_serial_sequence(pg, t, "id")

        print("Migration abgeschlossen.")
    except Exception:
        pg.rollback()
        raise
    finally:
        try: s.close()
        except: pass
        try: pg.close()
        except: pass

# -------------------- CLI --------------------

def main():
    ap = argparse.ArgumentParser(description="SQLite -> PostgreSQL Migration (optional)")
    ap.add_argument("--sqlite", required=True, help="Pfad zur SQLite-Datei")
    ap.add_argument("--pg", required=False, help="PostgreSQL-URL (postgres://user:pass@host/db)")
    args = ap.parse_args()

    cfg = read_config()
    pg_url = args.pg or cfg.get("postgres_url")
    if not pg_url:
        raise SystemExit("Keine PostgreSQL-URL. --pg nutzen oder postgres_url in config.json setzen.")
    migrate_sqlite_to_postgres(args.sqlite, pg_url)

if __name__ == "__main__":
    main()

