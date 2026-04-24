#!/usr/bin/env python3
"""Generate transparent PNG icon assets from simple vector-like primitives.

This keeps SVG files for future workflows while producing PNG files needed by
menubar integrations and packaging tools.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT / "assets" / "icons"


def _save_antialiased(draw_fn, size: int, out_path: Path, scale: int = 6) -> None:
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw_fn(draw, size * scale)
    image = canvas.resize((size, size), Image.Resampling.LANCZOS)
    image.save(out_path)


def _draw_menubar(draw: ImageDraw.ImageDraw, size: int) -> None:
    black = (0, 0, 0, 255)
    stroke = max(1, size // 20)

    bolt = [
        (size * 0.57, size * 0.08),
        (size * 0.35, size * 0.50),
        (size * 0.50, size * 0.50),
        (size * 0.42, size * 0.90),
        (size * 0.73, size * 0.44),
        (size * 0.58, size * 0.44),
    ]
    draw.polygon(bolt, fill=black)
    arc_bounds = (size * 0.08, size * 0.08, size * 0.92, size * 0.92)
    draw.arc(arc_bounds, 175, 300, fill=black, width=stroke)
    draw.arc(arc_bounds, 5, 130, fill=black, width=stroke)


def _draw_battery(draw: ImageDraw.ImageDraw, size: int) -> None:
    stroke = max(2, size // 24)
    fg = (255, 255, 255, 255)
    bg = (11, 17, 26, 255)
    fill = (52, 199, 89, 255)

    body = (size * 0.10, size * 0.20, size * 0.82, size * 0.80)
    draw.rounded_rectangle(body, radius=size * 0.08, fill=bg, outline=fg, width=stroke)
    tip = (size * 0.82, size * 0.38, size * 0.92, size * 0.62)
    draw.rounded_rectangle(tip, radius=size * 0.03, fill=fg)
    charge = (size * 0.18, size * 0.28, size * 0.66, size * 0.72)
    draw.rounded_rectangle(charge, radius=size * 0.04, fill=fill)


def _draw_charging(draw: ImageDraw.ImageDraw, size: int) -> None:
    _draw_battery(draw, size)
    bolt = [
        (size * 0.55, size * 0.12),
        (size * 0.40, size * 0.52),
        (size * 0.53, size * 0.52),
        (size * 0.44, size * 0.90),
        (size * 0.70, size * 0.42),
        (size * 0.57, size * 0.42),
    ]
    draw.polygon(bolt, fill=(255, 193, 7, 255))


def _draw_plug(draw: ImageDraw.ImageDraw, size: int) -> None:
    fg = (215, 222, 232, 255)
    accent = (48, 176, 199, 255)
    bg = (11, 17, 26, 255)

    draw.rounded_rectangle((0, 0, size, size), radius=size * 0.14, fill=bg)
    draw.rounded_rectangle(
        (size * 0.39, size * 0.14, size * 0.45, size * 0.34),
        radius=size * 0.02,
        fill=fg,
    )
    draw.rounded_rectangle(
        (size * 0.55, size * 0.14, size * 0.61, size * 0.34),
        radius=size * 0.02,
        fill=fg,
    )
    draw.rounded_rectangle(
        (size * 0.33, size * 0.34, size * 0.67, size * 0.62),
        radius=size * 0.06,
        fill=accent,
    )
    draw.rounded_rectangle(
        (size * 0.47, size * 0.62, size * 0.53, size * 0.88),
        radius=size * 0.03,
        fill=fg,
    )


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    _save_antialiased(_draw_menubar, 18, ICONS_DIR / "menubar-template.png")
    _save_antialiased(_draw_battery, 128, ICONS_DIR / "battery.png")
    _save_antialiased(_draw_charging, 128, ICONS_DIR / "charging.png")
    _save_antialiased(_draw_plug, 128, ICONS_DIR / "power-plug.png")

    print("Generated PNG icons in", ICONS_DIR)


if __name__ == "__main__":
    main()
