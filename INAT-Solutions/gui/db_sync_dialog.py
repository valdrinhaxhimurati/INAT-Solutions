from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QGroupBox, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt
import traceback
import os, shutil, time, tempfile, hashlib, sqlite3
from pathlib import Path
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from i18n import _
from paths import local_db_path
try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import sql
except Exception:
    psycopg2 = None
    sql = None

try:
    import paramiko
except Exception:
    paramiko = None

import re

# Pfad zur lokalen SQLite-DB - dynamisch aus paths.py
def _get_db_path():
    return Path(local_db_path())

DB_PATH = _get_db_path()

# Alle Tabellen die synchronisiert werden sollen
_SYNC_TABLES = [
    "kunden", "lieferanten", "rechnungen", "rechnung_positionen", 
    "buchhaltung", "dienstleistungen", "reifen", "artikel", "material",
    "auftraege", "kategorien", "config"
]

def _timestamp():
    return time.strftime("%Y%m%d_%H%M%S")

def backup_db(target_dir: str | Path | None = None) -> str:
    src = DB_PATH
    if not src.exists():
        raise FileNotFoundError(f"DB not found: {src}")
    target_dir = Path(target_dir) if target_dir else src.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    bak_base = target_dir / f"{src.stem}_{_timestamp()}{src.suffix}"
    shutil.copy2(str(src), str(bak_base))
    wal = src.with_name(src.name + "-wal")
    jrn = src.with_name(src.name + "-journal")
    if wal.exists():
        shutil.copy2(str(wal), str(bak_base.with_name(bak_base.name + ".wal")))
    if jrn.exists():
        shutil.copy2(str(jrn), str(bak_base.with_name(bak_base.name + ".journal")))
    return str(bak_base)

def create_sqlite_snapshot(src_db: str | Path, dst_path: str | Path) -> str:
    src_conn = sqlite3.connect(str(src_db))
    try:
        dst_conn = sqlite3.connect(str(dst_path))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
    return str(dst_path)

def sftp_put_get(host, port, username, password, remote_path, local_src=None, download=False, key_filepath=None):
    if paramiko is None:
        raise RuntimeError(_("paramiko nicht installiert (pip install paramiko)"))
    local_src = str(local_src) if local_src else None
    transport = paramiko.Transport((host, int(port)))
    try:
        if key_filepath:
            key = paramiko.RSAKey.from_private_key_file(key_filepath)
            transport.connect(username=username, pkey=key)
        else:
            transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        if download:
            sftp.get(remote_path, local_src)
        else:
            sftp.put(local_src, remote_path)
        sftp.close()
        return True
    finally:
        transport.close()

def upload_db_via_snapshot(host, port, username, password, remote_path, db_path: str | Path | None = None):
    db_path = str(db_path or DB_PATH)
    if not Path(db_path).exists():
        raise FileNotFoundError(db_path)
    backup_db()
    tmp = Path(tempfile.gettempdir()) / f"{Path(db_path).stem}_snapshot_{int(time.time())}.sqlite"
    create_sqlite_snapshot(db_path, tmp)
    try:
        ok = sftp_put_get(host, port, username, password, remote_path, local_src=str(tmp), download=False)
        # optional verify omitted for brevity
        return ok
    finally:
        try: tmp.unlink()
        except: pass

def download_db_via_snapshot(host, port, username, password, remote_path, local_db_path: str | Path | None = None):
    local_db_path = str(local_db_path or DB_PATH)
    tmp = Path(tempfile.gettempdir()) / f"{Path(local_db_path).stem}_download_{int(time.time())}.sqlite"
    sftp_put_get(host, port, username, password, remote_path, local_src=str(tmp), download=True)
    if Path(local_db_path).exists():
        backup_db()
    shutil.copy2(str(tmp), local_db_path)
    try: tmp.unlink()
    except: pass
    return True

def unc_copy_from(remote_unc_path: str, local_path: str | None = None) -> bool:
    local_path = str(local_path or DB_PATH)
    if Path(local_path).exists():
        backup_db()
    shutil.copy2(remote_unc_path, local_path)
    wal_remote = Path(remote_unc_path).with_name(Path(remote_unc_path).name + "-wal")
    if wal_remote.exists():
        shutil.copy2(str(wal_remote), str(Path(local_path).with_name(Path(local_path).name + ".wal")))
    return True

def unc_copy_to(local_path: str | None = None, remote_unc_path: str | None = None) -> bool:
    local_path = str(local_path or DB_PATH)
    if not Path(local_path).exists():
        raise FileNotFoundError(local_path)
    backup_db()
    if remote_unc_path is None:
        raise ValueError("remote_unc_path required")
    shutil.copy2(local_path, remote_unc_path)
    wal_local = Path(local_path).with_name(Path(local_path).name + "-wal")
    if wal_local.exists():
        shutil.copy2(str(wal_local), str(Path(remote_unc_path).with_name(Path(remote_unc_path).name + ".wal")))
    return True

def _get_remote_dsn_from_settings():
    """
    Liefert Remote-DSN nur aus dem GUI-Settings-Dialog (falls vorhanden).
    Fallback: None -> Dialog-Feld verwenden.
    """
    try:
        from gui.db_settings_dialog import get_remote_dsn
        return get_remote_dsn()
    except Exception:
        return None

def _sqlite_rows(db_path: str, table: str):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.execute(f"SELECT * FROM {table}")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows

def _sqlite_insert_many(db_path: str, table: str, rows):
    if not rows:
        return 0
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cols = list(rows[0].keys())
    placeholders = ",".join(["?"]*len(cols))
    sql = f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    vals = [[r.get(c) for c in cols] for r in rows]
    cur.executemany(sql, vals)
    con.commit()
    cnt = cur.rowcount if hasattr(cur, "rowcount") else len(vals)
    con.close()
    return cnt

def _pg_insert_many(pg_conn, table: str, rows):
    if not rows:
        return 0
    cols = list(rows[0].keys())
    colnames = ", ".join(cols)
    placeholders = ", ".join([f"%({c})s" for c in cols])
    sql = f"INSERT INTO {table} ({colnames}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
    with pg_conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows)
    pg_conn.commit()
    return len(rows)

def _pg_tables(pg_conn):
    """Gibt Liste (schema, table) in public zurück."""
    with pg_conn.cursor() as cur:
        cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='public';")
        return [(r[0], r[1]) for r in cur.fetchall()]

def _pg_columns(pg_conn, table: str) -> list[str]:
    """Gibt Spaltennamen einer Remote-Tabelle zurück."""
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        return [r[0] for r in cur.fetchall()]

def _pg_primary_key_columns(pg_conn, table: str) -> list[str]:
    """Ermittelt Primärschlüsselspalten einer Remote-Tabelle (public.schema)."""
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary;
        """, (f'public.{table}',))
        return [r[0] for r in cur.fetchall()]

def _sqlite_columns(db_path: str, table: str) -> list[str]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(f"PRAGMA table_info('{table}')")
        return [r["name"] for r in cur.fetchall()]
    finally:
        con.close()

def _sqlite_primary_key_column(db_path: str, table: str) -> str | None:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(f"PRAGMA table_info('{table}')")
        for r in cur.fetchall():
            if r["pk"]:
                return r["name"]
    finally:
        con.close()
    return None

def _map_local_row_to_remote(local_row: dict, colmap: dict) -> dict:
    """
    colmap: mapping from remote_col -> local_col
    Liefert dict mit remote_col keys und entsprechenden Werten aus local_row.
    """
    out = {}
    for rcol, lcol in colmap.items():
        out[rcol] = local_row.get(lcol)
    return out

def _build_colmap_for_table(local_db: str, pg_conn, table: str) -> dict:
    """
    Baut eine mapping remote_col -> local_col.
    - Priorität: gleiche Namen
    - Falls remote PK name existiert but local PK different, map remote_pk -> local_pk
    - Rückgabe enthält nur remote columns, die im lokalen Row vorhanden sind (oder None Werte erlaubt).
    """
    remote_cols = _pg_columns(pg_conn, table)
    local_cols = _sqlite_columns(local_db, table)
    colmap = {}
    for rc in remote_cols:
        if rc in local_cols:
            colmap[rc] = rc
    # ensure primary key mapping if names differ
    pk_local = _sqlite_primary_key_column(local_db, table)
    pk_remote_list = _pg_primary_key_columns(pg_conn, table)
    if pk_remote_list:
        pk_remote = pk_remote_list[0]
        if pk_remote not in colmap:
            # map remote pk to local pk if possible
            if pk_local:
                colmap[pk_remote] = pk_local
    return colmap

def _pg_insert_many_with_colmap(pg_conn, table: str, rows: list[dict], colmap: dict, pk_remote: str | None):
    """
    rows: lokale rows (dicts with local column names)
    colmap: remote_col -> local_col
    Baut Insert-Sätze mit remote-Spalten (nur die remote in colmap) und ON CONFLICT (pk_remote) DO NOTHING wenn pk_remote gegeben.
    """
    if not rows:
        return 0
    # build normalized rows mapped to remote column names
    mapped_rows = []
    remote_cols = list(colmap.keys())
    for r in rows:
        mapped_rows.append([r.get(colmap[c]) for c in remote_cols])

    # build SQL with psycopg2.sql
    ident_cols = sql.SQL(', ').join([sql.Identifier(c) for c in remote_cols])
    insert_base = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
        sql.Identifier('public', table),
        ident_cols
    )
    if pk_remote and pk_remote in remote_cols:
        conflict = sql.SQL(" ON CONFLICT ({}) DO NOTHING").format(sql.Identifier(pk_remote))
        q = sql.SQL("{}{}").format(insert_base, conflict)
    else:
        q = insert_base

    with pg_conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, q.as_string(pg_conn), mapped_rows)
    pg_conn.commit()
    return len(mapped_rows)

# Anpassung in _sync_local_to_remote_pg: ersetze bisherigen Insert-Mechanismus durch Mapping-Version
def _sync_local_to_remote_pg(local_db_path: str, remote_dsn: str, tables=None):
    if psycopg2 is None:
        raise RuntimeError(_("psycopg2 fehlt (pip install psycopg2-binary)"))
    tables = tables or _SYNC_TABLES
    pg = psycopg2.connect(dsn=remote_dsn)
    report = {}
    try:
        for t in tables:
            # sicherstellen, dass remote Tabelle existiert (retry/ schema.sql bei Bedarf)
            try:
                pk_remote_list = _pg_primary_key_columns(pg, t)
                pk_remote = pk_remote_list[0] if pk_remote_list else None
                # read remote existing PK values
                if pk_remote:
                    with pg.cursor() as cur:
                        cur.execute(sql.SQL("SELECT {} FROM {}").format(sql.Identifier(pk_remote), sql.Identifier('public', t)))
                        remote_ids = set(r[0] for r in cur.fetchall())
                else:
                    # keine PK remote -> leere Menge (alles wird gesendet)
                    remote_ids = set()
            except Exception:
                # schema.sql anwenden, reconnect und neu versuchen
                apply_schema_sql_to_remote(remote_dsn)
                try:
                    pg.close()
                except Exception:
                    pass
                pg = psycopg2.connect(dsn=remote_dsn)
                pk_remote_list = _pg_primary_key_columns(pg, t)
                pk_remote = pk_remote_list[0] if pk_remote_list else None
                if pk_remote:
                    with pg.cursor() as cur:
                        cur.execute(sql.SQL("SELECT {} FROM {}").format(sql.Identifier(pk_remote), sql.Identifier('public', t)))
                        remote_ids = set(r[0] for r in cur.fetchall())
                else:
                    remote_ids = set()

            # lokale Rows und PK
            local_rows = _sqlite_rows(local_db_path, t)
            pk_local = _sqlite_primary_key_column(local_db_path, t)
            # build colmap remote_col -> local_col
            colmap = _build_colmap_for_table(local_db_path, pg, t)
            if not colmap:
                # nothing to insert because no shared columns
                report[t] = {"local_total": len(local_rows), "to_send": 0, "inserted": 0}
                continue

            # determine which rows to send using local pk mapped to remote pk
            send_candidates = []
            for row in local_rows:
                if pk_remote and pk_local:
                    local_pk_val = row.get(pk_local)
                    if local_pk_val not in remote_ids:
                        send_candidates.append(row)
                else:
                    # no PK available -> send all (or skip)
                    send_candidates.append(row)

            inserted = _pg_insert_many_with_colmap(pg, t, send_candidates, colmap, pk_remote)
            report[t] = {"local_total": len(local_rows), "to_send": len(send_candidates), "inserted": inserted}
    finally:
        try:
            pg.close()
        except Exception:
            pass
    return report

def _sync_remote_to_local_pg(local_db_path: str, remote_dsn: str, tables=None):
    if psycopg2 is None:
        raise RuntimeError(_("psycopg2 fehlt (pip install psycopg2-binary)"))
    tables = tables or list(reversed(_SYNC_TABLES))
    pg = psycopg2.connect(dsn=remote_dsn)
    report = {}
    try:
        for t in tables:
            with pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM {t}")
                remote_rows = [dict(r) for r in cur.fetchall()]
            # hole lokale ids
            con = sqlite3.connect(local_db_path)
            cur_local = con.cursor()
            cur_local.execute(f"SELECT id FROM {t}")
            local_ids = set(r[0] for r in cur_local.fetchall())
            con.close()
            to_insert = [r for r in remote_rows if r.get("id") not in local_ids]
            inserted = _sqlite_insert_many(local_db_path, t, to_insert) if to_insert else 0
            report[t] = {"remote_total": len(remote_rows), "to_insert": len(to_insert), "inserted": inserted}
    finally:
        pg.close()
    return report

def _map_sqlite_type_to_pg(sqlite_type: str) -> str:
    t = (sqlite_type or "").upper()
    if "INT" in t:
        return "BIGINT"
    if "CHAR" in t or "CLOB" in t or "TEXT" in t:
        return "TEXT"
    if "BLOB" in t:
        return "BYTEA"
    if "REAL" in t or "FLOA" in t or "DOUB" in t:
        return "DOUBLE PRECISION"
    if "NUM" in t or "DEC" in t:
        return "NUMERIC"
    return "TEXT"

def _sqlite_sql_to_postgres(sql_text: str) -> str:
    """Heuristische Konvertierung: SQLite -> Postgres (Typen + INSERT OR IGNORE etc.)."""
    s = sql_text

    # Typ‑Mapping
    s = re.sub(r'\bBLOB\b', 'BYTEA', s, flags=re.IGNORECASE)
    s = re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b', 'BIGSERIAL PRIMARY KEY', s, flags=re.IGNORECASE)
    s = re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\b', 'BIGINT PRIMARY KEY', s, flags=re.IGNORECASE)
    s = re.sub(r'\bAUTOINCREMENT\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\bDATETIME\b', 'TIMESTAMP', s, flags=re.IGNORECASE)

    # SQLite -> Postgres: "INSERT OR IGNORE INTO ..." -> "INSERT INTO ... ON CONFLICT DO NOTHING"
    # Versuche komplette INSERT OR IGNORE Statements zu ersetzen (multiline tolerant).
    insert_pattern = re.compile(
        r'(INSERT\s+OR\s+IGNORE\s+INTO\s+([^\(\s;]+)\s*(\([^\)]*\))\s*VALUES\s*(\([^\;]*?\)))',
        flags=re.IGNORECASE | re.DOTALL
    )

    def _insert_repl(m):
        table = m.group(2).strip()
        cols = m.group(3).strip()
        vals = m.group(4).strip()
        return f"INSERT INTO {table} {cols} VALUES {vals} ON CONFLICT DO NOTHING"

    s = insert_pattern.sub(_insert_repl, s)

    # Falls es "INSERT OR IGNORE INTO table VALUES(...)" ohne Spaltenliste gibt:
    insert_pattern2 = re.compile(
        r'(INSERT\s+OR\s+IGNORE\s+INTO\s+([^\s;]+)\s+VALUES\s*(\([^\;]*?\)))',
        flags=re.IGNORECASE | re.DOTALL
    )

    def _insert_repl2(m):
        table = m.group(2).strip()
        vals = m.group(3).strip()
        return f"INSERT INTO {table} VALUES {vals} ON CONFLICT DO NOTHING"

    s = insert_pattern2.sub(_insert_repl2, s)

    # Entferne oder ignoriere PRAGMA / sqlite_sequence / other sqlite-only statements
    s = re.sub(r'PRAGMA\s+[^\;]+;', '', s, flags=re.IGNORECASE)
    s = re.sub(r'DROP\s+TABLE\s+IF\s+EXISTS\s+sqlite_sequence\s*;\s*', '', s, flags=re.IGNORECASE)

    # Aufräumen
    s = re.sub(r'[ \t]+', ' ', s)
    return s

def create_remote_schema_from_local(remote_dsn: str, tables: list | None = None, local_db: str | None = None) -> dict:
    """Erstellt fehlende Tabellen in Remote-Postgres basierend auf lokalem SQLite‑Schema."""
    if psycopg2 is None:
        raise RuntimeError(_("psycopg2 fehlt (pip install psycopg2-binary)"))
    local_db = str(local_db or DB_PATH)
    con = sqlite3.connect(local_db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    try:
        if not tables:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            tables = [r[0] for r in cur.fetchall()]
        pg = psycopg2.connect(dsn=remote_dsn)
        report = {"created": [], "skipped": [], "errors": {}}
        try:
            for tbl in tables:
                cols = cur.execute(f"PRAGMA table_info('{tbl}')").fetchall()
                if not cols:
                    report["skipped"].append(tbl); continue
                col_defs = []
                pk_cols = [c["name"] for c in cols if c["pk"]]
                for c in cols:
                    name = c["name"]
                    ctype = _map_sqlite_type_to_pg(c["type"])
                    if c["pk"] and len(pk_cols) == 1 and ("INT" in (c["type"] or "").upper()):
                        col_defs.append(f"{name} BIGSERIAL PRIMARY KEY"); continue
                    notnull = " NOT NULL" if c["notnull"] else ""
                    default = f" DEFAULT {c['dflt_value']}" if c["dflt_value"] is not None else ""
                    col_defs.append(f"{name} {ctype}{notnull}{default}")
                pk_clause = f", PRIMARY KEY ({', '.join(pk_cols)})" if len(pk_cols) > 1 else ""
                create_sql = f"CREATE TABLE IF NOT EXISTS {tbl} ({', '.join(col_defs)}{pk_clause});"
                try:
                    with pg.cursor() as pc:
                        pc.execute(create_sql)
                    report["created"].append(tbl)
                except Exception as e:
                    report["errors"][tbl] = str(e)
            pg.commit()
        finally:
            pg.close()
    finally:
        con.close()
    return report

def apply_schema_sql_to_remote(remote_dsn: str, schema_path: str = None):
    """
    Führt schema.sql (nach einfacher Anpassung) auf Remote Postgres aus.
    """
    if psycopg2 is None:
        raise RuntimeError(_("psycopg2 fehlt (pip install psycopg2-binary)"))
    schema_path = schema_path or str(Path(__file__).resolve().parents[1] / "schema.sql")
    p = Path(schema_path)
    if not p.exists():
        raise FileNotFoundError(f"schema.sql nicht gefunden: {schema_path}")
    raw_sql = p.read_text(encoding="utf-8")
    pg_sql = _sqlite_sql_to_postgres(raw_sql)
    with psycopg2.connect(dsn=remote_dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for stmt in (s.strip() for s in pg_sql.split(";")):
                if stmt:
                    cur.execute(stmt)
    return True

def _all_sqlite_tables(local_db: str | Path) -> list:
    """Gibt alle user-Tabellen aus der lokalen SQLite DB zurück (ohne sqlite_ Meta-Tabellen)."""
    local_db = str(local_db)
    con = sqlite3.connect(local_db)
    try:
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        return [r[0] for r in cur.fetchall()]
    finally:
        con.close()


class DBSyncDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Datenbank synchronisieren"))
        self.resize(550, 400)
        
        layout = self.content_layout
        layout.setSpacing(15)

        # === Verbindung ===
        conn_group = QGroupBox(_("Verbindung"))
        conn_group.setStyleSheet(GROUPBOX_STYLE)
        conn_layout = QVBoxLayout(conn_group)

        # Remote DSN: wenn bereits in Settings vorhanden, anzeigen; sonst Eingabefeld
        self.remote_from_settings = _get_remote_dsn_from_settings()
        if self.remote_from_settings:
            conn_layout.addWidget(QLabel(_("Remote-DB (aus Einstellungen):")))
            lbl = QLabel(self.remote_from_settings)
            lbl.setStyleSheet("color: #666;")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(lbl.textInteractionFlags() | Qt.TextSelectableByMouse)
            conn_layout.addWidget(lbl)
            self.le_remote = None
        else:
            conn_layout.addWidget(QLabel(_("Remote-DB-DSN:")))
            self.le_remote = QLineEdit()
            self.le_remote.setPlaceholderText("postgresql://user:pass@host:5432/db")
            conn_layout.addWidget(self.le_remote)

        layout.addWidget(conn_group)

        # === Synchronisation ===
        sync_group = QGroupBox(_("Synchronisation"))
        sync_group.setStyleSheet(GROUPBOX_STYLE)
        sync_layout = QVBoxLayout(sync_group)

        # Richtung
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel(_("Richtung:")))
        self.combo_dir = QComboBox()
        self.combo_dir.addItems([
            _("Upload (lokal → remote)"),
            _("Download (remote → lokal)")
        ])
        dir_layout.addWidget(self.combo_dir, 1)
        sync_layout.addLayout(dir_layout)

        # Backup Checkbox
        self.cb_backup = QCheckBox(_("Vorher lokales Backup erstellen (empfohlen)"))
        self.cb_backup.setChecked(True)
        sync_layout.addWidget(self.cb_backup)

        # Start-Button
        self.btn_start = QPushButton(_("Synchronisation starten"))
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.btn_start.clicked.connect(self._on_start)
        sync_layout.addWidget(self.btn_start)

        layout.addWidget(sync_group)

        # === Fortschrittsanzeige ===
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        
        self.progress_label = QLabel()
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_frame)

        # === Info ===
        info_group = QGroupBox(_("Hinweise"))
        info_group.setStyleSheet(GROUPBOX_STYLE)
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(_(
            "• Upload: Sendet lokale Daten zur Remote-Datenbank\n"
            "• Download: Holt Daten von der Remote-Datenbank\n"
            "• Bestehende Einträge werden nicht überschrieben\n"
            "• Ein Backup vor der Synchronisation wird empfohlen"
        ))
        info_text.setStyleSheet("color: #666;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)

        # Schließen-Button
        self.btn_close = QPushButton(_("Schließen"))
        self.btn_close.clicked.connect(self.reject)
        layout.addWidget(self.btn_close)

    def _on_start(self):
        self.btn_start.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.progress_label.setText(_("Synchronisation läuft..."))
        
        # Force UI update
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        try:
            direction = self.combo_dir.currentText()
            # determine remote DSN: prefer settings, else input
            remote_dsn = self.remote_from_settings or (self.le_remote.text().strip() if self.le_remote else "")
            if not remote_dsn:
                raise RuntimeError(_("Kein Remote-DB-DSN angegeben. Bitte in den Einstellungen konfigurieren."))

            # perform backup if requested
            if self.cb_backup.isChecked():
                self.progress_label.setText(_("Backup wird erstellt..."))
                QApplication.processEvents()
                try:
                    backup_db()
                except Exception as e:
                    QMessageBox.warning(self, _("Backup fehlgeschlagen"), 
                                       _("Lokales Backup konnte nicht erstellt werden:\n") + f"{e}")

            local_db = str(_get_db_path())

            if _("Download") in direction:
                self.progress_label.setText(_("Daten werden heruntergeladen..."))
                QApplication.processEvents()
                report = _sync_remote_to_local_pg(local_db, remote_dsn)
                self._show_report(_("Download abgeschlossen"), report)
            else:
                self.progress_label.setText(_("Schema wird erstellt..."))
                QApplication.processEvents()
                tables_to_sync = _all_sqlite_tables(local_db)
                create_report = create_remote_schema_from_local(remote_dsn, tables=tables_to_sync, local_db=local_db)
                
                if create_report.get("errors"):
                    QMessageBox.warning(self, _("Schema-Fehler"), 
                                       _("Einige Tabellen konnten nicht erstellt werden:\n") + 
                                       str(create_report["errors"]))
                
                self.progress_label.setText(_("Daten werden hochgeladen..."))
                QApplication.processEvents()
                report = _sync_local_to_remote_pg(local_db, remote_dsn, tables=tables_to_sync)
                self._show_report(_("Upload abgeschlossen"), report)

            self.accept()
            
        except Exception as e:
            tb = traceback.format_exc()
            QMessageBox.critical(self, _("Fehler bei DB-Sync"), f"{str(e)}\n\n{tb}")
        finally:
            self.progress_frame.setVisible(False)
            self.btn_start.setEnabled(True)
            self.btn_close.setEnabled(True)
    
    def _show_report(self, title, report):
        """Zeigt einen formatierten Sync-Report an."""
        lines = [title, ""]
        for table, info in report.items():
            if isinstance(info, dict):
                inserted = info.get("inserted", 0)
                total = info.get("local_total", info.get("remote_total", "?"))
                lines.append(f"• {table}: {inserted} neue Einträge (von {total})")
            else:
                lines.append(f"• {table}: {info}")
        
        QMessageBox.information(self, title, "\n".join(lines))