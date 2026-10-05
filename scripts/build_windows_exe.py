#!/usr/bin/env python3
"""
AcoustiGap Windows Executable Build Script
Compiles the standalone Windows application using PyInstaller and packages it into a release ZIP.
"""

import os
import shutil
import subprocess
import sys
import zipfile

def build():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)

    print("=" * 60)
    print("AcoustiGap — Building Standalone Windows Executable")
    print("=" * 60)

    spec_file = os.path.join(root_dir, "AcoustiGap.spec")
    if not os.path.exists(spec_file):
        print(f"Error: Spec file not found at {spec_file}")
        sys.exit(1)

    print(f"[*] Running PyInstaller with spec: {spec_file}...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file]
    result = subprocess.run(cmd, cwd=root_dir)
    if result.returncode != 0:
        print("[!] PyInstaller build failed!")
        sys.exit(result.returncode)

    dist_dir = os.path.join(root_dir, "dist", "AcoustiGap")
    exe_path = os.path.join(dist_dir, "AcoustiGap.exe")
    if not os.path.exists(exe_path):
        print(f"[!] Executable not found at {exe_path}")
        sys.exit(1)

    exe_size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"[OK] Built successfully: {exe_path} ({exe_size_mb:.2f} MB)")

    # Create release ZIP archive
    zip_path = os.path.join(root_dir, "dist", "AcoustiGap-Windows-x64.zip")
    print(f"[*] Packaging release ZIP: {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, os.path.dirname(dist_dir))
                zf.write(full_path, rel_path)

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[OK] Release ZIP created: {zip_path} ({zip_size_mb:.2f} MB)")
    print("=" * 60)
    print("BUILD COMPLETE! You can run or distribute dist/AcoustiGap-Windows-x64.zip")
    print("=" * 60)

if __name__ == "__main__":
    build()
