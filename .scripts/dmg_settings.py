"""dmgbuild configuration for MacBook Power.

Invoked by .scripts/build_app.sh. Reads env vars:
  MBP_APP_PATH   absolute path to the .app bundle
  MBP_APP_NAME   display name ("MacBook Power")
  MBP_BG_PATH    absolute path to background PNG (optional)
"""
from __future__ import annotations

import os

app_path = os.environ["MBP_APP_PATH"]
app_name = os.environ.get("MBP_APP_NAME", "MacBook Power")
bg_path = os.environ.get("MBP_BG_PATH") or None

# Contents shown in the mounted DMG
files = [app_path]
symlinks = {"Applications": "/Applications"}

# Icon positions (x, y) relative to the window
icon_locations = {
    f"{app_name}.app": (180, 210),
    "Applications": (520, 210),
}

# Window & view configuration — dmgbuild writes these directly into the
# DMG's .DS_Store without needing Finder/AppleScript, so the layout is
# reliable regardless of the user's Finder preferences.
background = bg_path  # None → plain background
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
sidebar_width = 0

window_rect = ((200, 120), (700, 400))
default_view = "icon-view"
show_icon_preview = False
include_icon_view_settings = "auto"
include_list_view_settings = "auto"

arrange_by = None
grid_offset = (0, 0)
grid_spacing = 100
scroll_position = (0, 0)
label_pos = "bottom"
text_size = 13
icon_size = 128

# DMG format
format = "UDZO"
compression_level = 9
filesystem = "HFS+"

# Hide invisibles regardless of user's Finder setting by not creating them
# at all — dmgbuild won't write a .background folder; the PNG is embedded
# via the .DS_Store "background picture" pointer pointing inside the image.
