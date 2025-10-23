import sys, os
# ensure repo root is on sys.path so imports like "import db_connection" work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test DB connection + schema + simple insert (works für SQLite und Postgres via get_db())
import traceback
from db_connection import get_db, get_configured_url, ensure_app_schema

print("Using DB:", get_configured_url())

ensure_app_schema()
print("ensure_app_schema OK")

conn = get_db()
print("is_sqlite:", conn.is_sqlite)

test_row_id = None
try:
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT 1")
            try:
                print("SELECT 1 ->", cur.fetchone())
            except Exception:
                print("SELECT 1 executed")
        except Exception:
            pass

        if conn.is_sqlite:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        else:
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        print("tables:", [r[0] for r in cur.fetchall()])

        if conn.is_sqlite:
            cur.execute("PRAGMA table_info(kunden)")
            print("kunden pragma:", cur.fetchall())
        else:
            cur.execute("SELECT column_name, column_default FROM information_schema.columns WHERE table_name='kunden' ORDER BY ordinal_position")
            print("kunden cols:", cur.fetchall())

        params = ("__TEST__", "FirmaTest", "0000", "Musterstr", "Ort", "+491234", "Herr", "test@example.local")
        if conn.is_sqlite:
            sql = "INSERT INTO kunden (name,firma,plz,strasse,stadt,telefon,anrede,email) VALUES (?,?,?,?,?,?,?,?)"
            cur.execute(sql, params)
            test_row_id = getattr(cur, "lastrowid", None)
            print("sqlite inserted id (lastrowid):", test_row_id)
            cur.execute("SELECT id,kundennr,name,telefon,anrede,email FROM kunden WHERE id=?", (test_row_id,))
            print("inserted row:", cur.fetchone())
        else:
            sql = "INSERT INTO kunden (name,firma,plz,strasse,stadt,telefon,anrede,email) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id,kundennr"
            cur.execute(sql, params)
            row = cur.fetchone()
            print("postgres returned:", row)
            if row:
                test_row_id = row[0]

    try:
        conn.commit()
    except Exception:
        pass

    print("Test insert done; cleanup follows")

    if test_row_id:
        with conn.cursor() as cur:
            if conn.is_sqlite:
                cur.execute("DELETE FROM kunden WHERE id=?", (test_row_id,))
            else:
                cur.execute("DELETE FROM kunden WHERE id=%s", (test_row_id,))
        try:
            conn.commit()
        except Exception:
            pass
        print("Cleanup done (deleted test row id):", test_row_id)
    else:
        print("No test row id found; nothing to delete.")

except Exception:
    traceback.print_exc()
finally:
    try:
        conn.close()
    except Exception:
        pass