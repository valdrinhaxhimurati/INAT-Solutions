"""
auto_smoke_full.py
Comprehensive non-interactive smoke tests against an isolated temporary SQLite DB.
- Does NOT touch configured remote DBs.
- Creates a temporary SQLite file inside the repo (left for inspection).
- Uses project schema creation (`ensure_app_schema`) and then performs safe inserts/selects.
"""
import sys, os, uuid, tempfile, traceback
RUN_ID = str(uuid.uuid4())[:8]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(f"AUTO-SMOKE-FULL {RUN_ID}")
# ensure project imports work
sys.path.insert(0, ROOT)

import db_connection as dbconn

# create temp sqlite inside project to make it easy to find
tmpf = tempfile.NamedTemporaryFile(prefix=f"inat_smoke_full_{RUN_ID}_", suffix=".sqlite", delete=False, dir=ROOT)
tmp_path = tmpf.name
tmpf.close()
print("Temp DB:", tmp_path)

# connect and monkeypatch
conn = dbconn.connect_sqlite_at(tmp_path)
orig_get_db = getattr(dbconn, 'get_db', None)
dbconn.get_db = lambda: conn

summary = {"inserts": [], "errors": []}

try:
    # ensure schema
    try:
        dbconn.ensure_app_schema()
        print("Schema ensured")
    except Exception as e:
        print("ensure_app_schema failed:", e)
        summary["errors"].append(str(e))
    # ensure_app_schema closes the connection it used; reconnect to operate on the temp DB
    try:
        conn.close()
    except Exception:
        pass
    conn = dbconn.connect_sqlite_at(tmp_path)
    dbconn.get_db = lambda: conn

    def list_tables():
        c = conn.cursor()
        try:
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            rows = c.fetchall()
            return [r[0] if not isinstance(r, dict) else r.get('name') for r in rows]
        finally:
            try: c.close()
            except: pass

    def get_columns(table):
        c = conn.cursor()
        try:
            c.execute(f"PRAGMA table_info({table})")
            rows = c.fetchall()
            cols = []
            for r in rows:
                # row: (cid,name,type,notnull,dflt_value,pk)
                if isinstance(r, (list, tuple)):
                    cols.append(r[1])
                else:
                    try:
                        cols.append(r['name'])
                    except Exception:
                        pass
            return cols
        finally:
            try: c.close()
            except: pass

    tables = list_tables()
    print("Tables found:", tables)

    # Prepare test payloads (will be filtered to available columns)
    payloads = {
        'kunden': {'anrede': 'Herr', 'name': f'Test Kunde {RUN_ID}', 'firma': 'AutoSmoke', 'telefon': '+499000', 'email': f'smoke-{RUN_ID}@example.local', 'bemerkung': f'smoke-run:{RUN_ID}'},
        'lieferanten': {'name': f'Test Lieferant {RUN_ID}', 'firma': 'AutoSmoke', 'telefon': '+499001', 'email': f'smoke-supp-{RUN_ID}@example.local'},
        'artikellager': {'artikelnummer': f'SM-{RUN_ID}', 'bezeichnung': 'AutoSmoke Artikel', 'bestand': 3, 'lagerort': 'Lager A'},
        'dienstleistungen': {'name': f'Service {RUN_ID}', 'beschreibung': 'Testing', 'preis': 12.5},
        'reifenlager': {'kundennr': None, 'kunde_anzeige': 'Test Kunde', 'fahrzeug': 'VW', 'dimension': '205/55R16', 'typ': 'Sommer', 'lagerort': 'Regal1'},
        'invoices': {'filename': f'test-{RUN_ID}.pdf', 'content_type': 'application/pdf', 'size': 1234}
    }

    # Helper: safe insert using %s placeholders (wrapper should adapt for sqlite)
    def safe_insert(table, data):
        try:
            cols = get_columns(table)
            keys = [k for k in data.keys() if k in cols]
            if not keys:
                print(f"{table}: no matching columns for payload, skipping")
                return False
            vals = [data[k] for k in keys]
            ph = ", ".join(["%s"] * len(keys))
            sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({ph})"
            c = conn.cursor()
            try:
                c.execute(sql, tuple(vals))
                try:
                    conn.commit()
                except Exception:
                    pass
                print(f"Inserted into {table}: {keys}")
                summary['inserts'].append((table, keys))
                return True
            finally:
                try: c.close()
                except: pass
        except Exception as e:
            tb = traceback.format_exc()
            print(f"ERROR inserting into {table}: {e}\n{tb}")
            summary['errors'].append(f"{table}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    # Run inserts for known tables present
    for t, payload in payloads.items():
        if t in tables:
            safe_insert(t, payload)
        else:
            print(f"Table {t} not present, skipping")

    # Try selects to verify
    def try_select(table, where_clause=None, params=()):
        try:
            c = conn.cursor()
            q = f"SELECT * FROM {table}"
            if where_clause:
                q += " WHERE " + where_clause
            q += " LIMIT 5"
            c.execute(q, params)
            rows = c.fetchall()
            print(f"Select {table}: {len(rows)} rows (showing up to 5)")
            for r in rows:
                print(r)
            try: c.close()
            except: pass
        except Exception as e:
            print(f"Select failed for {table}: {e}")
            summary['errors'].append(f"select_{table}:{e}")

    # Check a few tables
    for t in ['kunden', 'lieferanten', 'artikellager', 'dienstleistungen', 'reifenlager', 'invoices']:
        if t in tables:
            # try to filter by smoke markers if present
            if 'bemerkung' in get_columns(t):
                try_select(t, "bemerkung=?", (f'smoke-run:{RUN_ID}',))
            elif 'email' in get_columns(t):
                try_select(t, "email=?", (f'smoke-{RUN_ID}@example.local',))
            else:
                try_select(t)

finally:
    # restore
    try:
        if orig_get_db is not None:
            dbconn.get_db = orig_get_db
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass

print('\nAUTO-SMOKE-FULL SUMMARY:')
print('Temp DB:', tmp_path)
print('Inserts:', summary.get('inserts'))
print('Errors:', summary.get('errors'))
print('NOTE: temp DB left in repository for inspection; delete if desired')
