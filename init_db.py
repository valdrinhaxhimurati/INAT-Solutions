# init_db.py
# -*- coding: utf-8 -*-
from typing import Optional
import os
import psycopg2
from psycopg2 import sql

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
def _read_text_with_fallback(path: str) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                txt = f.read()
            # Wenn die Datei nicht UTF-8 war, direkt auf UTF-8 zurückschreiben (einmalige Reparatur)
            if enc != "utf-8":
                try:
                    with open(path, "w", encoding="utf-8") as fw:
                        fw.write(txt)
                except Exception:
                    pass
            return txt
        except UnicodeDecodeError:
            continue
    # Letzter Notbehelf – verliert nie
    with open(path, "rb") as fb:
        return fb.read().decode("latin-1", errors="replace")

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
