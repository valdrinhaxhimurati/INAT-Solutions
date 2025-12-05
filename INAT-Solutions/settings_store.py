import os, sys, json, sqlite3
from typing import Optional, Tuple, Any
from db_connection import get_db
import paths

SQLITE_TABLE = """
CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value_bytes BLOB,
  value_text TEXT,
  mime TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
PG_TABLE = """
CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value_bytes BYTEA,
  value_text TEXT,
  mime TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def _is_pg(conn) -> bool:
    # Since conn might be ConnectionWrapper, check if it's not sqlite
    return hasattr(conn, 'is_sqlite') and not conn.is_sqlite

def _ensure_table(conn):
    cur = conn.cursor()
    cur.execute(PG_TABLE if _is_pg(conn) else SQLITE_TABLE)
    conn.commit()

def set_blob(key: str, data: bytes, mime: Optional[str] = None) -> None:
    conn = get_db()
    try:
        _ensure_table(conn)
        cur = conn.cursor()
        ph = "%s" if _is_pg(conn) else "?"
        if _is_pg(conn):
            from psycopg2 import Binary as PGBinary  # type: ignore
            data = PGBinary(data)
            sql = f"""
            INSERT INTO app_settings (key, value_bytes, mime, updated_at)
            VALUES ({ph},{ph},{ph}, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET
              value_bytes = EXCLUDED.value_bytes,
              mime = EXCLUDED.mime,
              updated_at = CURRENT_TIMESTAMP;
            """
        else:
            data = sqlite3.Binary(data)
            sql = f"""
            INSERT INTO app_settings (key, value_bytes, mime, updated_at)
            VALUES ({ph},{ph},{ph}, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
              value_bytes = excluded.value_bytes,
              mime = excluded.mime,
              updated_at = CURRENT_TIMESTAMP;
            """
        cur.execute(sql, (key, data, mime))
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

def get_blob(key: str) -> Tuple[Optional[bytes], Optional[str]]:
    conn = get_db()
    try:
        _ensure_table(conn)
        cur = conn.cursor()
        ph = "%s" if _is_pg(conn) else "?"
        cur.execute(f"SELECT value_bytes, mime FROM app_settings WHERE key={ph} LIMIT 1", (key,))
        row = cur.fetchone()
        if not row:
            return None, None
        data, mime = row[0], row[1]
        if isinstance(data, memoryview):
            data = data.tobytes()
        return data, mime
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

def set_text(key: str, value: str, mime: Optional[str] = None) -> None:
    conn = get_db()
    try:
        _ensure_table(conn)
        cur = conn.cursor()
        ph = "%s" if _is_pg(conn) else "?"
        sql = (f"""
            INSERT INTO app_settings (key, value_text, mime, updated_at)
            VALUES ({ph},{ph},{ph}, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET
              value_text = EXCLUDED.value_text,
              mime = EXCLUDED.mime,
              updated_at = CURRENT_TIMESTAMP;
        """ if _is_pg(conn) else f"""
            INSERT INTO app_settings (key, value_text, mime, updated_at)
            VALUES ({ph},{ph},{ph}, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
              value_text = excluded.value_text,
              mime = excluded.mime,
              updated_at = CURRENT_TIMESTAMP;
        """)
        cur.execute(sql, (key, value, mime))
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

def get_text(key: str) -> Optional[str]:
    conn = get_db()
    try:
        _ensure_table(conn)
        cur = conn.cursor()
        ph = "%s" if _is_pg(conn) else "?"
        cur.execute(f"SELECT value_text FROM app_settings WHERE key={ph} LIMIT 1", (key,))
        row = cur.fetchone()
        return None if not row else row[0]
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

def set_json(key: str, obj: Any) -> None:
    set_text(key, json.dumps(obj, ensure_ascii=False), mime="application/json")

def get_json(key: str) -> Optional[Any]:
    txt = get_text(key)
    if not txt:
        return None
    try:
        return json.loads(txt)
    except Exception:
        return None

# Einmaliger Import aus Dateien (optional)
def _app_dir() -> str:
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(sys.argv[0]))

def _res_path(*parts) -> str:
    return os.path.join(_app_dir(), *parts)

def import_json_if_missing(key: str, rel_path: str) -> Optional[Any]:
    existing = get_json(key)
    if existing is not None:
        return existing
    src = _res_path(*rel_path.split("/"))
    try:
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        set_json(key, data)
        return data
    except Exception:
        return None

# Convenience fÃ¼r Logo
def save_logo_from_file(path: str) -> None:
    if not path or not os.path.isfile(path):
        return
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/bmp" if ext == ".bmp" else "application/octet-stream"
    with open(path, "rb") as f:
        set_blob("invoice_logo", f.read(), mime)

def load_config():
    import os
    import json
    config_file = os.path.join(paths.get_app_data_dir(), "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"db_type": "sqlite"}  # Default
