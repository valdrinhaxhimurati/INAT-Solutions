import csv
import sqlite3
import json
import argparse
import datetime
import pathlib

# Konfiguration: falls Tabelle anders heißt, anpassen
RECHNUNGEN_TABLE = "rechnungen"
POS_TABLE = "rechnung_positionen"  # passe an das echte Ziel an, z.B. "invoice_items"
# Spalten der Positions-Tabelle (wird bei Bedarf erzeugt)
POS_SCHEMA = """
CREATE TABLE IF NOT EXISTS {pos_table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rechnung_id INTEGER,
    position_index INTEGER,
    bezeichnung TEXT,
    menge REAL,
    preis REAL,
    mwst REAL,
    gesamt REAL
);
"""

def norm_date(s):
    if s is None: return None
    s = str(s).strip()
    if not s: return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def fix_positions_field(val):
    if val is None:
        return []
    v = val
    if isinstance(v, bytes):
        v = v.decode("utf-8", errors="ignore")
    v = v.strip()
    if not v:
        return []
    # Normalize doubled quotes
    if '""' in v and v.count('""') >= 2:
        v = v.replace('""', '"')
    # If the field is stored as a quoted JSON string e.g. '"[...]"', strip outer quotes
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    try:
        parsed = json.loads(v)
        if isinstance(parsed, dict):
            # sometimes a dict with numeric keys -> convert to list
            parsed = list(parsed.values())
        if not isinstance(parsed, list):
            return []
        return parsed
    except Exception:
        # try to fix common issues, replace single quotes with double
        try:
            tmp = v.replace("'", '"')
            parsed = json.loads(tmp)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    # fallback: try to split lines into simple positions
    lines = [l.strip() for l in v.splitlines() if l.strip()]
    out = []
    for i, L in enumerate(lines):
        out.append({"bezeichnung": L, "menge": 1, "preis": None, "mwst": None})
    return out

def ensure_positions_table(conn):
    conn.execute(POS_SCHEMA.format(pos_table=POS_TABLE))
    conn.commit()

def ensure_positionen_column(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info('rechnungen')").fetchall()]
    if "positionen" not in cols:
        conn.execute("ALTER TABLE rechnungen ADD COLUMN positionen TEXT")
        conn.commit()

def insert_positions(conn, rechnung_id, positions):
    cur = conn.cursor()
    sql = f'INSERT INTO {POS_TABLE} (rechnung_id, position_index, bezeichnung, menge, preis, mwst, gesamt) VALUES (?,?,?,?,?,?,?)'
    toins = []
    for idx, p in enumerate(positions):
        # akzeptiere verschiedene Feldnamen (CSV nutzt "beschreibung", "einzelpreis", "total")
        desc = p.get("beschreibung") or p.get("bezeichnung") or p.get("desc") or p.get("description") or ""
        menge = p.get("menge") or p.get("qty") or p.get("quantity") or p.get("amount") or None
        preis = p.get("preis") or p.get("einzelpreis") or p.get("price") or p.get("unit_price") or None
        mwst = p.get("mwst") or p.get("tax") or None
        gesamt = p.get("gesamt") or p.get("total") or None
        try:
            menge = float(menge) if menge not in (None, "") else None
        except Exception:
            menge = None
        try:
            preis = float(preis) if preis not in (None, "") else None
        except Exception:
            preis = None
        try:
            mwst = float(mwst) if mwst not in (None, "") else None
        except Exception:
            mwst = None
        try:
            gesamt = float(gesamt) if gesamt not in (None, "") else None
        except Exception:
            gesamt = None
        toins.append((rechnung_id, idx, desc, menge, preis, mwst, gesamt))
    if toins:
        cur.executemany(sql, toins)
        conn.commit()

def _parse_mwst(raw):
    if raw is None: 
        return 0.0
    s = str(raw).strip()
    if s == "" or s.lower() == "none":
        return 0.0
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def import_rechnungen_with_positions(db_path, csv_path, replace_positions=False):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_positions_table(conn)
    ensure_positionen_column(conn)
    inserted = 0
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        cols = [c for c in reader.fieldnames if c != "positionen"]
        cur = conn.cursor()
        try:
            conn.execute("BEGIN")
            for r in reader:
                # normalize mwst if present in CSV fields or ensure default
                if "mwst" in r:
                    r["mwst"] = _parse_mwst(r.get("mwst"))
                # prepare values (replace empty string with None except for numeric mwst which is already set)
                vals = []
                for c in cols:
                    v = r.get(c)
                    if c == "mwst":
                        vals.append(r.get("mwst", 0.0))
                    else:
                        vals.append((v or None) if (v != "") else None)
                # check existing by id or rechnung_nr/uid (same logic as before)
                csv_id = None
                if "id" in cols:
                    try:
                        csv_id = int(r.get("id")) if r.get("id") and str(r.get("id")).strip().isdigit() else None
                    except Exception:
                        csv_id = None
                rechnung_nr = r.get("rechnung_nr") or r.get("uid") or None
                existing_id = None
                if csv_id is not None:
                    row = cur.execute("SELECT id FROM rechnungen WHERE id = ?", (csv_id,)).fetchone()
                    if row:
                        existing_id = row["id"]
                if existing_id is None and rechnung_nr is not None:
                    row = cur.execute("SELECT id FROM rechnungen WHERE rechnung_nr = ? OR uid = ? LIMIT 1", (rechnung_nr, rechnung_nr)).fetchone()
                    if row:
                        existing_id = row["id"]
                if existing_id is not None:
                    target_id = existing_id
                else:
                    placeholders = ",".join(["?"] * len(cols))
                    sql = f'INSERT INTO rechnungen ({",".join(cols)}) VALUES ({placeholders})'
                    cur.execute(sql, vals)
                    target_id = cur.lastrowid if cur.lastrowid and cur.lastrowid != 0 else (csv_id or None)
                    inserted += 1
                positions = fix_positions_field(r.get("positionen"))
                if positions and target_id is not None:
                    # optional: entferne vorherige Positionen für diese Rechnung (vermeidet Duplikate)
                    if replace_positions:
                        cur.execute(f"DELETE FROM {POS_TABLE} WHERE rechnung_id = ?", (target_id,))
                    insert_positions(conn, target_id, positions)
                    # schreibe original/normalisierte Positionen auch in rechnungen.positionen (JSON)
                    try:
                        cur.execute("UPDATE rechnungen SET positionen = ? WHERE id = ?", (json.dumps(positions, ensure_ascii=False), target_id))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        conn.close()
                        raise
            conn.commit()
        except Exception:
            conn.rollback()
            conn.close()
            raise
    conn.close()
    return inserted

def import_kunden(db_path, csv_path):
    import csv, sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    inserted = 0
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        # adapt columns to your schema; common fields used here
        cols = ["kundennr", "name", "plz", "strasse", "stadt", "email", "firma", "anrede"]
        placeholders = ",".join("?" for _ in cols)
        sql = f'INSERT INTO kunden ({",".join(cols)}) VALUES ({placeholders})'
        rows = []
        for r in reader:
            try:
                kundennr = int(r.get("kundennr")) if r.get("kundennr") else None
            except Exception:
                kundennr = None
            rows.append((
                kundennr,
                r.get("name") or None,
                r.get("plz") or None,
                r.get("strasse") or None,
                r.get("stadt") or None,
                r.get("email") or None,
                r.get("firma") or None,
                r.get("anrede") or None,
            ))
        try:
            conn.executemany(sql, rows)
            conn.commit()
            inserted = len(rows)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return inserted

def import_buchhaltung(db_path, csv_path):
    import csv, sqlite3, datetime
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    inserted = 0
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        cols = ["id", "datum", "typ", "kategorie", "betrag", "beschreibung"]
        placeholders = ",".join("?" for _ in cols)
        sql = f'INSERT INTO buchhaltung ({",".join(cols)}) VALUES ({placeholders})'
        rows = []
        for r in reader:
            try:
                _id = int(r.get("id")) if r.get("id") else None
            except Exception:
                _id = None
            datum = r.get("datum") or None
            try:
                betrag = float(r.get("betrag")) if r.get("betrag") not in (None,"") else None
            except Exception:
                betrag = None
            rows.append((_id, datum, r.get("typ") or None, r.get("kategorie") or None, betrag, r.get("beschreibung") or None))
        try:
            conn.executemany(sql, rows)
            conn.commit()
            inserted = len(rows)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return inserted

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ziel-SQLite DB (z.B. data.db)")
    ap.add_argument("--rechnungen", help="Pfad zu rechnungen.csv")
    ap.add_argument("--kunden", help="Pfad zu kunden.csv")
    ap.add_argument("--buchhaltung", help="Pfad zu buchhaltung.csv")
    ap.add_argument("--replace-positions", action="store_true", help="Vor dem Einfügen vorhandene Positionen für die Rechnung löschen")
    args = ap.parse_args()
    if args.rechnungen:
        print("Import rechnungen + positionen:", import_rechnungen_with_positions(args.db, args.rechnungen, replace_positions=args.replace_positions))
    if args.kunden:
        print("Import kunden:", import_kunden(args.db, args.kunden))
    if args.buchhaltung:
        print("Import buchhaltung:", import_buchhaltung(args.db, args.buchhaltung))

if __name__ == "__main__":
    main()