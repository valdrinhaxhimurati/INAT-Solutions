# main.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],  # ggf. Pfad anpassen
    binaries=[],
    datas=[
        ('favicon.ico', '.'),
        ('INAT SOLUTIONS.png', '.'),
        ('style.qss', '.'),
        ('gui/*', 'gui'),
        ('rechnungen/*', 'rechnungen'),
        ('swissqr/*', 'swissqr'),
        ('version.py', '.'),    
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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
    console=False,  # Wenn GUI, dann False, sonst True
    icon='favicon.ico',  # Icon für exe
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
