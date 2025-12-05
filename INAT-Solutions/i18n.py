import json
import os
from settings_store import get_text, set_text
from paths import resource_path

# Pfad zu den Übersetzungsdateien (unter PyInstaller wird resource_path sys._MEIPASS berücksichtigen)
LOCALES_DIR = resource_path('locales')

# Aktuelle Sprache
_current_language = 'de'  # Standard: Deutsch

def set_language(lang):
    global _current_language
    _current_language = lang
    set_text('language', lang)

def get_language():
    lang = get_text('language')
    if lang:
        global _current_language
        _current_language = lang
    return _current_language

# Lade Übersetzungen
_translations = {}

def _load_translations():
    """Dynamically scan `LOCALES_DIR` for `*.json` files and load them.
    This works both in development (repo tree) and when the app is frozen
    (PyInstaller extracts data files to sys._MEIPASS and `resource_path` points
    to that location).
    """
    _translations.clear()
    try:
        if os.path.isdir(LOCALES_DIR):
            for fname in os.listdir(LOCALES_DIR):
                if not fname.lower().endswith('.json'):
                    continue
                lang = os.path.splitext(fname)[0]
                path = os.path.join(LOCALES_DIR, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        _translations[lang] = json.load(f)
                except Exception:
                    _translations[lang] = {}
    except Exception:
        # If anything goes wrong, leave translations empty
        pass


_load_translations()

def _(text):
    """Übersetze den Text in die aktuelle Sprache."""
    return _translations.get(_current_language, {}).get(text, text)

# Initialisiere Sprache beim Import
try:
    get_language()
except:
    pass