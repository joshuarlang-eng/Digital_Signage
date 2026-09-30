#!/usr/bin/env bash
set -e

# ==============================================================================
# Raspberry Pi OS Lite Setup Script for Swim Records Digital Signage
# ==============================================================================

echo "=========================================================="
echo "🏊 Setting up Swim Records Digital Signage on Raspberry Pi"
echo "=========================================================="

CURRENT_USER=$(id -un)
CURRENT_UID=$(id -u)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[*] Detected User: $CURRENT_USER (UID: $CURRENT_UID)"
echo "[*] Project Directory: $PROJECT_DIR"

# 1. Install System Dependencies
echo "[*] Installing system packages (cage, chromium-browser, python3-venv)..."
sudo apt-get update
sudo apt-get install -y \
    cage \
    chromium-browser \
    curl \
    python3 \
    python3-venv \
    python3-pip \
    libinput-bin \
    fonts-liberation \
    fonts-dejavu-core

# Optional: Install Tailscale for remote syncing across networks
if ! command -v tailscale >/dev/null 2>&1; then
    echo "[*] Installing Tailscale for remote internet sync..."
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "[✓] Tailscale installed. Run 'sudo tailscale up --ssh' to connect."
fi

# Add user to render and video groups for DRM access without root
sudo usermod -a -G video,render,input "$CURRENT_USER"

# 2. Setup Python Virtual Environment
echo "[*] Setting up Python virtual environment..."
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv "$PROJECT_DIR/.venv"
fi

"$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# 3. Initialize Records Database & JSON
echo "[*] Initializing records database and JSON dashboard data..."
"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/pipeline.py" --init-only

# Ensure kiosk-browser.sh is executable
chmod +x "$PROJECT_DIR/systemd/kiosk-browser.sh"

# 4. Generate and Install Systemd Services
echo "[*] Configuring systemd services..."

# Service 1: Web App
cat <<EOF | sudo tee /etc/systemd/system/swim-records-web.service > /dev/null
[Unit]
Description=Swim Records Board Web Application (Streamlit)
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PROJECT_DIR/.venv/bin/streamlit run app.py --server.port=8501 --server.headless=true --server.address=0.0.0.0 --browser.serverAddress=localhost --browser.gatherUsageStats=false
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Service 2: Cage Kiosk
cat <<EOF | sudo tee /etc/systemd/system/swim-records-kiosk.service > /dev/null
[Unit]
Description=Cage Wayland Chromium Kiosk for Swim Records
After=swim-records-web.service graphical.target
Wants=swim-records-web.service
Conflicts=getty@tty1.service

[Service]
Type=simple
User=$CURRENT_USER
PAMName=login
Environment="XDG_RUNTIME_DIR=/run/user/$CURRENT_UID"
Environment="WAYLAND_DISPLAY=wayland-0"
Environment="WLR_LIBINPUT_NO_DEVICES=1"
Environment="WLR_BACKENDS=drm"
ExecStart=/usr/bin/cage -s -- $PROJECT_DIR/systemd/kiosk-browser.sh
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

# 5. Reload systemd and enable services
echo "[*] Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable swim-records-web.service
sudo systemctl enable swim-records-kiosk.service

echo ""
echo "=========================================================="
echo "✅ Setup Complete!"
echo "=========================================================="
echo "To start services now, run:"
echo "  sudo systemctl start swim-records-web.service"
echo "  sudo systemctl start swim-records-kiosk.service"
echo ""
echo "To view live logs:"
echo "  journalctl -u swim-records-web.service -f"
echo "  journalctl -u swim-records-kiosk.service -f"
echo "=========================================================="
