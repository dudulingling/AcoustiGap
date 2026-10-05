#!/usr/bin/env python3
"""
AcoustiGap Main Executable Launcher
Launches AcoustiGap Desktop GUI by default, or runs CLI subcommands if arguments are passed.
Safely handles GUI/windowed mode where sys.stdout/sys.stderr can be None.
"""
import sys
import os

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Prevent NoneType write errors in PyInstaller windowed mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        # Default action when double-clicked: launch Desktop GUI
        from acoustigap.gui.app import launch_gui
        launch_gui()
    else:
        from acoustigap.cli.main import cli
        cli()
