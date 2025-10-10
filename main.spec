# main.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('style.qss', '.'),
        ('config.json', '.'),
        ('schema.sql', '.'),
        ('config\\rechnung_layout.json', 'config'),
        ('INAT SOLUTIONS.png', '.'),   # Splash/Logo
        ('favicon.ico', '.'),          # App-Icon (falls vorhanden)
    ],
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtPrintSupport',
        'reportlab.lib.utils',
        'reportlab.pdfgen',
        'reportlab.graphics.renderPM',
        'PIL.Image',
        'psycopg2', 'psycopg2._psycopg',  # nur relevant, wenn PG genutzt wird
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
    icon='favicon.ico',  # falls Datei fehlt, entferne diese Zeile oder füge die Datei hinzu
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
