import json
from db_connection import get_db, dict_cursor_factory

def run_db(sql, params=None, fetch=False, many=False):
    """Führe ein Statement sicher aus; gibt optional fetch-Ergebnisse zurück."""
    with get_db() as conn:
        try:
            try:
                conn.rollback()
            except Exception:
                pass

            # erkenne sqlite vs postgres über Wrapper-Property
            is_sqlite = getattr(conn, "is_sqlite", getattr(conn, "is_sqlite_conn", False))

            cur = conn.cursor() if is_sqlite else conn.cursor(cursor_factory=dict_cursor_factory)
            try:
                if many:
                    cur.executemany(sql, params or [])
                else:
                    cur.execute(sql, params or ())
                if fetch:
                    return cur.fetchall()
                return None
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise