import sqlite3, os, sys, re, shutil, time, argparse, traceback

def resolve_db_path():
    # prefer INAT_DB_URL if set and is sqlite:///
    dsn = os.environ.get("INAT_DB_URL")
    if dsn and dsn.lower().startswith("sqlite:///"):
        path = dsn.split("sqlite:///",1)[1]
        return os.path.abspath(path)
    # default to ProgramData path with datenbank.sqlite
    prog = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    data_dir = os.path.join(prog, "INAT Solutions", "data")
    db_path = os.path.join(data_dir, "datenbank.sqlite")
    if os.path.exists(db_path):
        return db_path
    # fallback: repo-root datenbank.sqlite
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(repo_root, "datenbank.sqlite")

TARGET_TABLES = [
    "kunden",
    "rechnungen", "rechnung", "rechnung_layout",
    "lieferanten",
    "artikellager",
    "reifenlager",
    "buchhaltung"
]

def show_summary(db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
    table_defs = {name: (sql or "") for name, sql in cur.fetchall()}
    print("\nFound tables:", ", ".join(sorted(table_defs.keys())) or "(none)")

    print("\n-- Tables with SERIAL/BIGSERIAL in CREATE SQL --")
    found_serial = False
    for name, sql in table_defs.items():
        if re.search(r"\b(BIGSERIAL|SERIAL)\b", (sql or ""), re.IGNORECASE):
            print("  ", name)
            print("    SQL:", sql.strip())
            found_serial = True
    if not found_serial:
        print("  None found.")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
    seq_exists = cur.fetchone() is not None
    print("\nsqlite_sequence exists:", seq_exists)

    print("\n-- Table checks --")
    issues = []
    for t in TARGET_TABLES:
        if t not in table_defs:
            print(f"\n{t}: (NOT FOUND)")
            continue
        print(f"\n{t}:")
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        if not cols:
            print("  PRAGMA returned no columns")
            continue
        for r in cols:
            cid, name, ctype, notnull, dflt, pk = r
            print(f"  col: {name:15} type: {str(ctype):15} pk:{pk} notnull:{notnull} default:{dflt}")
        idcol = None
        for r in cols:
            if r[1].lower() in ("id", "artikel_id", "reifen_id"):
                idcol = r
                break
        if not idcol:
            print("  -> WARNING: no id/PK column named id/artikel_id/reifen_id found")
            issues.append((t, "no_id"))
        else:
            _, idname, idtype, _, _, idpk = idcol
            is_int_pk = (idpk == 1) and (str(idtype or "").upper().startswith("INTEGER"))
            print(f"  -> id column: {idname} type={idtype} pk_flag={idpk}  -> INTEGER PK ok: {is_int_pk}")
            if not is_int_pk:
                print("     RECOMMENDATION: convert id to 'INTEGER PRIMARY KEY AUTOINCREMENT' (migration or drop+recreate).")
                issues.append((t, "bad_pk"))

        if seq_exists:
            cur.execute("SELECT seq FROM sqlite_sequence WHERE name=?", (t,))
            row = cur.fetchone()
            seq_val = row["seq"] if row else None
            maxid = None
            try:
                cur.execute(f"SELECT MAX(id) as m FROM {t}")
                rr = cur.fetchone()
                maxid = rr["m"] if rr and "m" in rr.keys() else None
            except Exception:
                for alt in ("artikel_id", "reifen_id"):
                    try:
                        cur.execute(f"SELECT MAX({alt}) as m FROM {t}")
                        rr = cur.fetchone()
                        if rr and rr["m"] is not None:
                            maxid = rr["m"]; break
                    except Exception:
                        pass
            print(f"  sqlite_sequence.seq={seq_val}  max(id)={maxid}")
            if seq_val is None:
                print("   -> No sqlite_sequence entry for this table.")
            else:
                try:
                    if maxid is not None and int(seq_val) < int(maxid):
                        print("   -> sqlite_sequence lower than max(id). Recommend: UPDATE sqlite_sequence or rebuild.")
                except Exception:
                    pass

    cur.close()
    conn.close()
    return issues

def migrate_pk_tables(db, tables):
    # backup
    bak = db + ".bak." + time.strftime("%Y%m%d%H%M%S")
    shutil.copy2(db, bak)
    print("Backup created:", bak)

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    migrated = []
    try:
        for tname, reason in tables:
            print("Migrating table:", tname, "reason:", reason)
            # define desired schemas (minimal necessary columns) - expand if needed
            desired_cols_map = {
                "kunden": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("kundennr","INTEGER"),("anrede","TEXT"),("name","TEXT"),("firma","TEXT"),("strasse","TEXT"),("plz","TEXT"),("stadt","TEXT"),("telefon","TEXT"),("email","TEXT"),("bemerkung","TEXT")],
                "rechnung": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("name","TEXT"),("layout","TEXT")],
                "rechnungen": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("datum","TIMESTAMP"),("betrag","NUMERIC")],
                "rechnung_layout": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("name","TEXT"),("layout_data","TEXT"),("layout","TEXT")],
                "lieferanten": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("lieferantnr","INTEGER"),("name","TEXT"),("firma","TEXT"),("strasse","TEXT"),("plz","TEXT"),("stadt","TEXT"),("telefon","TEXT"),("email","TEXT")],
                # add other tables if needed
            }
            if tname not in desired_cols_map:
                print("  No desired schema for", tname, "- skipping (add schema mapping if you want it migrated).")
                continue
            cols = desired_cols_map[tname]
            new_name = f"{tname}_new"
            defs = ", ".join(f"{n} {typ}" for n, typ in cols)
            cur.execute(f"CREATE TABLE IF NOT EXISTS {new_name} ({defs})")
            # compute common columns
            cur.execute(f"PRAGMA table_info({tname})")
            old_cols = [r["name"] for r in cur.fetchall()]
            common = [c for c,_ in cols if c in old_cols]
            if common:
                cols_csv = ", ".join(common)
                cur.execute(f"INSERT INTO {new_name} ({cols_csv}) SELECT {cols_csv} FROM {tname}")
            cur.execute(f"DROP TABLE {tname}")
            cur.execute(f"ALTER TABLE {new_name} RENAME TO {tname}")
            conn.commit()
            # update sqlite_sequence
            try:
                cur.execute(f"SELECT MAX(id) as m FROM {tname}")
                m = cur.fetchone()["m"] or 0
                cur.execute("INSERT OR REPLACE INTO sqlite_sequence(name,seq) VALUES(?,?)", (tname, int(m)))
                conn.commit()
            except Exception:
                pass
            migrated.append(tname)
    except Exception:
        traceback.print_exc()
        print("Migration failed, DB left in backup:", bak)
    finally:
        cur.close()
        conn.close()
    print("Migrated tables:", migrated)

def main():
    parser = argparse.ArgumentParser(description="Check and optionally migrate sqlite PKs (datenbank.sqlite).")
    parser.add_argument("--migrate", action="store_true", help="Perform migration for detected bad PKs (backup will be created).")
    args = parser.parse_args()

    db = resolve_db_path()
    print("Using DB:", db)
    if not os.path.exists(db):
        print("DB file does not exist:", db)
        sys.exit(1)

    issues = show_summary(db)
    if not issues:
        print("\nNo issues detected.")
        return

    print("\nDetected issues:", issues)
    if args.migrate:
        migrate_pk_tables(db, issues)
    else:
        print("Run with --migrate to attempt automatic migration of the affected tables (backup created).")

if __name__ == "__main__":
    main()
