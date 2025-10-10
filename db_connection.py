# -*- coding: utf-8 -*-
import os, json
import psycopg2, psycopg2.extras


CFG_PATHS = [
    os.path.join(os.getcwd(), "config.json"),
    os.path.join(os.path.dirname(__file__), "config.json"),
]


def _load_cfg() -> dict:
    """Config robust laden: erst utf-8, dann cp1252/latin-1; bei Nicht-UTF automatisch korrigiert zurückschreiben."""
    for p in CFG_PATHS:
        if not os.path.exists(p):
            continue
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                with open(p, "r", encoding=enc) as f:
                    cfg = json.load(f)
                if enc != "utf-8":
                    # gleich nach UTF-8 normalisieren
                    with open(p, "w", encoding="utf-8") as fw:
                        json.dump(cfg, fw, indent=4, ensure_ascii=False)
                return cfg
            except UnicodeDecodeError:
                continue
            except Exception:
                # defektes JSON etc.
                break
    return {}


def get_db():
    """
    Liefert die Hauptdatenbank-Verbindung (PostgreSQL).
    Erwartet in config.json:
      db_backend: "postgres"
      postgres_url: "postgresql://user:pass@host:port/dbname?...“
    """
    cfg = _load_cfg()
    url = (cfg.get("postgres_url") or os.environ.get("POSTGRES_URL") or "").strip()
    if not url:
        raise RuntimeError("Keine PostgreSQL-URL in config.json gefunden (Schlüssel: 'postgres_url').")

    conn = psycopg2.connect(url)
    # Optional: Schema setzen
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public")
    finally:
        conn.autocommit = False
    return conn


def dict_cursor_factory(conn):
    """Komfort: psycopg2-RealDictCursor zurückgeben (kompatibel zu vorhandenem Code)."""
    return psycopg2.extras.RealDictCursor
