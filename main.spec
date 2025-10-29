# main.spec
# -*- mode: python ; coding: utf-8 -*-

import os
here = lambda p: os.path.abspath(p)

block_cipher = None

# Ressourcen, nur anhängen wenn vorhanden (vermeidet Build-Fehler)
def maybe(path, dest):
    return (here(path), dest) if os.path.exists(path) else None

datas_list = list(filter(None, [
    maybe('style.qss', '.'),
    maybe('INAT SOLUTIONS.png', '.'),
    maybe('config.json', '.'),
    maybe('schema.sql', '.'),
    maybe(os.path.join('config','rechnung_layout.json'), os.path.join('config')),
    maybe('favicon.ico', '.'),
    (here('icons'), 'icons'),   # <-- zwingend das icons-Verzeichnis einfügen
]))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        'PyQt5.sip','PyQt5.QtPrintSupport',
        'reportlab.lib.utils','reportlab.pdfgen','reportlab.graphics.renderPM',
        'PIL.Image','packaging','swissqr'
    ],
    hookspath=[],
    runtime_hooks=[here('pyi_rescopy.py')],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='INAT-Solutions',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='favicon.ico',          # <- EXE-Icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='INAT-Solutions'
)
