from PyQt5.QtCore import QObject, pyqtSignal
import traceback
from datetime import datetime

class TabLoader(QObject):
    chunk_ready = pyqtSignal(str, list)
    finished = pyqtSignal(str)
    error = pyqtSignal(str, str)
    total_rows = pyqtSignal(str, int)

    def __init__(self, key: str, table: str = "", query: str = "", params: list = None, chunk_size: int = 100):
        super().__init__()
        self.key = key
        self.table = table
        self.query = query
        self.params = params or []
        self.chunk_size = chunk_size

    def _parse_year_from_value(self, val):
        """Try some common date formats and return year as int or None."""
        if val is None:
            return None
        # direct datetime / date
        try:
            if hasattr(val, "year"):
                return int(val.year)
        except Exception:
            pass
        s = str(val).strip()
        if not s:
            return None
        # common ISO-like prefix YYYY or YYYY-MM-DD...
        if len(s) >= 4 and s[:4].isdigit():
            try:
                return int(s[:4])
            except Exception:
                pass
        # try several strptime patterns
        fmts = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%d.%m.%Y %H:%M:%S", "%d/%m/%Y")
        for f in fmts:
            try:
                return datetime.strptime(s, f).year
            except Exception:
                continue
        return None

    def run(self):
        try:
            from db_connection import get_db
        except Exception as e:
            self.error.emit(self.key, f"import get_db failed: {e}")
            return

        conn = None
        cur = None
        try:
            conn = get_db()
            cur = conn.cursor()

            if self.query:
                sql = self.query
            else:
                sql = f"SELECT * FROM {self.table}"

            # Detect if SQLite and adapt placeholders. Use ConnectionWrapper flag
            # if available, otherwise fallback to heuristic on the class module name.
            is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False)
            try:
                if not is_sqlite:
                    import sqlite3
                    if isinstance(conn, sqlite3.Connection):
                        is_sqlite = True
                    elif "sqlite" in getattr(conn.__class__, "__module__", "").lower():
                        is_sqlite = True
            except Exception:
                pass

            # Execute with parameters if provided
            if self.params:
                # For SQLite, replace %s with ?
                if is_sqlite:
                    sql = sql.replace("%s", "?")
                cur.execute(sql, tuple(self.params))
            else:
                cur.execute(sql)

            cols = [d[0] for d in (getattr(cur, "description", None) or [])]

            current_year = datetime.now().year
            while True:
                rows = cur.fetchmany(self.chunk_size)
                if not rows:
                    break
                out = []
                for r in rows:
                    if cols:
                        try:
                            row_dict = {cols[i]: r[i] for i in range(len(cols))}
                            # If loading buchhaltung only emit rows for the current year
                            if self.key == "buchhaltung":
                                year = self._parse_year_from_value(row_dict.get("datum") or row_dict.get("Datum") or row_dict.get("date"))
                                if year is None:
                                    # try parsing second column if present
                                    try:
                                        year = self._parse_year_from_value(r[1])
                                    except Exception:
                                        year = None
                                if year != current_year:
                                    continue
                            elif self.key == "rechnungen":
                                year = self._parse_year_from_value(row_dict.get("datum"))
                                if year != current_year:
                                    continue
                            out.append(row_dict)
                        except Exception:
                            out.append({i: v for i, v in enumerate(r)})
                    else:
                        try:
                            out.append({i: v for i, v in enumerate(r)})
                        except Exception:
                            out.append({})
                try:
                    self.chunk_ready.emit(self.key, out)
                except Exception:
                    pass

            try:
                self.finished.emit(self.key)
            except Exception:
                pass
        except Exception as e:
            tb = traceback.format_exc()
            try:
                self.error.emit(self.key, f"{e}\n{tb}")
            except Exception:
                pass
        finally:
            try:
                if cur is not None:
                    cur.close()
            except Exception:
                pass
            try:
                # if get_db returns pooled connection, adapt accordingly in your db_connection
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            except Exception:
                pass