<p align="center">
	<img src="assets/branding/logo.png" alt="MacBook Power logo" width="860" />
</p>

<p align="center">
	macOS menubar battery monitor with live charge speed, ETA, real system power draw, and CPU/battery temperatures.
</p>

---

## Install

### Option A — Homebrew (recommended)

Homebrew handles the download, install, and Gatekeeper unquarantine for you:

```bash
brew tap tweekazoid/tap
brew install --cask macbook-power
```

Upgrade to the latest release with:

```bash
brew upgrade --cask macbook-power
```

### Option B — Direct download (`.dmg`)

1. Go to the [**Releases**](../../releases) page and download the latest
   `MacBook-Power-<version>.dmg`.
2. Open the `.dmg` and drag **MacBook Power.app** into your **Applications** folder.
3. Eject the disk image.

Because the app is **not code-signed by Apple**, macOS will quarantine it when
downloaded from GitHub. On first launch you'll see *"Apple cannot check it for
malicious software"*. To unblock it, either:

- Right-click the app in **Applications** → **Open** → confirm, **or**
- Clear the quarantine flag from a terminal:

  ```bash
  xattr -dr com.apple.quarantine "/Applications/MacBook Power.app"
  ```

> Homebrew users skip this step — `brew install --cask` removes the quarantine
> flag automatically.

### First launch — run it manually once

After installing, **open the app manually the first time** from
**Applications** (or Launchpad / Spotlight). A battery icon will appear in
your menu bar.

On first launch the app will ask whether you want it to **start automatically
at login**. Say yes and it will be registered with macOS; from then on it
comes up on its own whenever you log in.

> If you ever need to toggle this later, use the 🚀 **Launch at Login** checkbox
> in the app menu.

### Updates

Click the app icon → ⬆ **Check for Updates…** to compare your version against
the latest GitHub release. If a newer `.dmg` is available, the app will fetch
it to `~/Downloads` and open Finder for you — install it the same way as the
first time.

---

## What you get

- Live **percentage**, **charge speed**, **ETA**, and **real system power draw**
  (non-zero even at 100 %) right in the menu bar
- **Apple Silicon CPU temperature** (M1+) via `smctemp`, with one-click install
- **Battery temperature** from built-in AppleSmartBattery telemetry
- Transparent template icon that adapts to light/dark menu bars
- **Configurable title**: toggle state, time, power, temps, icons, or °C/°F
- **Menu stays open** while toggling, so you can tweak several settings at once
- Labeled text mode (e.g. `ETA:15m | PWR:7.1W`) when you hide the emoji icons

### Configurable display options

Open the menu and flip any of these on/off:

- **Charge State** — `CHG` / `BAT` / `AC` / `FULL`
- **Remaining Time (ETA)** — time to full charge or drain
- **Power Draw** — real system watts (from `PowerTelemetryData.SystemPowerIn`)
- **Battery Temperature** — pack temperature in °C or °F
- **CPU Temperature** — processor package temperature (see below)
- **Per-Metric Icons** — use ⚡🔌🔋 glyphs instead of text labels
- **Use Fahrenheit** — switch temperature unit globally

---

## CPU temperature (optional)

Battery temperature works out of the box. CPU temperature needs an extra
helper because macOS doesn't expose it through public APIs.

1. Enable **🧠 CPU temperature** in the menu.
2. If the helper isn't installed, an **⬇ Install CPU temperature tool** button
   appears. Click it to install via Homebrew (Homebrew must already be
   installed on your Mac).
3. Or install manually:

```bash
# Apple Silicon + Intel (recommended)
brew install narugit/tap/smctemp

# Intel Macs only:
brew install osx-cpu-temp
brew install istats
```

After install, restart the widget and re-enable CPU temperature in the menu.

> On Apple Silicon only `smctemp` reports real values — `osx-cpu-temp` and
> `istats` depend on Intel-era SMC keys.

---

## For developers

### Run from source

```bash
./.scripts/setup_project.sh
source .venv/bin/activate
macbook-power-widget
```

### Useful commands

```bash
source .venv/bin/activate
python -m macbook_power.main --once   # one-shot readout
pytest -q                              # tests
ruff check .                           # lint
```

### Build the `.app` + `.dmg` locally

Install the macOS build extras and run:

```bash
pip install -e ".[mac]"
bash .scripts/build_app.sh
```

Artifacts go into `dist/`:

- `MacBook Power.app` — native menubar-only bundle (`LSUIElement`)
- `MacBook-Power-<version>.dmg` — drag-to-install disk image

### Release automation

Pushing to `main` triggers [.github/workflows/release.yml](.github/workflows/release.yml):

- Auto-bumps the patch version (commit subject hints: `BREAKING CHANGE`/`[major]`,
  `feat:`/`[minor]`, otherwise patch; use `[skip release]` to opt out)
- Commits the bump back to `main` via the GitHub Contents API (auto-signed)
- Builds the `.app` + `.dmg`
- Creates a signed tag `vX.Y.Z` and a GitHub Release with the `.dmg` attached

CI on push/PR: [.github/workflows/ci.yml](.github/workflows/ci.yml) — tests + lint.

---

## Project visuals

- Brand hero 3:1: [assets/branding/logo.png](assets/branding/logo.png) · [SVG](assets/branding/logo.svg)
- GitHub social preview 2:1: [assets/branding/logo-social.png](assets/branding/logo-social.png) · [SVG](assets/branding/logo-social.svg)
- Brand mark 1:1: [assets/branding/logo-mark.png](assets/branding/logo-mark.png) · [SVG](assets/branding/logo-mark.svg)
- Menubar runtime icon: [assets/icons/menubar-template.png](assets/icons/menubar-template.png)
- Icon pack: [assets/icons](assets/icons)

Re-render PNGs from SVG (needs `brew install librsvg`):

```bash
rsvg-convert -w 1920 -h 640 assets/branding/logo.svg        -o assets/branding/logo.png
rsvg-convert -w 1280 -h 640 assets/branding/logo-social.svg -o assets/branding/logo-social.png
rsvg-convert -w 640  -h 640 assets/branding/logo-mark.svg   -o assets/branding/logo-mark.png
```

Regenerate runtime PNG icons:

```bash
source .venv/bin/activate
python .scripts/generate_icons.py
```

---

## Roadmap / App Store direction

This repo is a strong prototype for telemetry, UX, and release mechanics.
For eventual Mac App Store distribution the practical path is:

1. Keep this repo as the behavior reference and test bed.
2. Build a native SwiftUI shell for notarization + App Store rules.
3. Port matching battery logic and validate against this project's outputs.
