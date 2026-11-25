# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


hiddenimports = (
    collect_submodules("telegram")
    + collect_submodules("telegram.ext")
    + collect_submodules("campus_guard")
    + collect_submodules("webview")
    + collect_submodules("pystray")
)

a = Analysis(
    ["campus_guard.pyw"],
    pathex=[],
    binaries=[],
    datas=[
        ("data/universities.json", "data"),
        ("config.example.json", "."),
        ("campus_guard/web_dist", "campus_guard/web_dist"),
        ("assets", "assets"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["scripts/rthook_ssl_compat.py"],
    excludes=["PyQt6", "PyQt5", "PySide6", "tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AutoCampusNet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/app_icon.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AutoCampusNet",
)
