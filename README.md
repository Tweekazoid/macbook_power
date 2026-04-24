<p align="center">
	<img src="assets/branding/logo.svg" alt="MacBook Power logo" width="860" />
</p>

<p align="center">
	macOS menubar battery monitor with live charge speed and ETA to full.
</p>

## Highlights

- Live percentage, speed, power draw, and ETA in the menu bar
- Uses real AppleSmartBattery telemetry from ioreg
- Transparent template icon support for modern macOS menu bar behavior
- Checkbox-configurable title modules (state, time, power, temps, icons)
- No-icon mode uses labeled tokens for readability (for example `ETA:15m | PWR:7.1W`)
- Temperature units toggle between Celsius and Fahrenheit in menu settings
- Python package setup with tests, linting, and VS Code debug tasks
- GitHub Actions CI and automatic release workflow

## Configurable display options

All title components can be toggled on/off via menu checkboxes:

- **Charge State** (CHG / BAT / AC / FULL) – charging status and external power indicator
- **Remaining Time** (ETA) – time to full charge or battery drain
- **Power Draw** (watts) – current charging/discharging rate
- **Battery Temperature** – battery pack temperature in °C/°F (always available)
- **CPU Temperature** – processor package temperature (optional, see below)
- **Per-Metric Icons** – use symbols (⚡🔌🔋) instead of text labels

## CPU Temperature (optional)

Battery temperature is read from built-in macOS APIs via `ioreg`. However, CPU temperature requires third-party tools since macOS does not expose this data through standard APIs.

**To enable CPU temperature display:**

1. Enable the "🧠 CPU temperature" toggle in the app menu
2. If the tool is not installed, an "⬇ Install CPU temperature tool" button will appear
3. Click the button to auto-install via Homebrew (requires Homebrew to be installed)
4. Alternatively, install manually via Homebrew:

```bash
# Recommended: smctemp (works on Apple Silicon and Intel)
brew install narugit/tap/smctemp

# Intel Macs only (return 0.0 on Apple Silicon):
brew install osx-cpu-temp
brew install istats
```

After installation, restart the widget and enable CPU temperature in the menu settings.

If no working tool is installed, CPU temperature will display as `--` (disabled in UI).
On Apple Silicon Macs (M1+), only `smctemp` reports real values — `osx-cpu-temp`
and `istats` rely on Intel-era SMC keys.

## Project visuals

- Brand hero: [assets/branding/logo.svg](assets/branding/logo.svg)
- Brand mark: [assets/branding/logo-mark.svg](assets/branding/logo-mark.svg)
- Menubar runtime icon: [assets/icons/menubar-template.png](assets/icons/menubar-template.png)
- Additional icon pack: [assets/icons](assets/icons)

## Quick start

```bash
./.scripts/setup_project.sh
source .venv/bin/activate
macbook-power-widget
```

## Development commands

```bash
source .venv/bin/activate
python -m macbook_power.main --once
pytest -q
ruff check .
```

## Build and distribute

Create wheel and source distribution locally:

```bash
bash .scripts/build_dist.sh
```

Artifacts are written to dist.

## GitHub automation

CI workflow:

- [.github/workflows/ci.yml](.github/workflows/ci.yml)
- Runs tests and lint on push and pull requests

Release workflow:

- [.github/workflows/release.yml](.github/workflows/release.yml)
- Triggered when you push a tag matching v*
- Builds Python distributions and publishes a GitHub Release with attached artifacts

Example release flow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Icon pipeline

SVG files are kept for design and future tooling. PNG files are generated for runtime and packaging compatibility.

Regenerate PNG assets:

```bash
source .venv/bin/activate
python .scripts/generate_icons.py
```

## App Store direction

This repository is a strong prototype for telemetry logic, UX, and release mechanics.

For Mac App Store distribution later, the practical path is:

1. Keep this repo as behavior reference and test bed.
2. Build a native SwiftUI shell for notarization and App Store rules.
3. Port matching battery logic and validate against this project outputs.
