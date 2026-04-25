"""Temperature helpers for optional CPU telemetry.

CPU temperature reading on macOS requires third-party tools since the OS does
not expose CPU temperature through standard APIs without privileged access.

Supported tools (install via Homebrew):
  - smctemp (Apple Silicon + Intel): brew install narugit/tap/smctemp
  - osx-cpu-temp (Intel only): brew install osx-cpu-temp
  - istats (Intel only): brew install istats

On Apple Silicon (M1+), only ``smctemp`` reports real values; the other tools
return 0.0 because they rely on Intel-era SMC keys.

If no working tool is installed, CPU temperature will be unavailable
(shown as "--").
"""

from __future__ import annotations

import contextlib
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

_CPU_TEMP_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*°?\s*([CF])?", re.IGNORECASE)

_IS_APPLE_SILICON = platform.machine() == "arm64"

# Preferred install target. smctemp works on both Apple Silicon and Intel.
_DEFAULT_INSTALL_TOOL = "smctemp"
_DEFAULT_INSTALL_FORMULA = "narugit/tap/smctemp"

# Common Homebrew install locations. When the app is launched from
# ``/Applications`` via LaunchServices the PATH only contains ``/usr/bin``
# etc., so ``shutil.which('brew')`` returns None even though brew is
# installed. Probe these locations explicitly.
_BREW_PATHS = (
    "/opt/homebrew/bin/brew",  # Apple Silicon
    "/usr/local/bin/brew",  # Intel
    "/home/linuxbrew/.linuxbrew/bin/brew",
)

# Same problem applies to the temperature tools themselves. When PyInstaller-
# packaged apps run from /Applications, ``shutil.which`` only sees the
# sandboxed PATH. Search these dirs as a fallback.
_TOOL_SEARCH_DIRS = (
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
)


def _which(executable: str) -> str | None:
    """Locate ``executable``, falling back to common Homebrew dirs."""
    found = shutil.which(executable)
    if found:
        return found
    for directory in _TOOL_SEARCH_DIRS:
        candidate = os.path.join(directory, executable)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None

_INSTALL_LOG_PATH = Path.home() / "Library" / "Logs" / "macbook_power" / "install.log"


def _find_brew() -> str | None:
    """Locate the ``brew`` executable, including outside the app PATH."""
    found = shutil.which("brew")
    if found:
        return found
    for candidate in _BREW_PATHS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _brew_env() -> dict[str, str]:
    """Build an env dict that exposes Homebrew bin dirs on PATH."""
    env = os.environ.copy()
    extra = ["/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin"]
    current = env.get("PATH", "")
    parts = [p for p in extra if p not in current.split(os.pathsep)]
    if parts:
        env["PATH"] = os.pathsep.join([*parts, current]) if current else os.pathsep.join(parts)
    # ``HOME`` is required by brew when launched from a sandboxed context.
    env.setdefault("HOME", str(Path.home()))
    return env


def _log_install(message: str) -> None:
    """Append a line to the install log; never raises."""
    with contextlib.suppress(OSError):
        _INSTALL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _INSTALL_LOG_PATH.open("a", encoding="utf-8") as fp:
            fp.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

# Help text shown when CPU temp is unavailable
_INSTALL_HELP = (
    "CPU temperature requires an external tool. Install via Homebrew:\n"
    "  • smctemp (Apple Silicon + Intel): brew install narugit/tap/smctemp\n"
    "Then restart the app."
)


def _parse_temperature_output(output: str) -> float | None:
    match = _CPU_TEMP_RE.search(output)
    if not match:
        return None

    value = float(match.group(1))
    unit = (match.group(2) or "C").upper()
    if unit == "F":
        return (value - 32.0) * 5.0 / 9.0
    return value


def get_install_instructions() -> str:
    """Return installation instructions for CPU temperature tools."""
    return _INSTALL_HELP


def get_install_log_path() -> Path:
    """Return path of the install log file (may not exist yet)."""
    return _INSTALL_LOG_PATH


def is_brew_available() -> bool:
    """Check if Homebrew is installed."""
    return _find_brew() is not None


def is_cpu_temp_tool_available() -> bool:
    """Return True only if a tool produces a valid CPU temperature reading.

    Tools that return 0.0/NaN/errors (e.g. ``osx-cpu-temp`` on Apple Silicon)
    are treated as missing.
    """
    return read_cpu_temperature_c() is not None


def install_cpu_temp_tool(
    tool_name: str = _DEFAULT_INSTALL_TOOL, timeout_seconds: float = 120.0
) -> tuple[bool, str]:
    """Install a CPU temperature tool via Homebrew.

    Defaults to ``smctemp`` which works on Apple Silicon and Intel Macs.

    Returns:
        (success, message) tuple. ``success`` is True only if the tool is
        installed AND produces a valid reading afterwards.
    """
    brew = _find_brew()
    if brew is None:
        msg = (
            "Homebrew not found. Install from https://brew.sh, then "
            "restart the app."
        )
        _log_install(f"FAIL: {msg}")
        return False, msg

    formula = (
        _DEFAULT_INSTALL_FORMULA if tool_name == _DEFAULT_INSTALL_TOOL else tool_name
    )
    env = _brew_env()
    _log_install(f"START: brew={brew} formula={formula}")

    # smctemp lives in a custom tap; make sure it's added first.
    if tool_name == _DEFAULT_INSTALL_TOOL:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            tap_result = subprocess.run(
                [brew, "tap", "narugit/tap"],
                check=False,
                capture_output=True,
                text=True,
                timeout=60.0,
                env=env,
            )
            _log_install(
                f"tap rc={tap_result.returncode} "
                f"stdout={tap_result.stdout.strip()[:300]} "
                f"stderr={tap_result.stderr.strip()[:300]}"
            )

    try:
        result = subprocess.run(
            [brew, "install", formula],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
        _log_install(
            f"install rc={result.returncode} "
            f"stdout={result.stdout.strip()[-500:]} "
            f"stderr={result.stderr.strip()[-500:]}"
        )
        if result.returncode != 0:
            details = (result.stderr.strip() or result.stdout.strip())
            return False, f"brew install failed (exit {result.returncode}):\n{details}"
    except subprocess.TimeoutExpired:
        msg = f"Installation timed out after {timeout_seconds:.0f}s"
        _log_install(f"FAIL: {msg}")
        return False, msg
    except Exception as e:  # noqa: BLE001
        msg = f"Installation error: {e}"
        _log_install(f"FAIL: {msg}")
        return False, msg

    if read_cpu_temperature_c() is None:
        msg = (
            f"Installed {tool_name} but it returned no valid reading. "
            f"Try restarting the app."
        )
        _log_install(f"FAIL: {msg}")
        return False, msg
    _log_install(f"OK: {tool_name} installed and reading temperature")
    return True, f"Successfully installed {tool_name}"


def _is_valid_reading(value: float | None) -> bool:
    """Reject None, NaN, and the fake 0.0 returned by broken tools."""
    if value is None:
        return False
    if value != value:  # NaN
        return False
    # Real CPU temperature is always above 0 °C in practice.
    return value > 1.0


def read_cpu_temperature_c(timeout_seconds: float = 0.8) -> float | None:
    """Read CPU temperature in Celsius using best-effort local tools.

    Returns None if no working temperature tool is installed. On Apple Silicon
    only ``smctemp`` is trusted; ``osx-cpu-temp``/``istats`` return a fake 0.0.
    """
    commands: list[list[str]] = [
        # smctemp works on Apple Silicon and Intel.
        ["smctemp", "-c"],
    ]
    if not _IS_APPLE_SILICON:
        commands.extend(
            [
                ["osx-cpu-temp"],
                ["istats", "cpu", "temp", "--value-only"],
                ["istats", "cpu", "temp"],
            ]
        )

    for command in commands:
        executable = _which(command[0])
        if executable is None:
            continue
        try:
            result = subprocess.run(
                [executable, *command[1:]],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        if result.returncode != 0:
            continue

        parsed = _parse_temperature_output(result.stdout.strip())
        if _is_valid_reading(parsed):
            return parsed

    return None


class CpuTemperatureReader:
    """Cache CPU temperature reads to avoid expensive polling."""

    def __init__(self, cache_seconds: float = 15.0) -> None:
        self._cache_seconds = cache_seconds
        self._last_read_monotonic = 0.0
        self._last_value_c: float | None = None

    def read(self) -> float | None:
        now = time.monotonic()
        if now - self._last_read_monotonic < self._cache_seconds:
            return self._last_value_c

        self._last_value_c = read_cpu_temperature_c()
        self._last_read_monotonic = now
        return self._last_value_c
