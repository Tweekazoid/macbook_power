"""Check GitHub Releases for a newer version of the widget and download it."""

from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GITHUB_OWNER = "Tweekazoid"
GITHUB_REPO = "macbook_power"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


@dataclass
class ReleaseInfo:
    tag: str
    version_tuple: tuple[int, ...]
    name: str
    body: str
    html_url: str
    dmg_url: str | None
    dmg_name: str | None


class UpdateCheckError(RuntimeError):
    pass


def _parse_version(raw: str) -> tuple[int, ...]:
    cleaned = raw.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in cleaned.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) or (0,)


def fetch_latest_release(timeout: float = 10.0) -> ReleaseInfo:
    request = urllib.request.Request(
        RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{GITHUB_REPO}-updater",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw = response.read()
    except Exception as error:  # pragma: no cover - network
        raise UpdateCheckError(f"Network error: {error}") from error

    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as error:  # pragma: no cover
        raise UpdateCheckError(f"Malformed response: {error}") from error

    tag = str(payload.get("tag_name", ""))
    if not tag:
        raise UpdateCheckError("No releases published yet")

    dmg_url = None
    dmg_name = None
    for asset in payload.get("assets", []) or []:
        name = str(asset.get("name", ""))
        if name.endswith(".dmg"):
            dmg_url = str(asset.get("browser_download_url", ""))
            dmg_name = name
            break

    return ReleaseInfo(
        tag=tag,
        version_tuple=_parse_version(tag),
        name=str(payload.get("name") or tag),
        body=str(payload.get("body") or ""),
        html_url=str(payload.get("html_url") or RELEASES_PAGE_URL),
        dmg_url=dmg_url,
        dmg_name=dmg_name,
    )


def is_newer(latest: ReleaseInfo, current_version: str) -> bool:
    return latest.version_tuple > _parse_version(current_version)


def download_dmg(release: ReleaseInfo, dest_dir: Path | None = None) -> Path:
    if not release.dmg_url or not release.dmg_name:
        raise UpdateCheckError("Latest release has no .dmg asset")
    dest_dir = dest_dir or (Path.home() / "Downloads")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / release.dmg_name
    request = urllib.request.Request(
        release.dmg_url,
        headers={"User-Agent": f"{GITHUB_REPO}-updater"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60.0) as response:  # noqa: S310
            dest.write_bytes(response.read())
    except Exception as error:  # pragma: no cover - network
        raise UpdateCheckError(f"Download failed: {error}") from error
    return dest


def reveal_in_finder(path: Path) -> None:
    subprocess.run(["open", "-R", str(path)], check=False)


def open_path(path: Path) -> None:
    subprocess.run(["open", str(path)], check=False)
