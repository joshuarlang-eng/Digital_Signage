#!/usr/bin/env bash
# ==============================================================================
# Quick Sync Script: Push records to Raspberry Pi
# ==============================================================================

# Target: accepts argument $1, or $PI_TARGET environment variable, or default Tailscale host
# Example: export PI_TARGET="pi@swim-signage:/home/pi/Digital-Signage"
PI_TARGET="${1:-${PI_TARGET:-pi@swim-signage:/home/pi/Digital-Signage}}"

echo "[*] Syncing records to Raspberry Pi ($PI_TARGET)..."

FILES=(
    "records.json"
    "records.sqlite"
    "SCY-Records.csv"
    "logo_transparent.png"
)

EXISTING=()
for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
        EXISTING+=("$f")
    fi
done

if [ ${#EXISTING[@]} -eq 0 ]; then
    echo "[!] No record files found to sync. Run 'python3 pipeline.py --init-only' first."
    exit 1
fi

rsync -avz --progress "${EXISTING[@]}" "$PI_TARGET"

echo "[✓] Sync complete! The TV display will automatically refresh."
