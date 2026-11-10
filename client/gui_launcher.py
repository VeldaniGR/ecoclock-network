#!/usr/bin/env python3
"""Lanzador absoluto para PyInstaller (evita relative import issues)."""
from client.gui.app import main
import sys

if __name__ == "__main__":
    sys.exit(main())
