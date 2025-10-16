from cx_Freeze import setup, Executable

build_exe_options = {
    "includes": ["PyQt5.sip", "PyQt5.QtPrintSupport"],
    "packages": ["reportlab", "PIL", "packaging", "swissqr"],
    "include_files": [
        ("style.qss", "style.qss"),
        ("INAT SOLUTIONS.png", "INAT SOLUTIONS.png"),
        ("config.json", "config.json"),
        ("schema.sql", "schema.sql"),
        ("config/rechnung_layout.json", "config/rechnung_layout.json"),
        # ("favicon.ico", "favicon.ico"),  # falls vorhanden
    ],
    "optimize": 0,
    "include_msvcr": True,  # MSVC-Runtime mitgeben
}

setup(
    name="INAT Solutions",
    version="1.0.0",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base="Win32GUI", icon="favicon.ico")],
)