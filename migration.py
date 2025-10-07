# -*- coding: utf-8 -*-
"""
SQLite -> PostgreSQL Migration (robust, mit Normalisierung)
- Spalten-Schnittmenge je Tabelle
- Datum/Zahl/Bool werden vor dem Insert normalisiert
"""
import argparse, os, json, sqlite3, re
from datetime import datetime

try:
    import psycopg2
except Exception:
    raise SystemExit("psycopg2 fehlt. Bitte: pip install psycopg2-binary")

# ---- Helpers ----------------------------------------------------------------
DATE_COL_HINTS = {"datum", "faellig_am", "created_at", "updated_at", "date"}
BOOL_COL_HINTS = {"bezahlt", "active", "ist_bezahlt"}
NUMERIC_LIKE = re.compile(r"^\s*-?\d{1,3}(\.\d{3})*(,\d+)?\s*$")  # "1.234,56" oder "123,45" oder "1.234"
DATE_PATTERNS = [
    "%d.%m.%Y",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%y",
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
]

def read_config():
    for p in [os.path.join(os.getcwd(),"config.json"), os.path.join(os.path.dirname(__file__),"config.json")]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

def list_sqlite_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    return [r[0] for r in cur.fetchall()]

def sqlite_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    return [r[1] for r in cur.fetchall()]

def pg_columns(pg, table):
    with pg.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
        """, (table,))
        return [r[0] for r in cur.fetchall()]

def table_exists_pg(pg, table):
    with pg.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema='public' AND table_name=%s
            )
        """, (table,))
        return cur.fetchone()[0]

def set_serial_sequence(pgconn, table: str, pk_col: str):
    """SERIAL/IDENTITY-Sequence korrekt setzen:
       - Wenn Tabelle leer: setval(seq, 1, false)  -> nächster nextval() gibt 1
       - Sonst: setval(seq, max_id, true)          -> nächster nextval() gibt max_id+1
    """
    with pgconn.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (table, pk_col))
        row = cur.fetchone()
        seqname = row[0] if row else None
        if not seqname:
            return  # keine Sequenz (z.B. kein SERIAL/IDENTITY)
        cur.execute(f"SELECT COALESCE(MAX({pk_col}), 0) FROM {table}")
        mx = cur.fetchone()[0] or 0
        if mx < 1:
            # leer -> auf 1 setzen, is_called = False
            cur.execute("SELECT setval(%s, %s, %s)", (seqname, 1, False))
        else:
            # gefüllt -> auf max setzen, is_called = True
            cur.execute("SELECT setval(%s, %s, %s)", (seqname, int(mx), True))


def normalize_value(table, col, val):
    if val is None:
        return None
    # String?
    if isinstance(val, str):
        s = val.strip()

        # Datum erkennen/konvertieren (bei typischen Spaltennamen oder wenn es wie Datum aussieht)
        if col.lower() in DATE_COL_HINTS or re.match(r"^\d{1,2}\.\d{1,2}\.\d{2,4}", s) or re.match(r"^\d{4}-\d{2}-\d{2}", s):
            for fmt in DATE_PATTERNS:
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.strftime("%Y-%m-%d")  # ISO-Datum
                except ValueError:
                    pass
            # Wenn nicht parsebar: roh zurückgeben (Postgres entscheidet)
            return s

        # Bool
        if col.lower() in BOOL_COL_HINTS:
            if s.lower() in {"true", "t", "ja", "yes", "y", "1"}:
                return True
            if s.lower() in {"false", "f", "nein", "no", "n", "0"}:
                return False

        # Numerik mit deutschem Format "1.234,56"
        if NUMERIC_LIKE.match(s):
            s2 = s.replace(".", "").replace(",", ".")
            try:
                # Wenn es wie eine Ganzzahl aussieht, int; sonst float
                return int(s2) if re.match(r"^-?\d+$", s2) else float(s2)
            except ValueError:
                return s2  # als String

        return s

    # SQLite bool/int/float direkt durchlassen
    if isinstance(val, (int, float, bool)):
        return val

    return val

# ---- Migration --------------------------------------------------------------
def migrate(sqlite_path, pg_url):
    if not os.path.exists(sqlite_path):
        raise SystemExit(f"SQLite not found: {sqlite_path}")

    s = sqlite3.connect(sqlite_path)
    s.row_factory = sqlite3.Row

    pg = psycopg2.connect(pg_url)
    pg.autocommit = False

    try:
        tables = list_sqlite_tables(s)
        for t in tables:
            if not table_exists_pg(pg, t):
                raise SystemExit(f"Target table missing in PostgreSQL: {t}. Run schema first.")

        for t in tables:
            s_cols = sqlite_columns(s, t)
            p_cols = pg_columns(pg, t)
            cols = [c for c in p_cols if c in s_cols]   # Schnittmenge in PG-Reihenfolge
            if not cols:
                print(f"[{t}] no common columns, skipping")
                continue

            print(f"-> {t} ({len(cols)} columns)")
            placeholders = ", ".join(["%s"]*len(cols))
            col_list = ", ".join(cols)
            # Wenn 'id' Spalte vorhanden, Konflikte auf id ignorieren (erneuter Lauf = keine Duplikate)
            if "id" in cols:
                updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols if c != "id"])
                ins = f"INSERT INTO {t} ({col_list}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {updates}"
            else:
                ins = f"INSERT INTO {t} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"


            cur = s.cursor()
            cur.execute(f"SELECT {col_list} FROM {t}")
            rows = cur.fetchall()
            if not rows:
                print("   (no rows)")
                continue

            # Vor dem Insert Werte normalisieren
            norm_rows = []
            for r in rows:
                norm_rows.append(tuple(normalize_value(t, c, r[c]) for c in cols))

            with pg.cursor() as curp:
                curp.executemany(ins, norm_rows)
            pg.commit()
            print(f"   inserted: {len(rows)}")

        # Sequenzen auf MAX(id) setzen
        for t in tables:
            p_cols = pg_columns(pg, t)
            if "id" in p_cols:
                set_serial_sequence(pg, t, "id")

        # rechnr_seq auf MAX(rechnungsnummer)+1
        with pg.cursor() as curp:
            curp.execute("""
                SELECT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='rechnungen' AND column_name='rechnungsnummer')
            """)
            if curp.fetchone()[0]:
                curp.execute("SELECT COALESCE(MAX(rechnungsnummer), 9999) FROM rechnungen")
                mx = curp.fetchone()[0] or 9999
                curp.execute("SELECT setval('rechnr_seq', %s, true)", (int(mx)+1,))
        pg.commit()
        print("\nDone.")
    except Exception:
        pg.rollback()
        raise
    finally:
        try: s.close()
        except: pass
        try: pg.close()
        except: pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True)
    ap.add_argument("--pg", required=False)
    args = ap.parse_args()
    cfg = read_config()
    pg_url = args.pg or cfg.get("postgres_url")
    if not pg_url:
        raise SystemExit("No PG URL provided. Use --pg or set postgres_url in config.json")
    migrate(args.sqlite, pg_url)

def migration_ausfuehren(sqlite_path="db/datenbank.sqlite", pg_url=None):
    """Kompatibilität für main.py"""
    if not pg_url:
        cfg = read_config()
        pg_url = cfg.get("postgres_url")
    if not pg_url:
        raise SystemExit("Keine PostgreSQL-URL in config.json")
    migrate(sqlite_path, pg_url)


if __name__ == "__main__":
    main()
