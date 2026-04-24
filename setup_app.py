"""py2app build configuration for the MacBook Power menubar app.

Build the .app bundle with::

    python -m pip install -e ".[mac]"
    python setup_app.py py2app

The wheel/sdist packaging is handled by ``pyproject.toml`` via setuptools; this
file exists solely because py2app still relies on a classic ``setup.py``.
"""

from __future__ import annotations

import pathlib
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - 3.9/3.10 fallback
    import tomli as tomllib  # type: ignore[import-not-found]

from setuptools import setup

ROOT = pathlib.Path(__file__).resolve().parent
_PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())
_PROJECT = _PYPROJECT["project"]

APP_NAME = "MacBook Power"
APP_ENTRY = "src/macbook_power/main.py"
VERSION = _PROJECT["version"]

ICON_FILE = ROOT / "assets" / "branding" / "logo-mark.icns"
ICONS_DIR = ROOT / "assets" / "icons"

# Files/folders to ship inside the .app's Resources
DATA_FILES = []
if ICONS_DIR.exists():
    DATA_FILES.append(
        (
            "assets/icons",
            [str(p) for p in ICONS_DIR.iterdir() if p.is_file()],
        )
    )

PLIST = {
    "CFBundleName": APP_NAME,
    "CFBundleDisplayName": APP_NAME,
    "CFBundleIdentifier": "com.tweekazoid.macbookpower",
    "CFBundleVersion": VERSION,
    "CFBundleShortVersionString": VERSION,
    "NSHumanReadableCopyright": "© 2026 Michal Hons",
    # Hide from Dock / Cmd-Tab — this is a menubar-only app.
    "LSUIElement": True,
    "LSMinimumSystemVersion": "12.0",
    "NSHighResolutionCapable": True,
}

OPTIONS = {
    "argv_emulation": False,
    "plist": PLIST,
    "packages": ["rumps", "macbook_power"],
    "includes": ["pkg_resources"],
    "excludes": ["tkinter", "pytest", "ruff"],
    "iconfile": str(ICON_FILE) if ICON_FILE.exists() else None,
    # Use system Python frameworks when available to keep the bundle small.
    "semi_standalone": False,
    "site_packages": True,
}


# py2app rejects any truthy `install_requires` on the Distribution. Setuptools
# auto-populates it from pyproject.toml's `[project].dependencies` during
# `finalize_options`, overriding any kwarg we pass to `setup()`. Subclass the
# py2app command so it wipes the field just before it runs.
from py2app.build_app import py2app as _py2app_cmd  # noqa: E402


class py2app(_py2app_cmd):
    def finalize_options(self):  # type: ignore[override]
        self.distribution.install_requires = []
        super().finalize_options()


setup(
    name=APP_NAME,
    app=[APP_ENTRY],
    version=VERSION,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    install_requires=[],
    cmdclass={"py2app": py2app},
)
