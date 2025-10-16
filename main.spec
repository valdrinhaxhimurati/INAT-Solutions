# main.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],  # PyInstaller sammelt benötigte Qt-DLLs selbst
    datas=[
        ('style.qss', '.'),                       # Stylesheet neben EXE
        ('INAT SOLUTIONS.png', '.'),              # Splash-Bild neben EXE
        ('config.json', '.'),                     # Default-Konfig
        ('schema.sql', '.'),                      # DB-Schema
        ('config\\rechnung_layout.json', 'config'),
        # Optional: nur eintragen, wenn vorhanden
        # ('favicon.ico', '.'),
    ],
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtPrintSupport',
        'reportlab.lib.utils',
        'reportlab.pdfgen',
        'reportlab.graphics.renderPM',
        'PIL.Image',
        'packaging',
        'swissqr',
        # Falls du PG nutzt und installiert hast:
        # 'psycopg2', 'psycopg2._psycopg',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='INAT Solutions',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    # icon='favicon.ico',  # aktivieren, wenn die Datei existiert
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
