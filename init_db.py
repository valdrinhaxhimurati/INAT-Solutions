# init_db.py
# -*- coding: utf-8 -*-
from typing import Optional
import os
import psycopg2
from psycopg2 import sql
import traceback

# --- Dein bisheriges Default-Schema bleibt erhalten (rückwärtskompatibel) ---
DEFAULT_SCHEMA_SQL = """
CREATE SEQUENCE IF NOT EXISTS rechnr_seq START 10000;
CREATE TABLE IF NOT EXISTS kunden (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    adresse TEXT,
    plz TEXT,
    ort TEXT,
    email TEXT
);
CREATE TABLE IF NOT EXISTS rechnungen (
    id SERIAL PRIMARY KEY,
    rechnungsnummer INT NOT NULL DEFAULT nextval('rechnr_seq'),
    kunde_id INT REFERENCES kunden(id),
    datum DATE NOT NULL DEFAULT CURRENT_DATE
);
"""

# ------------------------------------------------------------
# robustes Lesen von Textdateien (UTF-8, Fallbacks, Auto-Normalisierung)
# ------------------------------------------------------------
def _read_text_with_fallback(path):
    """Versuche UTF-8, dann cp1252, dann latin-1. Liefert str oder wirft Exception."""
    encodings = ("utf-8", "cp1252", "latin-1")
    last_exc = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_exc = e
            continue
    # wenn alle fehlschlagen, nochmal mit replace, damit nichts mehr crasht
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        raise last_exc or UnicodeDecodeError("unknown", b"", 0, 1, "cannot decode")

def _read_schema(path):
    # Versuche UTF-8, fallback cp1252 (Windows dumps)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="cp1252") as f:
            return f.read()

def _detect_and_decode(path):
    """
    Liest Datei als Bytes und versucht mehrere Decodings.
    Gibt (text, encoding) zurück oder wirft Exception.
    """
    encodings = ("utf-8", "cp1252", "latin-1")
    b = open(path, "rb").read()
    last_exc = None
    for enc in encodings:
        try:
            text = b.decode(enc)
            # Protokollieren, welche Kodierung gewählt wurde
            try:
                with open(os.path.join(os.path.dirname(__file__), "error.log"), "a", encoding="utf-8") as ef:
                    ef.write(f"[init_db] decode {path} with {enc}\n")
            except Exception:
                pass
            return text, enc
        except UnicodeDecodeError as e:
            last_exc = e
            continue
    # letzter Versuch: utf-8 mit replace, damit nichts mehr abstürzt
    try:
        text = b.decode("utf-8", errors="replace")
        try:
            with open(os.path.join(os.path.dirname(__file__), "error.log"), "a", encoding="utf-8") as ef:
                ef.write(f"[init_db] decode {path} with utf-8 (replace)\n")
        except Exception:
            pass
        return text, "utf-8(replace)"
    except Exception:
        raise last_exc or UnicodeDecodeError("unknown", b, 0, 1, "cannot decode")

# ------------------------------------------------------------
# Rolle & Datenbank idempotent anlegen (sicher gequotet)
# ------------------------------------------------------------
def ensure_role(pg_super_url: str, role: str, password: str):
    """
    Sorgt dafür, dass LOGIN-Rolle 'role' existiert und Passwort gesetzt ist.
    super_url z.B. postgresql://postgres:<pw>@localhost:5432/postgres
    """
    if not role:
        raise ValueError("Username fehlt für ensure_role().")

    with psycopg2.connect(pg_super_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(role)),
                    (password,)
                )
            else:
                cur.execute(
                    sql.SQL("ALTER ROLE {} WITH PASSWORD %s").format(sql.Identifier(role)),
                    (password,)
                )
            # Optional: Defaults setzen
            cur.execute(sql.SQL("ALTER ROLE {} SET search_path TO public").format(sql.Identifier(role)))

def ensure_database(pg_super_url: str, dbname: str, owner: Optional[str] = None):
    """
    Sorgt dafür, dass DB 'dbname' existiert (optional OWNER).
    """
    if not dbname:
        raise ValueError("DB-Name fehlt für ensure_database().")

    with psycopg2.connect(pg_super_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cur.fetchone() is not None
            if not exists:
                if owner:
                    cur.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {}").format(
                            sql.Identifier(dbname),
                            sql.Identifier(owner)
                        )
                    )
                else:
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
            elif owner:
                # Eigentümer ggf. anpassen (nicht kritisch, kann an Rechten scheitern)
                try:
                    cur.execute(
                        sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                            sql.Identifier(dbname),
                            sql.Identifier(owner)
                        )
                    )
                except Exception:
                    pass

# ------------------------------------------------------------
# Schema anwenden (inline-String ODER externe Datei)
# ------------------------------------------------------------
def apply_schema(pg_app_url: str, schema_sql: str = DEFAULT_SCHEMA_SQL):
    """
    Spielt das Schema ein.
    - Wenn du eine externe Datei nutzen willst: rufe ohne schema_sql auf
      und benenne deine Datei 'schema.sql' im Projekt- oder Modulverzeichnis.
    - Encoding wird robust gehandhabt (UTF-8 / CP1252 / Latin-1).
    - Mehrere Statements (durch ';') werden nacheinander ausgeführt.
    """
    sql_text = (schema_sql or "").strip()

    # Falls schema_sql leer ist -> versuche schema.sql zu finden/lesen
    if not sql_text:
        # zuerst im CWD, dann neben diesem Modul
        candidates = [
            os.path.join(os.getcwd(), "schema.sql"),
            os.path.join(os.path.dirname(__file__), "schema.sql"),
        ]
        for path in candidates:
            if os.path.exists(path):
                sql_text = _read_text_with_fallback(path).strip()
                break

    if not sql_text:
        # Nichts zu tun
        return

    # Naive Statement-Trennung (für "plain" Schemas ausreichend)
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]

    with psycopg2.connect(pg_app_url) as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()

def apply_schema(app_url, schema_path=None):
    """
    Liest schema.sql robust (Encoding-Fallback) und versucht, Statements auszuführen.
    Fehler bei einzelnen Statements werden protokolliert und übersprungen.
    """
    try:
        import psycopg2
    except Exception:
        raise RuntimeError("psycopg2 erforderlich, um apply_schema auszuführen.")

    if schema_path is None:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_path):
        return

    try:
        sql_text, used_enc = _detect_and_decode(schema_path)
    except Exception as e:
        # Protokollieren und neu werfen, damit Aufrufer die Ursache sieht
        with open(os.path.join(os.path.dirname(__file__), "error.log"), "a", encoding="utf-8") as ef:
            ef.write("[init_db] Fehler beim Lesen von schema: " + repr(e) + "\n")
            ef.write(traceback.format_exc() + "\n")
        raise

    conn = psycopg2.connect(app_url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        # Einfaches Split; komplexe Dumps ggf. mit psql importieren
        for stmt in sql_text.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                cur.execute(stmt)
            except Exception as e:
                # Fehler protokollieren, aber nicht abbrechen
                try:
                    with open(os.path.join(os.path.dirname(__file__), "error.log"), "a", encoding="utf-8") as ef:
                        ef.write(f"[init_db] Fehler beim Ausführen eines Statements (ignored): {e}\n")
                except Exception:
                    pass
                continue
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
