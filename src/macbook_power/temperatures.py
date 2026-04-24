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
import platform
import re
import shutil
import subprocess
import time

_CPU_TEMP_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*°?\s*([CF])?", re.IGNORECASE)

_IS_APPLE_SILICON = platform.machine() == "arm64"

# Preferred install target. smctemp works on both Apple Silicon and Intel.
_DEFAULT_INSTALL_TOOL = "smctemp"
_DEFAULT_INSTALL_FORMULA = "narugit/tap/smctemp"

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


def is_brew_available() -> bool:
    """Check if Homebrew is installed."""
    return shutil.which("brew") is not None


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
    if not is_brew_available():
        return False, "Homebrew not found. Install from https://brew.sh"

    formula = (
        _DEFAULT_INSTALL_FORMULA if tool_name == _DEFAULT_INSTALL_TOOL else tool_name
    )

    # smctemp lives in a custom tap; make sure it's added first.
    if tool_name == _DEFAULT_INSTALL_TOOL:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(
                ["brew", "tap", "narugit/tap"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30.0,
            )

    try:
        result = subprocess.run(
            ["brew", "install", formula],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if result.returncode != 0:
            return False, f"Installation failed: {result.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        return False, f"Installation timed out after {timeout_seconds}s"
    except Exception as e:  # noqa: BLE001
        return False, f"Installation error: {e}"

    if read_cpu_temperature_c() is None:
        return False, f"Installed {tool_name} but no valid reading yet"
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
        if shutil.which(command[0]) is None:
            continue
        try:
            result = subprocess.run(
                command,
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
