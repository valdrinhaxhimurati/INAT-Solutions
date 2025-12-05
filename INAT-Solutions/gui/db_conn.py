# gui/db_conn.py
import os, json, psycopg2
from paths import data_dir

def _cfg_path():
    return str(data_dir().parent / "config.json")

def _load_cfg():
    with open(_cfg_path(), "r", encoding="utf-8") as f:
        return json.load(f)

def get_pg_conn():
    cfg = _load_cfg()
    pg = cfg.get("pg") or {}
    host = pg.get("host"); port = str(pg.get("port") or "")
    db   = pg.get("database"); user = pg.get("user")
    pwd  = pg.get("password"); ssl  = pg.get("sslmode") or ("require" if "aivencloud.com" in (host or "") else "disable")
    if not all([host, port, db, user]):
        raise RuntimeError("PostgreSQL-Verbindung unvollständig. Bitte Installer/Settings prüfen.")
    conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd, sslmode=ssl)
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
    return conn


