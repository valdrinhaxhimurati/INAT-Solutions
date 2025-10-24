# Kopiert Ressourcen aus _internal neben die EXE, damit QSS/Logos gefunden werden.
import os, shutil, sys
from paths import data_dir

def _cand_paths():
    bases = []
    if getattr(sys, "_MEIPASS", None):
        bases += [sys._MEIPASS, os.path.join(sys._MEIPASS, "_internal")]
    exe_dir = os.path.dirname(getattr(sys, "executable", ""))
    if exe_dir:
        bases += [exe_dir, os.path.join(exe_dir, "_internal")]
    return [b for b in bases if b and os.path.isdir(b)]

def _copy(src, dst):
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)
    except Exception:
        pass

def _copy_first_found(relpath, dest_root):
    for base in _cand_paths():
        s = os.path.join(base, relpath)
        if os.path.exists(s):
            _copy(s, os.path.join(dest_root, relpath))
            return True
    return False

def main():
    if not getattr(sys, "frozen", False):
        return
    dest_root = os.path.dirname(sys.executable)
    needed = [
        "style.qss",
        "INAT SOLUTIONS.png",
        str(data_dir() / "config.json"),
        str(data_dir() / "schema.sql"),
        "config/rechnung_layout.json",
        "favicon.ico",
    ]
    for rel in needed:
        _copy_first_found(rel, dest_root)
    for d in ("rechnungen",):
        try: os.makedirs(os.path.join(dest_root, d), exist_ok=True)
        except Exception: pass

main()
