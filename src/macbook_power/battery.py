"""Battery telemetry collection from macOS ioreg."""

from __future__ import annotations

import plistlib
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class BatterySample:
    """Normalized battery sample extracted from AppleSmartBattery data."""

    timestamp: datetime
    percent: float
    current_capacity_mah: int
    max_capacity_mah: int
    amperage_ma: int
    voltage_mv: int
    is_charging: bool
    is_fully_charged: bool
    external_connected: bool
    battery_temperature_c: float | None = None
    system_power_in_mw: int | None = None

    @property
    def battery_power_w(self) -> float:
        """Battery charge/discharge power in watts (0 when full & plugged in)."""
        if self.amperage_ma == 0 or self.voltage_mv == 0:
            return 0.0
        return abs(self.amperage_ma * self.voltage_mv) / 1_000_000

    @property
    def power_w(self) -> float:
        """Real system power draw in watts.

        Prefers ``PowerTelemetryData.SystemPowerIn`` (the actual draw from the
        adapter, in mW) which is non-zero even when the battery is full.
        Falls back to battery charge/discharge power when telemetry is absent.
        """
        if self.system_power_in_mw is not None and self.system_power_in_mw > 0:
            return self.system_power_in_mw / 1000.0
        return self.battery_power_w


class BatteryReadError(RuntimeError):
    """Raised when battery telemetry cannot be read."""


def _read_ioreg_plist() -> bytes:
    result = subprocess.run(
        ["ioreg", "-r", "-n", "AppleSmartBattery", "-a"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise BatteryReadError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def _as_bool(payload: dict[str, Any], key: str) -> bool:
    return bool(payload.get(key, False))


def _as_int(payload: dict[str, Any], key: str) -> int:
    raw = payload.get(key, 0)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _normalize_temperature_c(raw_temp: int) -> float | None:
    """Normalize AppleSmartBattery temperature value to Celsius."""
    if raw_temp <= 0:
        return None

    # Most AppleSmartBattery readings are tenths of Kelvin.
    if raw_temp > 2000:
        return (raw_temp / 10.0) - 273.15

    # Fallback: assume centi-Celsius when values are smaller.
    return raw_temp / 100.0


def parse_ioreg_payload(raw_payload: bytes, now: datetime | None = None) -> BatterySample:
    """Parse `ioreg -a` plist output into a BatterySample."""
    decoded = plistlib.loads(raw_payload)
    if not isinstance(decoded, list) or not decoded:
        raise BatteryReadError("AppleSmartBattery payload is empty")

    payload = decoded[0]
    if not isinstance(payload, dict):
        raise BatteryReadError("AppleSmartBattery payload has unexpected format")

    current_capacity = _as_int(payload, "CurrentCapacity")
    max_capacity = _as_int(payload, "MaxCapacity")
    raw_current_capacity = _as_int(payload, "AppleRawCurrentCapacity")
    raw_max_capacity = _as_int(payload, "AppleRawMaxCapacity")

    normalized_current_capacity = (
        raw_current_capacity if raw_current_capacity > 0 else current_capacity
    )
    normalized_max_capacity = raw_max_capacity if raw_max_capacity > 0 else max_capacity
    amperage = _as_int(payload, "Amperage")
    voltage = _as_int(payload, "Voltage")
    battery_temperature_c = _normalize_temperature_c(_as_int(payload, "Temperature"))

    telemetry = payload.get("PowerTelemetryData")
    system_power_in_mw: int | None = None
    if isinstance(telemetry, dict):
        raw = telemetry.get("SystemPowerIn")
        try:
            system_power_in_mw = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            system_power_in_mw = None

    if normalized_max_capacity <= 0:
        raise BatteryReadError("Battery max capacity is unavailable")

    timestamp = now or datetime.now()
    if 0 < max_capacity <= 100:
        percent = max(0.0, min(100.0, (current_capacity / max_capacity) * 100.0))
    else:
        percent = max(
            0.0,
            min(100.0, (normalized_current_capacity / normalized_max_capacity) * 100.0),
        )

    return BatterySample(
        timestamp=timestamp,
        percent=percent,
        current_capacity_mah=normalized_current_capacity,
        max_capacity_mah=normalized_max_capacity,
        amperage_ma=amperage,
        voltage_mv=voltage,
        is_charging=_as_bool(payload, "IsCharging"),
        is_fully_charged=_as_bool(payload, "FullyCharged"),
        external_connected=_as_bool(payload, "ExternalConnected"),
        battery_temperature_c=battery_temperature_c,
        system_power_in_mw=system_power_in_mw,
    )


def read_battery_sample(now: datetime | None = None) -> BatterySample:
    """Read and parse the current battery telemetry from macOS."""
    return parse_ioreg_payload(_read_ioreg_plist(), now=now)
