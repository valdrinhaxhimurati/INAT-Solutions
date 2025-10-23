import sys, os, traceback
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_connection import get_db, get_configured_url, ensure_app_schema

def run():
    print("Using DB:", get_configured_url())
    ensure_app_schema()
    conn = get_db()
    print("is_sqlite:", conn.is_sqlite)

    tests = [
        # table, columns, sample values
        ("kunden", ["name","firma","plz","strasse","stadt","telefon","anrede","email"],
         ("Test Kunde","Firma","00000","Muster","Ort","+491234","Herr","t@t.test")),
        ("lieferanten", ["name","firma","strasse","plz","stadt","telefon","email","portal_link","login","passwort"],
         ("LiefTest","LF","Str","00000","Ort","+491234","l@l.test","http://x","user","pw")),
        ("buchhaltung", ["datum","typ","kategorie","betrag","beschreibung"],
         ("2025-10-23 12:00:00","Einnahme","Sonstiges",123.45,"Test Eintrag")),
        ("artikellager", ["artikelnummer","bezeichnung","bestand","lagerort"],
         ("A-100","Testartikel",5,"Lager1")),
        ("reifenlager", ["kundennr","kunde_anzeige","fahrzeug","dimension","typ","dot","lagerort","eingelagert_am","ausgelagert_am","bemerkung"],
         (None,"Kunde Anzeige","VW","205/55R16","Sommer","2020","Regal","2025-10-23","","keine")),
        ("rechnung_layout", ["name","layout_data","layout","kopfzeile","einleitung","fusszeile","logo","logo_mime","logo_skala"],
         ("Default","{}","{}","Kopf","Einleitung","Fuss",None,None,1.0)),
    ]

    summary = []
    try:
        for table, cols, vals in tests:
            print("\n--- Testing table:", table, "cols:", cols)
            placeholders = None
            if conn.is_sqlite:
                placeholders = ", ".join(["?"] * len(cols))
            else:
                placeholders = ", ".join(["%s"] * len(cols))
            col_list = ", ".join(cols)
            insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
            try:
                with conn.cursor() as cur:
                    cur.execute(insert_sql, vals)
                    # fetch id info
                    inserted = None
                    # try RETURNING for Postgres if available
                    if not conn.is_sqlite:
                        try:
                            # some psycopg2 cursors return row from execute if RETURNING used,
                            # but we didn't add RETURNING; try to get lastrow via cursor.fetchone() if any
                            rid = getattr(cur, "lastrowid", None)
                            inserted = rid
                        except Exception:
                            inserted = None
                    else:
                        inserted = getattr(cur, "lastrowid", None)
                    # commit per insert
                    try:
                        conn.commit()
                    except Exception:
                        pass

                # select inserted row to verify (try by id if available, else use last inserted rowid)
                with conn.cursor() as cur:
                    if conn.is_sqlite and inserted:
                        sel_sql = f"SELECT * FROM {table} WHERE rowid=?"
                        cur.execute(sel_sql, (inserted,))
                        row = cur.fetchone()
                    elif inserted and not conn.is_sqlite:
                        # assume 'id' column exists
                        sel_sql = f"SELECT * FROM {table} WHERE id=%s"
                        cur.execute(sel_sql, (inserted,))
                        row = cur.fetchone()
                    else:
                        # fallback: select last row by ordering descending on ROWID or id
                        if conn.is_sqlite:
                            cur.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1")
                        else:
                            cur.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 1")
                        row = cur.fetchone()
                    print("Verified row (sample):", row)
            except Exception as e:
                print("ERROR inserting/selecting in", table, "->", e)
                traceback.print_exc()
                # continue to next test
                continue

            # cleanup: try to delete the inserted row(s)
            try:
                with conn.cursor() as cur:
                    if conn.is_sqlite:
                        # delete by matching the sample values (safer if id unknown)
                        where_clauses = " AND ".join([f"{c} = ?" for c in cols])
                        del_sql = f"DELETE FROM {table} WHERE {where_clauses} LIMIT 1"
                        # sqlite doesn't support LIMIT in DELETE before v3.25; try without LIMIT fallback
                        try:
                            cur.execute(del_sql, vals)
                        except Exception:
                            cur.execute(f"DELETE FROM {table} WHERE {where_clauses}", vals)
                    else:
                        where_clauses = " AND ".join([f"{c} = %s" for c in cols])
                        del_sql = f"DELETE FROM {table} WHERE {where_clauses} LIMIT 1"
                        try:
                            cur.execute(del_sql, vals)
                        except Exception:
                            cur.execute(f"DELETE FROM {table} WHERE {where_clauses}", vals)
                    try:
                        conn.commit()
                    except Exception:
                        pass
                summary.append((table, "OK"))
            except Exception as e:
                print("Cleanup error for", table, "->", e)
                traceback.print_exc()
                summary.append((table, "CLEANUP_FAILED"))

        print("\n--- Summary ---")
        for t, s in summary:
            print(t, ":", s)

    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    run()