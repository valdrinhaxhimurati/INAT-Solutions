from PyQt5.QtCore import QObject, pyqtSignal
import traceback
from datetime import datetime

class TabLoader(QObject):
    chunk_ready = pyqtSignal(str, list)     # key, list_of_rows (dicts)
    total_rows = pyqtSignal(str, int)       # key, total_count (or -1)
    finished = pyqtSignal(str)              # key
    error = pyqtSignal(str, str)            # key, errmsg

    def __init__(self, key: str, table: str = None, query: str | None = None, chunk_size: int = 500):
        super().__init__()
        self.key = key
        self.table = table or key
        self.query = query
        self.chunk_size = int(chunk_size)

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
        # import inside run to avoid import-time DB side-effects
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

            # total rows (best effort)
            try:
                if self.query:
                    count_sql = f"SELECT COUNT(*) FROM ({self.query}) AS _cnt"
                else:
                    count_sql = f"SELECT COUNT(*) FROM {self.table}"
                cur.execute(count_sql)
                row = cur.fetchone()
                total = int(row[0]) if row and row[0] is not None else -1
            except Exception:
                total = -1
            try:
                self.total_rows.emit(self.key, total)
            except Exception:
                pass

            # For buchhaltung, prefer DB-side ordering newest-first to reduce client work
            if self.key == "buchhaltung" and not self.query:
                try:
                    sql = f"SELECT * FROM {self.table} ORDER BY datum DESC"
                except Exception:
                    sql = f"SELECT * FROM {self.table}"
            else:
                sql = self.query or f"SELECT * FROM {self.table}"
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