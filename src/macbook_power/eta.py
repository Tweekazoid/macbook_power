"""Charge speed and ETA estimation logic."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import timedelta

from macbook_power.battery import BatterySample


@dataclass
class ChargeMetrics:
    """Computed metrics shown by the widget."""

    charge_speed_percent_per_hour: float | None
    eta_seconds_to_full: float | None


class ChargeEstimator:
    """Estimate charge speed and time-to-full from live samples."""

    def __init__(self, history_size: int = 20) -> None:
        self._history: deque[BatterySample] = deque(maxlen=history_size)
        self._last_is_charging: bool | None = None

    def update(self, sample: BatterySample) -> ChargeMetrics:
        if self._last_is_charging is None:
            self._last_is_charging = sample.is_charging
        elif self._last_is_charging != sample.is_charging:
            # Avoid stale trend estimates when power source changes.
            self._history.clear()
            self._last_is_charging = sample.is_charging

        self._history.append(sample)
        speed = self._estimate_speed(sample)
        eta = self._estimate_eta(sample)
        return ChargeMetrics(charge_speed_percent_per_hour=speed, eta_seconds_to_full=eta)

    def _estimate_speed(self, sample: BatterySample) -> float | None:
        if sample.is_fully_charged or sample.percent >= 100.0:
            return 0.0
        if not sample.is_charging:
            return None

        amperage_speed = self._speed_from_amperage(sample)
        if amperage_speed is not None:
            return amperage_speed

        return self._speed_from_trend()

    def _estimate_eta(self, sample: BatterySample) -> float | None:
        if sample.is_fully_charged or sample.percent >= 100.0:
            return 0.0
        if not sample.is_charging:
            return None

        eta_from_amperage = self._eta_from_amperage(sample)
        if eta_from_amperage is not None:
            return eta_from_amperage

        speed = self._speed_from_trend()
        if speed is None or speed <= 0:
            return None

        remaining_percent = max(0.0, 100.0 - sample.percent)
        return (remaining_percent / speed) * 3600.0

    @staticmethod
    def _speed_from_amperage(sample: BatterySample) -> float | None:
        if not sample.is_charging:
            return None
        if sample.max_capacity_mah <= 0:
            return None
        if sample.amperage_ma == 0:
            return None

        return abs(sample.amperage_ma) / sample.max_capacity_mah * 100.0

    @staticmethod
    def _eta_from_amperage(sample: BatterySample) -> float | None:
        if not sample.is_charging:
            return None

        remaining_mah = sample.max_capacity_mah - sample.current_capacity_mah
        if remaining_mah <= 0:
            return 0.0

        charge_ma = abs(sample.amperage_ma)
        if charge_ma <= 0:
            return None

        return remaining_mah / charge_ma * 3600.0

    def _speed_from_trend(self) -> float | None:
        if len(self._history) < 2:
            return None

        first = self._history[0]
        last = self._history[-1]

        delta_seconds = (last.timestamp - first.timestamp).total_seconds()
        if delta_seconds < 60:
            return None

        delta_percent = last.percent - first.percent
        if delta_percent <= 0:
            return None

        return (delta_percent / delta_seconds) * 3600.0


def format_duration(seconds: float | None) -> str:
    """Format duration as compact human-readable string."""
    if seconds is None:
        return "--"
    if seconds <= 0:
        return "0m"

    rounded = int(round(seconds))
    hours, rem = divmod(rounded, 3600)
    minutes, _ = divmod(rem, 60)

    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def format_speed(speed_percent_per_hour: float | None) -> str:
    """Format charge speed percentage per hour."""
    if speed_percent_per_hour is None:
        return "--"
    return f"{speed_percent_per_hour:.1f}%/h"


def format_timedelta(delta: timedelta) -> str:
    """Convert timedelta to compact string, mostly useful for debugging output."""
    return format_duration(delta.total_seconds())
