"""Entrypoint for CLI and menubar app."""

from __future__ import annotations

import argparse

from macbook_power.app import MacBookPowerApp
from macbook_power.battery import BatteryReadError, read_battery_sample
from macbook_power.eta import ChargeEstimator, format_duration, format_speed


def _run_once() -> int:
    try:
        sample = read_battery_sample()
    except BatteryReadError as error:
        print(f"Error reading battery: {error}")
        return 1

    estimator = ChargeEstimator()
    metrics = estimator.update(sample)

    print(f"Percent: {sample.percent:.2f}%")
    print(f"Charging: {sample.is_charging}")
    print(f"Power: {sample.power_w:.2f} W")
    print(f"Speed: {format_speed(metrics.charge_speed_percent_per_hour)}")
    print(f"ETA: {format_duration(metrics.eta_seconds_to_full)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MacBook charge speed and ETA widget")
    parser.add_argument("--once", action="store_true", help="Print one battery sample and exit")
    args = parser.parse_args()

    if args.once:
        return _run_once()

    app = MacBookPowerApp()
    app.run_with_timer()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
