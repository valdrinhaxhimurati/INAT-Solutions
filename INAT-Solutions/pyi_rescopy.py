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
            # If the source is a directory, copy the whole tree
            dst = os.path.join(dest_root, relpath)
            try:
                if os.path.isdir(s):
                    # copytree but preserve existing files and only overwrite if source is newer
                    for root, dirs, files in os.walk(s):
                        rel_root = os.path.relpath(root, s)
                        for d in dirs:
                            os.makedirs(os.path.join(dst, rel_root, d), exist_ok=True)
                        for f in files:
                            srcf = os.path.join(root, f)
                            dstf = os.path.join(dst, rel_root, f)
                            _copy(srcf, dstf)
                else:
                    _copy(s, dst)
            except Exception:
                pass
            return True
    return False

def main():
    if not getattr(sys, "frozen", False):
        return
    dest_root = os.path.dirname(sys.executable)
    needed = [
        "style.qss",
        "INAT SOLUTIONS.png",
        "locales",
        str(data_dir() / "config.json"),
        str(data_dir() / "schema.sql"),
        "config/rechnung_layout.json",
        "icons/logo.svg",
    ]
    for rel in needed:
        _copy_first_found(rel, dest_root)
    for d in ("rechnungen",):
        try: os.makedirs(os.path.join(dest_root, d), exist_ok=True)
        except Exception: pass

main()
