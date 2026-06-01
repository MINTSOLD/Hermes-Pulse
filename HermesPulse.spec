# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules

# Force-include all submodules of tricky packages whose imports are dynamic
# (pythonnet uses lazy import, pywebview imports differently per platform, etc.)
extra_hidden = []
for pkg in ['pythonnet', 'clr_loader', 'bottle', 'webview', 'webview.platforms',
            'wsgiref', 'http', 'xmlrpc', 'pydoc']:
    try:
        extra_hidden += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    ['hermes_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('config_server.py', '.'), ('index.html', '.'), ('styles.css', '.'), ('app.js', '.'), ('hermes-logo.png', '.'), ('hermes.ico', '.'), ('hermes-titlebar.ico', '.'), ('splash.html', '.')],
    hiddenimports=['uuid', 'wsgiref', 'wsgiref.simple_server', 'wsgiref.handlers', 'wsgiref.util', 'socketserver', 'http.server', 'http.client', 'http.cookies', 'configparser', 'ctypes.util', 'xmlrpc', 'xmlrpc.client', 'xmlrpc.server', 'pydoc', 'doctest', 'argparse', 'difflib', 'pdb', 'profile', 'cProfile', 'pyclbr', 'yaml', 'PIL._tkinter_finder', 'pystray'] + list(set(extra_hidden)),
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
    name='HermesPulse',
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
    icon=['hermes.ico'],
)
