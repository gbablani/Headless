"""Build script to produce runner.exe using PyInstaller.

Usage:
    python build.py

Requires:
    pip install pyinstaller playwright
    playwright install chromium
"""

import subprocess
import sys


def main():
    print("=== Building runner.exe with PyInstaller ===")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "runner.spec",
        "--clean",
        "--noconfirm",
    ]
    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print("\nBuild successful!  Binary at: dist/runner.exe")
        print(
            "\nNOTE: Playwright browsers are NOT bundled. The user must run:\n"
            "  playwright install chromium\n"
            "Or set PLAYWRIGHT_BROWSERS_PATH to an existing installation."
        )
    else:
        print("\nBuild failed.", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
