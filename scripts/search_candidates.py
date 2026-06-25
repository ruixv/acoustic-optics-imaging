#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/update_candidates.py for scheduled runs."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("update_candidates.py")), run_name="__main__")
