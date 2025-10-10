# -*- coding: utf-8 -*-
from typing import Optional
import psycopg2, psycopg2.extras

DEFAULT_SCHEMA_SQL = """
CREATE SEQUENCE IF NOT EXISTS rechnr_seq START 10000;
CREATE TABLE IF NOT EXISTS kunden ( id SERIAL PRIMARY KEY, name TEXT NOT NULL, adresse TEXT, plz TEXT, ort TEXT, email TEXT );
CREATE TABLE IF NOT EXISTS rechnungen ( id SERIAL PRIMARY KEY, rechnungsnummer INT NOT NULL DEFAULT nextval('rechnr_seq'), kunde_id INT REFERENCES kunden(id), datum DATE NOT NULL DEFAULT CURRENT_DATE );
"""
def ensure_role(pg_super_url: str, role: str, password: str):
    with psycopg2.connect(pg_super_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
            if cur.fetchone() is None:
                cur.execute(f"CREATE ROLE {role} LOGIN PASSWORD %s", (password,))
def ensure_database(pg_super_url: str, dbname: str, owner: Optional[str] = None):
    with psycopg2.connect(pg_super_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone() is None:
                if owner: cur.execute(f"CREATE DATABASE {dbname} OWNER {owner}")
                else: cur.execute(f"CREATE DATABASE {dbname}")
def apply_schema(pg_app_url: str, schema_sql: str = DEFAULT_SCHEMA_SQL):
    with psycopg2.connect(pg_app_url) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
