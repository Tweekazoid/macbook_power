#!/usr/bin/env bash
# Build a native macOS .app bundle and drag-to-install .dmg for MacBook Power.
#
# Outputs (under dist/):
#   - MacBook Power.app        (py2app bundle)
#   - MacBook-Power-<ver>.dmg  (compressed, read-only, ready to distribute)
#
# Prerequisites:
#   - macOS with Xcode command line tools (for iconutil and hdiutil)
#   - Python venv with py2app installed:  pip install -e ".[mac]"

set -euo pipefail

cd "$(dirname "$0")/.."

# ---------------------------------------------------------------------------
# Pre-flight cleanup: ensure no stale state from a previous build blocks us.
# ---------------------------------------------------------------------------

# 1. Detach any leftover MacBook Power volumes (from previous builds or from
#    the user browsing the last .dmg in Finder).
for mount in /Volumes/MacBook\ Power*; do
    [[ -d "${mount}" ]] || continue
    # Ask Finder to close any windows pointing at the volume first
    osascript -e "tell application \"Finder\" to close (every window whose target's POSIX path contains \"${mount}\")" 2>/dev/null || true
    hdiutil detach "${mount}" -quiet 2>/dev/null || \
        hdiutil detach "${mount}" -force -quiet 2>/dev/null || true
done

# 2. Quit any running installed copy of the app so we can overwrite it.
osascript -e 'tell application "MacBook Power" to quit' 2>/dev/null || true
pkill -f "MacBook Power.app/Contents/MacOS" 2>/dev/null || true

# 3. Remove previous build artifacts so py2app starts clean.
rm -rf build "dist/MacBook Power.app"

# Auto-activate the project venv when invoked outside an already-activated shell
# (e.g. from VS Code tasks/launch). Fall back to system python3 otherwise.
if [[ -z "${VIRTUAL_ENV:-}" ]] && [[ -f .venv/bin/activate ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi
if ! command -v python >/dev/null 2>&1; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python3)"
    else
        echo "ERROR: no python interpreter found. Activate a venv or install python3." >&2
        exit 1
    fi
else
    PYTHON_BIN="$(command -v python)"
fi

VERSION=$("${PYTHON_BIN}" -c '
import sys, pathlib
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])
')
APP_NAME="MacBook Power"
APP_BUNDLE="dist/${APP_NAME}.app"
DMG_NAME="MacBook-Power-${VERSION}.dmg"
DMG_PATH="dist/${DMG_NAME}"
ICONSET_SRC="assets/branding/logo-mark.png"
ICONSET_DIR="build/logo-mark.iconset"
ICNS_OUT="assets/branding/logo-mark.icns"

echo "==> Building MacBook Power v${VERSION}"

# 1. Generate .icns from PNG if missing or stale
if [[ -f "${ICONSET_SRC}" ]] && { [[ ! -f "${ICNS_OUT}" ]] || [[ "${ICONSET_SRC}" -nt "${ICNS_OUT}" ]]; }; then
    echo "==> Generating ${ICNS_OUT} from ${ICONSET_SRC}"
    rm -rf "${ICONSET_DIR}"
    mkdir -p "${ICONSET_DIR}"
    # Apple requires these sizes for a well-formed iconset
    for spec in \
        "16 icon_16x16.png" \
        "32 icon_16x16@2x.png" \
        "32 icon_32x32.png" \
        "64 icon_32x32@2x.png" \
        "128 icon_128x128.png" \
        "256 icon_128x128@2x.png" \
        "256 icon_256x256.png" \
        "512 icon_256x256@2x.png" \
        "512 icon_512x512.png" \
        "1024 icon_512x512@2x.png"; do
        size="${spec%% *}"
        fname="${spec##* }"
        sips -z "${size}" "${size}" "${ICONSET_SRC}" --out "${ICONSET_DIR}/${fname}" >/dev/null
    done
    iconutil -c icns "${ICONSET_DIR}" -o "${ICNS_OUT}"
    rm -rf "${ICONSET_DIR}"
else
    echo "==> Using existing ${ICNS_OUT}"
fi

# 2. Clean previous build outputs
rm -rf build "${APP_BUNDLE}" "${DMG_PATH}"

# 3. Build the .app bundle via py2app
echo "==> Running py2app"
"${PYTHON_BIN}" setup_app.py py2app --dist-dir dist --bdist-base build

if [[ ! -d "${APP_BUNDLE}" ]]; then
    echo "ERROR: ${APP_BUNDLE} was not produced." >&2
    exit 1
fi

# 4. Package the .app into a drag-to-install .dmg using dmgbuild
#    (writes .DS_Store directly — layout is reliable regardless of Finder state)
echo "==> Creating ${DMG_PATH}"

# Detach any stale mount from previous runs
for stale in /Volumes/"${APP_NAME} ${VERSION}"*; do
    [[ -d "${stale}" ]] && hdiutil detach "${stale}" -force -quiet 2>/dev/null || true
done

rm -f "${DMG_PATH}"

BG_SRC="$(pwd)/assets/branding/dmg-background.png"
if [[ -f "${BG_SRC}" ]]; then
    export MBP_BG_PATH="${BG_SRC}"
else
    unset MBP_BG_PATH || true
fi
export MBP_APP_PATH="$(pwd)/${APP_BUNDLE}"
export MBP_APP_NAME="${APP_NAME}"

"${PYTHON_BIN}" -m dmgbuild \
    -s .scripts/dmg_settings.py \
    "${APP_NAME} ${VERSION}" \
    "${DMG_PATH}"

echo ""
echo "==> Build complete"
echo "    .app: ${APP_BUNDLE}"
echo "    .dmg: ${DMG_PATH} ($(du -h "${DMG_PATH}" | cut -f1))"

echo ""
echo "==> Build complete"
echo "    .app: ${APP_BUNDLE}"
echo "    .dmg: ${DMG_PATH} ($(du -h "${DMG_PATH}" | cut -f1))"
