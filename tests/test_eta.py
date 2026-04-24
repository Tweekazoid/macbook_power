from __future__ import annotations

from datetime import datetime, timedelta

from macbook_power.battery import BatterySample
from macbook_power.eta import ChargeEstimator, format_duration


def _sample(
    *,
    percent: float,
    current: int,
    max_capacity: int,
    amperage: int,
    is_charging: bool,
    ts: datetime,
) -> BatterySample:
    return BatterySample(
        timestamp=ts,
        percent=percent,
        current_capacity_mah=current,
        max_capacity_mah=max_capacity,
        amperage_ma=amperage,
        voltage_mv=12000,
        is_charging=is_charging,
        is_fully_charged=False,
        external_connected=True,
    )


def test_eta_from_amperage() -> None:
    estimator = ChargeEstimator()
    now = datetime(2026, 1, 1, 12, 0, 0)
    sample = _sample(
        percent=50.0,
        current=3000,
        max_capacity=6000,
        amperage=-2000,
        is_charging=True,
        ts=now,
    )

    metrics = estimator.update(sample)

    assert metrics.eta_seconds_to_full is not None
    assert round(metrics.eta_seconds_to_full) == 5400


def test_fallback_trend_when_amperage_unavailable() -> None:
    estimator = ChargeEstimator()
    t0 = datetime(2026, 1, 1, 12, 0, 0)
    t1 = t0 + timedelta(minutes=30)

    estimator.update(
        _sample(
            percent=40.0,
            current=2400,
            max_capacity=6000,
            amperage=0,
            is_charging=True,
            ts=t0,
        )
    )
    metrics = estimator.update(
        _sample(
            percent=45.0,
            current=2700,
            max_capacity=6000,
            amperage=0,
            is_charging=True,
            ts=t1,
        )
    )

    assert metrics.charge_speed_percent_per_hour is not None
    assert round(metrics.charge_speed_percent_per_hour, 2) == 10.0
    assert metrics.eta_seconds_to_full is not None
    assert round(metrics.eta_seconds_to_full) == 19800


def test_format_duration() -> None:
    assert format_duration(None) == "--"
    assert format_duration(0) == "0m"
    assert format_duration(65) == "1m"
    assert format_duration(3660) == "1h 01m"


def test_unplugging_clears_charging_estimates() -> None:
    estimator = ChargeEstimator()
    now = datetime(2026, 1, 1, 12, 0, 0)

    charging = _sample(
        percent=82.0,
        current=4920,
        max_capacity=6000,
        amperage=2200,
        is_charging=True,
        ts=now,
    )
    unplugged = _sample(
        percent=81.8,
        current=4908,
        max_capacity=6000,
        amperage=-900,
        is_charging=False,
        ts=now + timedelta(seconds=30),
    )

    estimator.update(charging)
    metrics = estimator.update(unplugged)

    assert metrics.charge_speed_percent_per_hour is None
    assert metrics.eta_seconds_to_full is None


def test_plugged_not_charging_has_no_charge_estimates() -> None:
    estimator = ChargeEstimator()
    now = datetime(2026, 1, 1, 13, 0, 0)

    plugged_idle = _sample(
        percent=80.0,
        current=4800,
        max_capacity=6000,
        amperage=0,
        is_charging=False,
        ts=now,
    )

    metrics = estimator.update(plugged_idle)

    assert metrics.charge_speed_percent_per_hour is None
    assert metrics.eta_seconds_to_full is None
