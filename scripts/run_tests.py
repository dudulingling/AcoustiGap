#!/usr/bin/env python3
"""
AcoustiGap Automated Test Runner
Executes all unit, integration, and DSP loopback test suites.
"""

import os
import subprocess
import sys

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_script = os.path.join(root_dir, "tests", "run_all_tests.py")

    print(f"[*] Running AcoustiGap Test Suites: {test_script}")
    result = subprocess.run([sys.executable, test_script], cwd=root_dir)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
