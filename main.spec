# main.spec
# -*- mode: python ; coding: utf-8 -*-

import os
here = lambda p: os.path.abspath(p)

block_cipher = None

# Ressourcen, nur anhängen wenn vorhanden (vermeidet Build-Fehler)
def maybe(path, dest):
    return (here(path), dest) if os.path.exists(path) else None

datas_list = list(filter(None, [
    maybe('style.qss', '.'),                      # landet in _internal, Hook kopiert ins Root
    maybe('INAT SOLUTIONS.png', '.'),
    maybe('config.json', '.'),
    maybe('schema.sql', '.'),
    maybe(os.path.join('config','rechnung_layout.json'), os.path.join('config')),
    # maybe(os.path.join('config','qr_daten.json'), os.path.join('config')),
]))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],               # keine DLLs manuell – PyInstaller sammelt Qt selbst ein
    datas=datas_list,
    hiddenimports=[
        'PyQt5.sip','PyQt5.QtPrintSupport','PyQt5.QtSvg','PyQt5.QtGui','PyQt5.QtCore','PyQt5.QtWidgets',
        'reportlab.pdfgen','reportlab.lib.utils','reportlab.graphics.renderPM','reportlab.graphics.renderPDF',
        'svglib.svglib','PIL.Image','packaging','swissqr','cairosvg','lxml'
    ],
    hookspath=[],
    runtime_hooks=[here('pyi_rescopy.py')],   # <- unser Kopier-Hook
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='INAT_Solutions',      # ohne Leerzeichen
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    # icon='favicon.ico',        # nur wenn vorhanden
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='INAT Solutions'
)
