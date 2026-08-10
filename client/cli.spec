# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ecoclock-cli (Linux x86_64). Empaqueta solo la CLI (client/cli.py) + requests. Excluye explícitamente tkinter/PyQt/PySide para no inflar el binario."""
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
	['cli.py'],
	pathex=['.'],
	binaries=[],
	datas=[],
	hiddenimports=collect_submodules('requests'),
	hookspath=[],
	runtime_hooks=[],
	excludes=[
		'tkinter',
		'unittest',
		'pydoc',
		'doctest',
		'PyQt6',
		'PyQt5',
		'PySide6',
		'test',
		'tests',
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
	a.binaries,
	a.zipfiles,
	a.datas,
	[],
	name='ecoclock-cli',
	debug=False,
	bootloader_ignore_signals=False,
	strip=True,
	upx=False,
	upx_exclude=[],
	runtime_tmpdir=None,
	console=True,
	disable_windowed_redirector=False,
	target_arch=None,
	codesign_identity=None,
	entitlements_file=None,
)
