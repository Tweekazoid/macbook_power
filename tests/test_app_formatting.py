from macbook_power.app import _format_temperature, _metric_text


def test_format_temperature_celsius_and_fahrenheit() -> None:
    assert _format_temperature(None) == "--"
    assert _format_temperature(25.0) == "25.0C"
    assert _format_temperature(25.0, use_fahrenheit=True) == "77.0F"


def test_metric_text_with_and_without_icons() -> None:
    assert _metric_text("7.1W", "🔌", True, label="PWR") == "🔌7.1W"
    assert _metric_text("7.1W", "🔌", False, label="PWR") == "PWR:7.1W"
