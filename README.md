# 🏊 Local Swim Team Digital Signage System

A localized, offline-capable digital signage solution for displaying swim team records on a TV display via a Raspberry Pi OS Lite (64-bit) running `cage` and Chromium in kiosk mode.

---

## 🌟 Key Features

1. **Unified Data Pipeline (`pipeline.py`)**:
   - Parses Hy-Tek `.cl2` meet result files directly.
   - Extracts swimmer information, ages, genders, events, and both prelims & finals times.
   - Converts swim times to seconds and standard swim time notation (`18.99`, `1:04.92`, `19:34.22`).
   - Compares meet results against master records **in-memory** without intermediate CSV files.
   - Automatically detects broken records, calculates time drops, and logs previous record holders.
   - Exports directly to `records.json`, SQLite database (`records.sqlite`), and updated master CSV (`SCY-Records.csv`).

2. **TV Digital Signage Dashboard (`app.py`)**:
   - Official Team Branding: Includes `MCSC Fly Logo2.png` embedded in the header.
   - Official Palette: **Pantone 299 C** (`#00A3E0`, aquatic blue) and **Pantone 802 C** (`#44D62C`, neon lime green).
   - High-contrast, dark-mode display optimized for 1080p and 4K TVs.
   - Large typography and color-coded hierarchy:
     - **Pantone 802 C Green**: Bold record times & progress bar accent.
     - **Pantone 299 C Blue**: Event names, card borders, & glowing accents.
     - **White**: Swimmer names.
     - **Muted Slate**: Record dates.
   - Dynamic **"NEW!"** pulse badges for newly broken records.
   - Automatically cycles through all 12 age group / gender combinations every 12 seconds with an animated top progress bar.
   - Interactive controls: Spacebar to pause/resume auto-cycling, Arrow keys to navigate, 'R' to reload, or click on group pills.
   - Periodic background reload every 3 minutes to pick up newly synced records seamlessly.

3. **Systemd & Wayland Kiosk Automation**:
   - Web application auto-launches on boot under systemd (`swim-records-web.service`).
   - Cage Wayland compositor launches Chromium in fullscreen kiosk mode (`swim-records-kiosk.service`).
   - Health-check wait loop in `kiosk-browser.sh` prevents `ERR_CONNECTION_REFUSED` on boot.
   - Suppresses error dialogs, update banners, and session restore prompts.

4. **Public Website Widget & GitHub Pages CI/CD (`index.html`)**:
   - Responsive, mobile-first records dashboard embedded directly on the team website at **`https://www.swimmcsc.com/scyrecords`**.
   - Hosted publicly via GitHub Pages (`https://joshuarlang-eng.github.io/Digital_Signage/`).
   - Automated CI/CD pipeline via GitHub Actions (`.github/workflows/pages.yml`) deploying in ~25s upon push to `main`.
   - Features fast client-side search, stroke filtering, age/gender pills, dynamic `NEW!` badges, and Dark Mode toggle.
   - Dual-fetch architecture: dynamic `fetch('./records.json?v=timestamp')` for live web updates with offline fallback embedded JSON.

---

## 📁 Project Structure

```
Digital Signage/
├── pipeline.py                 # Unified CL2 parser, record checker & auto-sync
├── app.py                      # Streamlit TV kiosk web dashboard (1080p/4K)
├── index.html                  # Public website records widget (swimmcsc.com)
├── records.json                # Pre-formatted JSON consumed by dashboards
├── records.sqlite              # SQLite database (records, meets, history log)
├── SCY-Records - 2-25-26.csv   # Initial master records CSV
├── SCY-Records.csv             # Updated master records CSV
├── sync.sh                     # Dual-sync script (Raspberry Pi + GitHub Pages)
├── .github/
│   └── workflows/
│       └── pages.yml           # GitHub Actions workflow for static Pages deploy
├── requirements.txt            # Python dependencies
├── systemd/
│   ├── setup.sh                # Automated installer for Raspberry Pi OS Lite
│   ├── kiosk-browser.sh        # Chromium launcher with kiosk flags & health check
│   ├── swim-records-web.service    # Systemd service for Streamlit web app
│   └── swim-records-kiosk.service  # Systemd service for Cage Wayland kiosk
└── README.md                   # Documentation
```

---

## 🚀 Usage Guide

### 1. Initializing or Resetting Records

To initialize `records.json` and `records.sqlite` from the master CSV without processing a meet:

```bash
python3 pipeline.py --init-only
```

### 2. Processing a New Swim Meet (`.cl2` file)

To process a new meet file, update all databases, and **automatically publish to GitHub Pages**:

```bash
python3 pipeline.py --meet "/path/to/Meet-Results.cl2" --team MCSC
```

* This updates `records.json`, `records.sqlite`, `SCY-Records.csv`, and `index.html`.
* It automatically commits and pushes data changes to GitHub (`origin main`), where GitHub Actions rebuilds and updates **`www.swimmcsc.com/scyrecords`** within ~25 seconds.

To process a meet, update the website, **AND** sync directly to the Raspberry Pi TV display at the pool in a single command:

```bash
python3 pipeline.py --meet "/path/to/Meet-Results.cl2" --team MCSC --sync pi@swim-signage:/home/pi/Digital-Signage
```

**Options**:
- `-m, --meet`: Path to the `.cl2` file.
- `-t, --team`: Team code (default: `MCSC`).
- `-r, --records`: Path to master records CSV (default: `SCY-Records - 2-25-26.csv`).
- `--push / --no-push`: Auto commit and push updated records to GitHub Pages (default: enabled).
- `--sync`: Target for remote sync (e.g. `pi@swim-signage:/home/pi/Digital-Signage`).
- `--json`: Output path for JSON dashboard data (default: `records.json`).
- `--db`: Output path for SQLite database (default: `records.sqlite`).
- `--csv`: Output path for updated master CSV (default: `SCY-Records.csv`).
- `--html`: Output path for web records HTML (default: `index.html`).

---

## 🌐 Public Website Integration (`swimmcsc.com/scyrecords`)

The records board is embedded on the official team website via an `<iframe>` hosted on GitHub Pages.

### Live URLs
* **Live Website**: [www.swimmcsc.com/scyrecords](https://www.swimmcsc.com/scyrecords)
* **GitHub Pages Source**: [joshuarlang-eng.github.io/Digital_Signage/](https://joshuarlang-eng.github.io/Digital_Signage/)

### Website Embed Snippet (Commit Swimming / CMS)
In Commit Swimming's page editor, add a **Custom HTML** block with:

```html
<iframe src="https://joshuarlang-eng.github.io/Digital_Signage/" width="100%" height="900" style="border:0; width:100%; height:900px;" title="MCSC Swim Team Records"></iframe>
```

*Note: Inside the Commit Swimming admin editor (`team.commitswimming.com`), security headers block third-party iframe previews with a "Content is blocked" notice. Once published or viewed directly on the public domain (`www.swimmcsc.com`), the iframe displays cleanly without restrictions.*

---

## 🌐 Remote Sync via Tailscale (Pool to Home)

Since the Raspberry Pi is stationed at the pool and not on your home Wi-Fi, [Tailscale](https://tailscale.com/) connects your local machine and the Pi into a private, encrypted mesh network that works through any pool firewall or guest Wi-Fi.

### Step 1: Install Tailscale on your Local Machine
Download and log in to Tailscale on your local computer from [tailscale.com/download](https://tailscale.com/download).

### Step 2: Install Tailscale on the Raspberry Pi
The automated installer (`bash systemd/setup.sh`) installs Tailscale automatically. To connect the Pi to your Tailscale network:

```bash
sudo tailscale up --ssh --hostname=swim-signage
```

*Note: The `--ssh` flag enables Tailscale SSH, allowing secure, keyless SSH/rsync authentication between your devices.*

### Step 3: Push Records from Anywhere
Once both machines are connected to Tailscale:

```bash
# Push directly using pipeline.py
python3 pipeline.py --meet "meet.cl2" --sync pi@swim-signage:/home/pi/Digital-Signage

# Or use the quick sync script:
./sync.sh pi@swim-signage:/home/pi/Digital-Signage
```

The TV display at the pool will automatically refresh with the new records.

### Remote Access & Troubleshooting
Because Tailscale SSH is enabled, you can also SSH directly into the Raspberry Pi from home to inspect logs, run updates, or reboot if needed:

```bash
ssh pi@swim-signage
```

---

## 🖥️ Raspberry Pi OS Lite Setup & Deployment

### Quick Setup

Run the automated setup script on your Raspberry Pi:

```bash
cd "/home/pi/Digital-Signage"
bash systemd/setup.sh
```

### Manual Setup (Step-by-Step)

#### Step 1: Install OS Dependencies
```bash
sudo apt-get update
sudo apt-get install -y cage chromium-browser curl python3 python3-venv python3-pip libinput-bin
sudo usermod -a -G video,render,input $USER
```

#### Step 2: Set Up Python Virtual Environment
```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
python3 pipeline.py --init-only
chmod +x systemd/kiosk-browser.sh
```

#### Step 3: Install Systemd Services
Copy the service files to `/etc/systemd/system/`:
```bash
sudo cp systemd/swim-records-web.service /etc/systemd/system/
sudo cp systemd/swim-records-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable swim-records-web.service
sudo systemctl enable swim-records-kiosk.service
```

#### Step 4: Start Services
```bash
sudo systemctl start swim-records-web.service
sudo systemctl start swim-records-kiosk.service
```

#### Step 5: Monitoring & Logs
```bash
# View Web App logs
journalctl -u swim-records-web.service -f

# View Kiosk display logs
journalctl -u swim-records-kiosk.service -f
```
