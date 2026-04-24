# Changelog

All notable changes to **MacBook Power** are documented here.
The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).

The release workflow automatically picks up the first line matching the
current version (e.g. `## v0.1.1 — Headline goes here`) and uses the text
after the dash as the GitHub release name.

## v0.3.0 — feat(release): enhance release workflow to check for code changes before proceeding

- (auto-generated; edit CHANGELOG.md on main and push)

## v0.2.0 — feat(release): add Homebrew tap update step to release workflow

- (auto-generated; edit CHANGELOG.md on main and push)

## v0.1.1 — Apple Silicon CPU temps, real system power draw, native .app

- Add native macOS `.app` bundle and drag-to-install `.dmg` (via `py2app`)
- CPU temperature via `smctemp` (Apple Silicon + Intel), with auto-install
- Real system power draw from `PowerTelemetryData.SystemPowerIn` (non-zero when full)
- Menu stays open on toggle — tweak several settings without re-clicking
- Refreshed branding: 3:1 hero PNG, 1280×640 social preview, rendering script
- Release workflow runs on `main` pushes and names releases from this file

## v0.1.0 — Initial release

- Live battery percentage, charge speed, ETA and power draw in the menu bar
- Transparent template icon that matches light/dark menu bars
- Configurable title modules (state, time, power, temps, icons, °C/°F)
- Tests, lint, CI, and automatic release workflow
