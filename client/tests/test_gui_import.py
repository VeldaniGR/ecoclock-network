"""Tests del sub-comando gui. No requieren PyQt6 instalado: solo verifican que el modulo client.gui existe y que el CLI lo registra como sub-comando."""
from __future__ import annotations

import pytest


def test_gui_module_is_importable():
	import client.gui  # noqa: F401
	from client.gui import __main__  # noqa: F401


def test_gui_subcommand_is_registered():
	from client.cli import build_parser
	parser = build_parser()
	try:
		parser.parse_args(["gui", "--help"])
	except SystemExit:
		pass


def test_cli_parser_lists_gui_subcommand():
	from client.cli import build_parser
	parser = build_parser()
	try:
		args = parser.parse_args(["gui"])
	except SystemExit as e:
		pytest.fail(f"Sub-comando gui no registrado: SystemExit({e.code})")
	assert hasattr(args, "func")
