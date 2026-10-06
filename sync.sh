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
    "pipeline.py"
    "app.py"
    "static"
    "ticker_bot.py"
    "bot_config.json"
)

EXISTING=()
for f in "${FILES[@]}"; do
    if [ -e "$f" ]; then
        EXISTING+=("$f")
    fi
done

if [ ${#EXISTING[@]} -eq 0 ]; then
    echo "[!] No record files found to sync. Run 'python3 pipeline.py --init-only' first."
    exit 1
fi

rsync -avz --progress "${EXISTING[@]}" "$PI_TARGET"

# Extract user@host from PI_TARGET to trigger immediate service refresh
TARGET_HOST="${PI_TARGET%%:*}"
if [ -n "$TARGET_HOST" ]; then
    echo "[*] Restarting digital signage services on $TARGET_HOST to refresh TV display..."
    ssh -o ConnectTimeout=10 "$TARGET_HOST" "sudo systemctl restart swim-records-web swim-records-kiosk" || {
        echo "[!] Warning: Could not automatically restart services on $TARGET_HOST. You may need to restart manually."
    }
fi

echo "[✓] Raspberry Pi TV display updated!"

# Git Push to update GitHub Pages (www.swimmcsc.com/scyrecords)
echo ""
echo "[*] Pushing updates to GitHub Pages (swimmcsc.com/scyrecords)..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # Add record data files and web pages
    git add records.json records.sqlite SCY-Records.csv index.html 2>/dev/null
    
    # Check if there are staged changes
    if ! git diff --cached --quiet; then
        COMMIT_MSG="data: update team records [$(date +'%Y-%m-%d %H:%M')]"
        git commit -m "$COMMIT_MSG"
        if git push origin main; then
            echo "[✓] Successfully pushed to GitHub! Website will update in ~25 seconds."
        else
            echo "[!] Warning: Git push failed. Please verify your internet or GitHub connection."
        fi
    else
        echo "[i] GitHub Pages is already up to date with latest records."
    fi
fi

echo ""
echo "[✓] Full sync complete! Both TV display and website are synchronized."

