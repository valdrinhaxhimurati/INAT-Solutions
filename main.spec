# main.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('style.qss', '.'),
        ('INAT SOLUTIONS.png', '.'),
        ('config.json', '.'),
        ('schema.sql', '.'),
        # Entferne diese Zeile, falls Datei/Ordner nicht existiert:
        # ('config\\rechnung_layout.json', 'config'),
        ('icons', 'icons'),
        ('gui', 'gui'),           # optional; kann bleiben
        ('db', 'db'),
        ('rechnungen', 'rechnungen'),
        ('swissqr', 'swissqr'),
        # Falls du buchhaltung.csv zur Laufzeit lädst:
        # ('buchhaltung.csv', '.'),
    ],
    hiddenimports=[
        'PyQt5.sip','PyQt5.QtPrintSupport','PyQt5.QtSvg','PyQt5.QtGui','PyQt5.QtCore','PyQt5.QtWidgets',
        'reportlab.pdfgen','reportlab.lib.utils','reportlab.graphics.renderPM','reportlab.graphics.renderPDF',
        'svglib.svglib','PIL.Image','packaging','swissqr',
        'cairosvg','lxml',
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
    name='INAT_Solutions',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='INAT_Solutions'
)
