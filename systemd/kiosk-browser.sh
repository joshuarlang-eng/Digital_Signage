#!/usr/bin/env bash
# ==============================================================================
# Chromium Kiosk Launcher for Cage Wayland Compositor
# ==============================================================================

TARGET_URL="http://localhost:8501"

# Wait for Streamlit server to be healthy before launching Chromium
# This prevents ERR_CONNECTION_REFUSED if browser starts faster than Python
echo "Waiting for Streamlit server at $TARGET_URL..."
for i in {1..60}; do
    if curl -s "${TARGET_URL}/_stcore/health" > /dev/null; then
        echo "Streamlit is healthy and responding!"
        break
    fi
    sleep 1
done

# Detect Chromium binary name (prefer direct binary to avoid Debian wrapper injecting --disable-dev-shm-usage and --force-renderer-accessibility)
if [ -x "/usr/lib/chromium/chromium" ]; then
    CHROME_BIN="/usr/lib/chromium/chromium"
elif command -v chromium >/dev/null 2>&1; then
    CHROME_BIN="chromium"
elif command -v chromium-browser >/dev/null 2>&1; then
    CHROME_BIN="chromium-browser"
else
    echo "Error: Chromium browser not found!" >&2
    exit 1
fi

# Clean up any stale crash flags or locks from sudden power-offs
rm -rf ~/.config/chromium/Singleton* /tmp/chromium-cache

# Set 1080p @ 60 FPS on HDMI-A-1 for ultra-smooth 60Hz compositor and cool operation
if command -v wlr-randr >/dev/null 2>&1; then
    wlr-randr --output HDMI-A-1 --mode 1920x1080@60Hz || true
fi

# Launch Chromium in dedicated kiosk mode on Wayland
exec "$CHROME_BIN" \
    --ozone-platform=wayland \
    --kiosk \
    --force-dark-mode \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --fast \
    --fast-start \
    --enable-gpu-rasterization \
    --use-angle=gles \
    --disable-features=TranslateUI,Spellcheck \
    --disable-spell-checking \
    --check-for-update-interval=31536000 \
    --simulate-outdated-no-au='Tue, 31 Dec 2099 23:59:59 GMT' \
    --overscroll-history-navigation=0 \
    --disable-pinch \
    --password-store=basic \
    --disk-cache-dir=/tmp/chromium-cache \
    --disk-cache-size=10485760 \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --incognito \
    "$TARGET_URL"
