# auto_smoke.py
# Non-interactive smoke tests for core DB operations (safe, idempotent-ish)
import uuid
import time
import os
import tempfile
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import db_connection as dbconn

RUN_ID = str(uuid.uuid4())[:8]
print(f"SMOKE RUN {RUN_ID}")

# Create an isolated temporary SQLite DB for the smoke run to avoid touching remote DBs
tmpf = tempfile.NamedTemporaryFile(prefix="inat_smoke_", suffix=".sqlite", delete=False, dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
tmp_path = tmpf.name
tmpf.close()
print("Using temp sqlite:", tmp_path)

# Connect to that sqlite and monkeypatch db_connection.get_db to return it
conn = dbconn.connect_sqlite_at(tmp_path)
orig_get_db = getattr(dbconn, 'get_db', None)
dbconn.get_db = lambda: conn

try:
    # ensure schema is created in the temp DB
    try:
        dbconn.ensure_app_schema()
    except Exception as e:
        print("ensure_app_schema failed:", e)

    try:
        from db_connection import list_business_tables
    except Exception:
        def list_business_tables():
            return []

        with conn.cursor() as cur:
            try:
                tables = list_business_tables()
            except Exception:
                tables = []
            print("Tables:", tables)

        def get_columns(table):
            try:
                # try PG information_schema
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = %s ORDER BY ordinal_position", (table,))
                rows = cur.fetchall()
                if rows:
                    return [r[0] if not isinstance(r, dict) else r['column_name'] for r in rows]
            except Exception:
                pass
            try:
                # fallback: sqlite pragma
                cur.execute(f"PRAGMA table_info({table})")
                rows = cur.fetchall()
                return [r[1] if isinstance(r, (list, tuple)) else (r['name'] if isinstance(r, dict) else r[0]) for r in rows]
            except Exception:
                return []

        for t in tables[:10]:
            cols = get_columns(t)
            print(f"Table {t}: cols={cols}")

        # Safe inserts: try for kunden or lieferanten or artikellager
        def try_insert(table, data: dict):
            print(f"Trying insert into {table}: {data}")
            cols = get_columns(table)
            keys = [k for k in data.keys() if k in cols]
            if not keys:
                print(f" -> No matching cols for {table}, skipping")
                return
            vals = [data[k] for k in keys]
            ph = ", ".join(["%s"]*len(keys))
            col_list = ", ".join(keys)
            sql = f"INSERT INTO {table} ({col_list}) VALUES ({ph})"
            try:
                cur.execute(sql, tuple(vals))
                conn.commit()
                print(" -> insert OK")
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                print(" -> insert FAILED:", e)

        test_data = {
            'kunden': {
                'name': f'Test Kunde {RUN_ID}',
                'firma': 'AutoSmoke',
                'telefon': '+499000',
                'email': f'smoke-{RUN_ID}@example.local',
                'bemerkung': f'smoke-run:{RUN_ID}'
            },
            'lieferanten': {
                'name': f'Test Lieferant {RUN_ID}',
                'firma': 'AutoSmoke',
                'telefon': '+499001',
                'email': f'smoke-supp-{RUN_ID}@example.local',
            },
            'artikellager': {
                'artikelnummer': f'SM-{RUN_ID}',
                'bezeichnung': 'AutoSmoke Artikel',
                'bestand': 5
            }
        }

        for table, data in test_data.items():
            if table in tables:
                try_insert(table, data)

        # Try select back the recently inserted kunden by bemerknung or email
        try:
            if 'kunden' in tables:
                cur.execute("SELECT * FROM kunden WHERE bemerkung = ? OR email = ? ORDER BY rowid DESC LIMIT 5", (f'smoke-run:{RUN_ID}', f'smoke-{RUN_ID}@example.local'))
                rows = cur.fetchall()
                print('Found kunden rows:', rows[:5])
        except Exception as e:
            print('Select kunden failed:', e)

finally:
    try:
        # restore original get_db
        if orig_get_db is not None:
            dbconn.get_db = orig_get_db
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
    # keep tempfile for inspection, but print location so user can remove it

print('SMOKE DONE — temp DB left at: ', tmp_path)
