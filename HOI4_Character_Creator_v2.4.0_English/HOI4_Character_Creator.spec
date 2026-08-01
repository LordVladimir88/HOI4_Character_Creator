# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH)

datas = [
    (str(project_root / "assets"), "assets"),
    (str(project_root / "data"), "data"),
]

sources_dir = project_root / "sources"
if sources_dir.exists():
    datas.append((str(sources_dir), "sources"))

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HOI4 Character Creator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "logo.ico"),
)
