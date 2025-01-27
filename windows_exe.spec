# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from dwg_converter import __version__

if os.name == "nt":
    script_path = "dwg_converter\\__main__.py"

else:
    script_path = "dwg_converter/__main__.py"

from PyInstaller.utils.hooks import collect_all
tz_datas, tz_binaries, tz_hiddenimports = collect_all("tzdata")

a = Analysis(
    [script_path],
    binaries=tz_binaries,
    datas=[*tz_datas],
    hiddenimports=tz_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"dwg-converter-{__version__}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon="logo.ico",
)
