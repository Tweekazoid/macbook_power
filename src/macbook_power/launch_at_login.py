"""Manage the macOS LaunchAgent that auto-starts the widget on login."""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

LAUNCH_AGENT_LABEL = "com.github.tweekazoid.macbook-power"


def _launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def launch_agent_plist_path() -> Path:
    return _launch_agents_dir() / f"{LAUNCH_AGENT_LABEL}.plist"


def _resolve_app_bundle_path() -> Path | None:
    """Return the path to the current .app bundle, or None when running from source."""
    exe = Path(sys.executable).resolve()
    for parent in [exe, *exe.parents]:
        if parent.suffix == ".app":
            return parent
    # Also check __file__ path (py2app sometimes puts python in Resources/)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.suffix == ".app":
            return parent
    return None


def _build_program_arguments() -> list[str] | None:
    """Return the ProgramArguments list for the LaunchAgent, or None if unsupported."""
    bundle = _resolve_app_bundle_path()
    if bundle is None:
        return None
    # The .app's main executable lives in Contents/MacOS/<name>
    macos_dir = bundle / "Contents" / "MacOS"
    if not macos_dir.is_dir():
        return None
    # py2app uses the app name (spaces and all) as the executable name
    candidates = [p for p in macos_dir.iterdir() if p.is_file() and p.stat().st_mode & 0o111]
    if not candidates:
        return None
    # Prefer the one matching the bundle name
    bundle_stem = bundle.stem
    for candidate in candidates:
        if candidate.name == bundle_stem:
            return [str(candidate)]
    return [str(candidates[0])]


def is_launch_at_login_supported() -> bool:
    return _build_program_arguments() is not None


def is_launch_at_login_enabled() -> bool:
    return launch_agent_plist_path().exists()


def enable_launch_at_login() -> tuple[bool, str]:
    """Install the LaunchAgent plist and load it. Returns (success, message)."""
    args = _build_program_arguments()
    if args is None:
        return False, "Launch at login only works when running from the installed .app"

    plist_path = launch_agent_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": args,
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
    }
    try:
        with plist_path.open("wb") as fp:
            plistlib.dump(payload, fp)
    except OSError as error:
        return False, f"Could not write plist: {error}"

    # Try to load it now so it takes effect without a logout/login
    subprocess.run(
        ["launchctl", "unload", str(plist_path)],
        check=False,
        capture_output=True,
    )
    result = subprocess.run(
        ["launchctl", "load", str(plist_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Not fatal — the agent will still be loaded at next login
        return True, f"Enabled (will activate at next login): {result.stderr.strip()}"
    return True, "Enabled"


def disable_launch_at_login() -> tuple[bool, str]:
    plist_path = launch_agent_plist_path()
    if plist_path.exists():
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            check=False,
            capture_output=True,
        )
        try:
            plist_path.unlink()
        except OSError as error:
            return False, f"Could not remove plist: {error}"
    return True, "Disabled"
