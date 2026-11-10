# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ecoclock-gui (Linux + Windows).
Modo onedir (recomendado) + windowed (sin consola).
Incluye PyQt6, assets (theme.qss + logo.svg) y todo el cliente necesario.
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import sys
from pathlib import Path

block_cipher = None

# Rutas relativas al directorio client/ (desde donde se ejecuta pyinstaller)
gui_dir = Path('.')
assets_dir = gui_dir / 'gui' / 'assets'

# Datos a empaquetar (theme + logo)
datas = [
    ('gui/theme.qss', 'client/gui'),           # se busca relativo al entry
    ('gui/assets/logo.svg', 'client/gui/assets'),
]

# Si quieres incluir también el icono de Windows (opcional pero recomendado)
# datas.append(('../packaging/windows/ecoclock.ico', '.'))

# Hidden imports importantes
hiddenimports = (
    collect_submodules('PyQt6')
    + collect_submodules('client')
    + [
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'requests',
        'client.cli',
        'client.worker',          # por si el auto_worker lo usa
        'client.gui.services',
        'client.gui.auto_worker',
        'client.gui.leaf_widget',
        'client.gui.sonar_widget',
        'client.gui.toggle_switch',
        'client.gui.nodes_page',
        'client.gui.i18n',        # aunque aún no esté commiteado, lo dejamos listo
    ]
)

a = Analysis(
    ['gui_launcher.py'],          # entry point limpio
    pathex=['.'],                 # ejecuta pyinstaller desde client/
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'matplotlib',
        'numpy.testing',
        'IPython',
        'jupyter',
    ],
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
    exclude_binaries=True,        # onedir
    name='ecoclock-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,                  # mejor False en Windows para evitar problemas
    upx=False,
    console=False,                # ← CLAVE: sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../packaging/windows/ecoclock.ico' if sys.platform.startswith('win') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ecoclock-gui',
)
