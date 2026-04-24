from __future__ import annotations

from datetime import datetime

from macbook_power.battery import parse_ioreg_payload


def test_parse_ioreg_payload() -> None:
    payload = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<array>
  <dict>
    <key>CurrentCapacity</key>
    <integer>3500</integer>
    <key>MaxCapacity</key>
    <integer>7000</integer>
    <key>Amperage</key>
    <integer>-1800</integer>
    <key>Voltage</key>
    <integer>12000</integer>
    <key>Temperature</key>
    <integer>3011</integer>
    <key>IsCharging</key>
    <true/>
    <key>FullyCharged</key>
    <false/>
    <key>ExternalConnected</key>
    <true/>
  </dict>
</array>
</plist>
"""

    now = datetime(2026, 4, 24, 10, 0, 0)
    sample = parse_ioreg_payload(payload, now=now)

    assert sample.timestamp == now
    assert sample.percent == 50.0
    assert sample.power_w == 21.6
    assert round(sample.battery_temperature_c or 0.0, 2) == 27.95
    assert sample.is_charging is True
    assert sample.external_connected is True
