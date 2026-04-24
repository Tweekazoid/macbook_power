"""Menubar widget application."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import rumps

from macbook_power import __version__
from macbook_power.battery import BatteryReadError, read_battery_sample
from macbook_power.eta import ChargeEstimator, format_duration, format_speed
from macbook_power.launch_at_login import (
    disable_launch_at_login,
    enable_launch_at_login,
    is_launch_at_login_enabled,
    is_launch_at_login_supported,
)
from macbook_power.temperatures import (
    CpuTemperatureReader,
    install_cpu_temp_tool,
    is_cpu_temp_tool_available,
)
from macbook_power.updater import (
    UpdateCheckError,
    download_dmg,
    fetch_latest_release,
    is_newer,
    open_path,
)


@dataclass
class DisplaySettings:
    """User-configurable title display options."""

    show_state: bool = True
    show_remaining_time: bool = True
    show_power_draw: bool = True
    show_battery_temperature: bool = False
    show_cpu_temperature: bool = False
    show_metric_icons: bool = True
    use_fahrenheit: bool = False


class MacBookPowerApp(rumps.App):
    """Simple macOS menubar app showing battery speed and ETA."""

    def __init__(self) -> None:
        icon_path = _menubar_icon_path()
        icon = str(icon_path) if icon_path.exists() else None
        super().__init__("Batt", quit_button="Quit", icon=icon, template=True)
        self._estimator = ChargeEstimator(history_size=24)
        self._cpu_temperature_reader = CpuTemperatureReader(cache_seconds=15.0)
        self._display_settings = _load_display_settings()
        refresh_seconds = _refresh_interval_seconds()

        self._status_item = rumps.MenuItem("Status: loading...")
        self._speed_item = rumps.MenuItem("Speed: --")
        self._eta_item = rumps.MenuItem("ETA: --")
        self._power_item = rumps.MenuItem("Power draw: --")
        self._battery_temp_item = rumps.MenuItem("Battery temp: --")
        self._cpu_temp_item = rumps.MenuItem("CPU temp: --")
        self._detail_item = rumps.MenuItem("Capacity: --")

        self._display_header_item = rumps.MenuItem("Display In Title")
        self._display_header_item.set_callback(lambda _: None)
        self._opt_show_state = rumps.MenuItem("⚡ Charge state")
        self._opt_show_remaining_time = rumps.MenuItem("⏳ Remaining time")
        self._opt_show_power_draw = rumps.MenuItem("🔌 Current power draw")
        self._opt_show_battery_temperature = rumps.MenuItem("🌡 Battery temperature")
        self._opt_show_cpu_temperature = rumps.MenuItem("🧠 CPU temperature")
        self._opt_show_metric_icons = rumps.MenuItem("✨ Per-metric icons")
        self._opt_use_fahrenheit = rumps.MenuItem("🌡 Use Fahrenheit (F)")

        self._install_cpu_tool_item = rumps.MenuItem(
            "⬇ Install CPU temperature tool"
        )
        self._install_cpu_tool_item.set_callback(self._install_cpu_temperature_tool)

        self._launch_at_login_item = rumps.MenuItem("🚀 Launch at Login")
        self._launch_at_login_item.set_callback(self._toggle_launch_at_login)

        self._check_updates_item = rumps.MenuItem("⬆ Check for Updates…")
        self._check_updates_item.set_callback(self._check_for_updates_clicked)

        self._updated_item = rumps.MenuItem("Updated: --")
        self.menu = [
            self._status_item,
            self._speed_item,
            self._eta_item,
            self._power_item,
            self._battery_temp_item,
            self._cpu_temp_item,
            self._detail_item,
            None,
            self._display_header_item,
            self._opt_show_state,
            self._opt_show_remaining_time,
            self._opt_show_power_draw,
            self._opt_show_battery_temperature,
            self._opt_show_cpu_temperature,
            self._opt_show_metric_icons,
            self._opt_use_fahrenheit,
            self._install_cpu_tool_item,
            None,
            self._launch_at_login_item,
            self._check_updates_item,
            None,
            self._updated_item,
        ]
        self._bind_display_toggle(
            item=self._opt_show_state,
            key="show_state",
            callback=self._toggle_show_state,
        )
        self._bind_display_toggle(
            item=self._opt_show_remaining_time,
            key="show_remaining_time",
            callback=self._toggle_show_remaining_time,
        )
        self._bind_display_toggle(
            item=self._opt_show_power_draw,
            key="show_power_draw",
            callback=self._toggle_show_power_draw,
        )
        self._bind_display_toggle(
            item=self._opt_show_battery_temperature,
            key="show_battery_temperature",
            callback=self._toggle_show_battery_temperature,
        )
        self._bind_display_toggle(
            item=self._opt_show_cpu_temperature,
            key="show_cpu_temperature",
            callback=self._toggle_show_cpu_temperature,
        )
        self._bind_display_toggle(
            item=self._opt_show_metric_icons,
            key="show_metric_icons",
            callback=self._toggle_show_metric_icons,
        )
        self._bind_display_toggle(
            item=self._opt_use_fahrenheit,
            key="use_fahrenheit",
            callback=self._toggle_use_fahrenheit,
        )

        self._timer = rumps.Timer(self._refresh, refresh_seconds)

    def run_with_timer(self) -> None:
        """Start polling before entering app loop."""
        self._refresh(None)
        self._timer.start()
        self._maybe_prompt_launch_at_login()
        self.run()

    def _maybe_prompt_launch_at_login(self) -> None:
        """On first run from an installed .app, ask whether to auto-start at login."""
        if not is_launch_at_login_supported():
            return
        flag = _first_run_flag_path()
        if flag.exists():
            return
        # Mark as asked even if they cancel — we only prompt once.
        try:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text("asked", encoding="utf-8")
        except OSError:
            pass

        if is_launch_at_login_enabled():
            return

        response = rumps.alert(
            title="Start MacBook Power at login?",
            message=(
                "Launch MacBook Power automatically when you log in, so the widget "
                "is always available in the menubar.\n\n"
                "You can change this anytime from the menu."
            ),
            ok="Enable",
            cancel="Not now",
        )
        if response == 1:
            success, message = enable_launch_at_login()
            if not success:
                rumps.alert(title="Launch at Login", message=message)
            self._update_install_button_visibility()

    def _refresh(self, _: object | None) -> None:
        try:
            sample = read_battery_sample()
        except BatteryReadError as error:
            self.title = "Batt ERR"
            self._status_item.title = f"Read error: {error}"
            self._speed_item.title = "Speed: --"
            self._eta_item.title = "ETA: --"
            self._power_item.title = "Power draw: --"
            self._battery_temp_item.title = "Battery temp: --"
            self._cpu_temp_item.title = "CPU temp: --"
            self._detail_item.title = "Capacity: unavailable"
            self._updated_item.title = f"Updated: {datetime.now().strftime('%H:%M:%S')}"
            self._update_install_button_visibility()
            return

        # Update install button visibility
        self._update_install_button_visibility()

        metrics = self._estimator.update(sample)

        eta_label = format_duration(metrics.eta_seconds_to_full)
        speed_label = format_speed(metrics.charge_speed_percent_per_hour)
        watts_label = f"{sample.power_w:.1f}W"

        if sample.is_fully_charged or sample.percent >= 100.0:
            state = "Full"
            state_short = "FULL"
        elif sample.is_charging:
            state = "Charging"
            state_short = "CHG"
        elif sample.external_connected:
            state = "Plugged"
            state_short = "AC"
        else:
            state = "On battery"
            state_short = "BAT"

        bar = _battery_bar(sample.percent)
        cpu_temp_c = (
            self._cpu_temperature_reader.read()
            if self._display_settings.show_cpu_temperature
            else None
        )
        self.title = self._compose_title(
            percent=sample.percent,
            state_short=state_short,
            eta_label=eta_label,
            power_w=sample.power_w,
            battery_temp_c=sample.battery_temperature_c,
            cpu_temp_c=cpu_temp_c,
        )

        battery_temp_label = _format_temperature(
            sample.battery_temperature_c,
            use_fahrenheit=self._display_settings.use_fahrenheit,
        )
        cpu_temp_label = _format_temperature(
            cpu_temp_c,
            use_fahrenheit=self._display_settings.use_fahrenheit,
        )

        self._status_item.title = f"Status: {state} {bar} ({sample.percent:.1f}%)"
        self._speed_item.title = f"Speed: {speed_label}"
        self._eta_item.title = f"ETA to full: {eta_label}"
        self._power_item.title = f"Power draw: {watts_label}"
        self._battery_temp_item.title = f"Battery temp: {battery_temp_label}"
        self._cpu_temp_item.title = f"CPU temp: {cpu_temp_label}"
        self._detail_item.title = (
            "Capacity: "
            f"{sample.current_capacity_mah}mAh / {sample.max_capacity_mah}mAh"
        )
        self._updated_item.title = f"Updated: {sample.timestamp.strftime('%H:%M:%S')}"

    def _update_install_button_visibility(self) -> None:
        """Sync CPU temperature UI visibility with tool availability.

        - If tool is NOT available: hide the CPU temp toggle + status item,
          force the setting off, and show the Install button.
        - If tool IS available: show the toggle + status item, hide Install button.
        """
        tool_available = is_cpu_temp_tool_available()

        # If tool is missing, force the setting off so it does not appear in title
        if not tool_available and self._display_settings.show_cpu_temperature:
            self._display_settings.show_cpu_temperature = False
            self._opt_show_cpu_temperature.state = 0
            _save_display_settings(self._display_settings)

        # Hide / show the CPU temperature toggle checkbox
        _set_menu_item_hidden(self._opt_show_cpu_temperature, not tool_available)
        # Hide / show the CPU temp status line
        _set_menu_item_hidden(self._cpu_temp_item, not tool_available)
        # Show install button only when tool is missing
        _set_menu_item_hidden(self._install_cpu_tool_item, tool_available)

        # Sync Launch at Login state
        if is_launch_at_login_supported():
            _set_menu_item_hidden(self._launch_at_login_item, False)
            self._launch_at_login_item.state = int(is_launch_at_login_enabled())
        else:
            _set_menu_item_hidden(self._launch_at_login_item, True)

    def _compose_title(
        self,
        *,
        percent: float,
        state_short: str,
        eta_label: str,
        power_w: float,
        battery_temp_c: float | None,
        cpu_temp_c: float | None,
    ) -> str:
        parts: list[str] = [f"{percent:3.0f}%"]
        show_icons = self._display_settings.show_metric_icons

        if self._display_settings.show_state:
            state_icon = {
                "FULL": "✅",
                "CHG": "⚡",
                "AC": "🔌",
                "BAT": "🔋",
            }.get(state_short, "•")
            parts.append(
                _metric_text(state_short, state_icon, show_icons, label="STATE")
            )

        if self._display_settings.show_remaining_time:
            parts.append(_metric_text(eta_label, "⏳", show_icons, label="ETA"))

        if self._display_settings.show_power_draw:
            parts.append(_metric_text(f"{power_w:.1f}W", "🔌", show_icons, label="PWR"))

        if self._display_settings.show_battery_temperature:
            battery_temp_text = _format_temperature(
                battery_temp_c,
                use_fahrenheit=self._display_settings.use_fahrenheit,
            )
            parts.append(
                _metric_text(
                    battery_temp_text,
                    "🌡",
                    show_icons,
                    label="BAT",
                )
            )

        if self._display_settings.show_cpu_temperature:
            cpu_temp_text = _format_temperature(
                cpu_temp_c,
                use_fahrenheit=self._display_settings.use_fahrenheit,
            )
            parts.append(_metric_text(cpu_temp_text, "🧠", show_icons, label="CPU"))

        separator = " " if show_icons else " | "
        return separator.join(parts)

    def _bind_display_toggle(
        self,
        *,
        item: rumps.MenuItem,
        key: str,
        callback,
    ) -> None:
        item.state = int(bool(getattr(self._display_settings, key, False)))
        item.set_callback(callback)

    def _toggle_setting(self, sender: rumps.MenuItem, *, key: str) -> None:
        new_value = not bool(sender.state)
        sender.state = int(new_value)
        setattr(self._display_settings, key, new_value)
        _save_display_settings(self._display_settings)
        self._refresh(None)
        self._reopen_menu()

    def _reopen_menu(self, delay: float = 0.08) -> None:
        """Re-open the status-bar menu after a toggle so it stays visible.

        macOS closes NSMenus on any item click; we work around that by asking
        the status-bar button to perform another click after a tiny debounce
        delay. The menu reopens at its original location.
        """
        with suppress(AttributeError, Exception):
            button = self._nsapp.nsstatusitem.button()
            button.performSelector_withObject_afterDelay_(
                "performClick:", None, float(delay)
            )

    def _toggle_show_state(self, sender: rumps.MenuItem) -> None:
        self._toggle_setting(sender, key="show_state")

    def _toggle_show_remaining_time(self, sender: rumps.MenuItem) -> None:
        self._toggle_setting(sender, key="show_remaining_time")

    def _toggle_show_power_draw(self, sender: rumps.MenuItem) -> None:
        self._toggle_setting(sender, key="show_power_draw")

    def _toggle_show_battery_temperature(self, sender: rumps.MenuItem) -> None:
        self._toggle_setting(sender, key="show_battery_temperature")

    def _toggle_show_cpu_temperature(self, sender: rumps.MenuItem) -> None:
        self._toggle_setting(sender, key="show_cpu_temperature")

    def _toggle_show_metric_icons(self, sender: rumps.MenuItem) -> None:
        self._toggle_setting(sender, key="show_metric_icons")

    def _toggle_use_fahrenheit(self, sender: rumps.MenuItem) -> None:
        self._toggle_setting(sender, key="use_fahrenheit")

    def _install_cpu_temperature_tool(self, _: rumps.MenuItem) -> None:
        """Install CPU temperature tool in background thread."""

        def _install():
            self._install_cpu_tool_item.title = "⏳ Installing..."
            success, message = install_cpu_temp_tool(timeout_seconds=120.0)
            if success:
                self._install_cpu_tool_item.title = "✅ Installed!"
                # Refresh UI: toggle appears, install button hides
                self._update_install_button_visibility()
            else:
                self._install_cpu_tool_item.title = f"❌ Failed: {message}"

        thread = threading.Thread(target=_install, daemon=True)
        thread.start()

    def _toggle_launch_at_login(self, sender: rumps.MenuItem) -> None:
        if not is_launch_at_login_supported():
            rumps.alert(
                title="Launch at Login",
                message=(
                    "This feature only works when the app is installed to /Applications.\n\n"
                    "Install the .dmg from the Releases page and run from there."
                ),
            )
            self._reopen_menu()
            return

        if sender.state:
            success, message = disable_launch_at_login()
        else:
            success, message = enable_launch_at_login()

        if success:
            sender.state = int(not sender.state)
        else:
            rumps.alert(title="Launch at Login", message=message)
        self._reopen_menu()

    def _check_for_updates_clicked(self, _: rumps.MenuItem) -> None:
        self._check_updates_item.title = "⏳ Checking for updates…"

        def _run():
            try:
                release = fetch_latest_release()
            except UpdateCheckError as error:
                self._check_updates_item.title = "⬆ Check for Updates…"
                rumps.alert(title="Check for Updates", message=str(error))
                return

            self._check_updates_item.title = "⬆ Check for Updates…"

            if not is_newer(release, __version__):
                rumps.alert(
                    title="You're up to date",
                    message=(
                        f"Current version {__version__} is the latest "
                        f"(tested against {release.tag})."
                    ),
                )
                return

            changelog = release.body.strip()
            if len(changelog) > 500:
                changelog = changelog[:500] + "…"
            body = (
                f"A new version {release.tag} is available "
                f"(you have {__version__}).\n\n"
                f"{changelog}\n\n"
                "Download the .dmg now?"
            )
            response = rumps.alert(
                title=f"Update available: {release.name}",
                message=body,
                ok="Download",
                cancel="Later",
            )
            if response != 1:
                return

            if not release.dmg_url:
                subprocess.run(["open", release.html_url], check=False)
                return

            self._check_updates_item.title = "⬇ Downloading update…"
            try:
                dmg_path = download_dmg(release)
            except UpdateCheckError as error:
                self._check_updates_item.title = "⬆ Check for Updates…"
                rumps.alert(title="Download failed", message=str(error))
                return

            self._check_updates_item.title = "⬆ Check for Updates…"
            # Open the DMG in Finder so the user can drag into Applications
            open_path(dmg_path)
            rumps.notification(
                title="Update downloaded",
                subtitle=release.tag,
                message="Drag MacBook Power into Applications to install.",
            )

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()


def _set_menu_item_hidden(item: rumps.MenuItem, hidden: bool) -> None:
    """Toggle menu item visibility using the underlying NSMenuItem API."""
    with suppress(AttributeError):
        item._menuitem.setHidden_(bool(hidden))


def _battery_bar(percent: float, slots: int = 10) -> str:
    """Render an ASCII battery progress bar for quick visual scanning."""
    clamped = max(0.0, min(100.0, percent))
    filled = int(round((clamped / 100.0) * slots))
    empty = max(0, slots - filled)
    return f"[{('#' * filled) + ('-' * empty)}]"


def _menubar_icon_path() -> Path:
    """Resolve menubar icon asset path from source package location."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "assets" / "icons" / "menubar-template.png"


def _refresh_interval_seconds() -> float:
    """Resolve polling interval from env var with safe defaults."""
    raw = os.getenv("MACBOOK_POWER_REFRESH_SECONDS", "3")
    try:
        value = float(raw)
    except ValueError:
        return 3.0
    return max(1.0, value)


def _format_temperature(value_c: float | None, *, use_fahrenheit: bool = False) -> str:
    """Format temperature for display."""
    if value_c is None:
        return "--"

    if use_fahrenheit:
        value_f = (value_c * 9.0 / 5.0) + 32.0
        return f"{value_f:.1f}F"

    return f"{value_c:.1f}C"


def _metric_text(value: str, icon: str, show_icons: bool, *, label: str) -> str:
    """Render a metric token with optional icon."""
    if not show_icons:
        return f"{label}:{value}"
    return f"{icon}{value}"


def _display_settings_path() -> Path:
    """Settings file location under user Library application support."""
    base = Path.home() / "Library" / "Application Support" / "macbook-power"
    return base / "display-settings.json"


def _first_run_flag_path() -> Path:
    """Marker file that records we've already asked about launch-at-login."""
    base = Path.home() / "Library" / "Application Support" / "macbook-power"
    return base / "launch-at-login-prompted"


def _load_display_settings() -> DisplaySettings:
    path = _display_settings_path()
    if not path.exists():
        return DisplaySettings()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DisplaySettings()

    return DisplaySettings(
        show_state=bool(payload.get("show_state", True)),
        show_remaining_time=bool(payload.get("show_remaining_time", True)),
        show_power_draw=bool(payload.get("show_power_draw", True)),
        show_battery_temperature=bool(payload.get("show_battery_temperature", False)),
        show_cpu_temperature=bool(payload.get("show_cpu_temperature", False)),
        show_metric_icons=bool(payload.get("show_metric_icons", True)),
        use_fahrenheit=bool(payload.get("use_fahrenheit", False)),
    )


def _save_display_settings(settings: DisplaySettings) -> None:
    path = _display_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
