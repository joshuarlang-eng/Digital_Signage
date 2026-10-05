# 🏊 Swim Team Digital Signage — Project Journal

**Date**: September 27, 2026  
**Project**: MCSC Swim Team Digital Signage Board  
**Working Directory**: `/home/jrl/Projects/Digital_Signage`  
**GitHub Repository**: `https://github.com/joshuarlang-eng/Digital_Signage` (Release `v2.0`)  

---

## 📌 Executive Summary

Today we built, tested, and finalized **Version 1** of an offline-capable, automated digital signage system for the Marshall County Swim Club (MCSC) record board, designed to replace a manual Google Sheets/Slides workflow with a fully localized Python pipeline. We then cloned the completed project into **Version 2** as a sandbox for future enhancements.

---

## 🛠️ What Was Accomplished Today

### 1. Refactored Data Pipeline (`pipeline.py`)
* **Merged Legacy Code**: Consolidated `cl2 parser.py` (Hy-Tek meet parser) and `NEW SCY Records Match.py` (record comparison logic) into a unified, zero-dependency standard library pipeline.
* **In-Memory Matching**: Eliminated intermediate CSV files. Meet data is parsed directly into memory, comparing prelims and finals times against the master records in a single pass.
* **Swim Meet Timing & Bins**:
  * Accurate age group binning: `6U`, `8U`, `9-10`, `11-12`, `13-14`, `Senior`.
  * Robust swim time string parser handling non-times (DQ, NS, SCR) and course codes (`Y`, `L`, `S`).
  * Time formatter converting seconds to standard swim notation (e.g. `18.99`, `1:04.92`, `20:55.17`).
* **Real Meet Verification**: Tested against `2026 SE Southeastern Winter SC Championships` meet file, accurately detecting and logging 8 broken team records with time drops and previous record holders.
* **Outputs Generated**:
  * `records.json`: Pre-structured, pre-grouped JSON consumed by the dashboard.
  * `records.sqlite`: Relational SQLite database with tables for `records`, `meets`, and `broken_records_history`.
  * `SCY-Records.csv`: Updated master records CSV maintained for spreadsheet backwards-compatibility.

### 2. Digital Signage Web Dashboard (`app.py`)
* **Dark Mode TV Layout**: High-contrast dark theme (`#070c18`) designed for viewing from 20+ feet away across a pool deck.
* **Official MCSC Branding**:
  * Integrated `MCSC Fly Logo2.png` into the header. Created a clean transparent version (`logo_transparent.png`) base64-encoded directly into the frontend for 100% offline, zero-asset-lag loading.
  * **Pantone 299 C (`#00A3E0` - Aquatic Blue)**: Used for event titles, borders, ambient glow, and active pill highlights.
  * **Pantone 802 C (`#44D62C` - Electric Neon Green)**: Used for bold record times, the top progress bar, and pulsing "NEW!" badges.
  * High-contrast white for swimmer names and muted slate for dates.
* **12-Second Auto-Cycling**: Cycles through all 12 age group / gender combinations with an animated top progress bar.
* **Zero-Scroll Guarantee Verified**:
  * Formatted with `grid-auto-flow: column;` and 3 balanced columns:
    * **Column 1**: All Freestyle events (25 Free through 1650 Free)
    * **Column 2**: Backstroke & Breaststroke events
    * **Column 3**: Butterfly & Individual Medley (IM) events
  * Dynamic row calculation (`Math.ceil(records.length / 3)`) and responsive `clamp()` padding.
  * Verified via headless Chromium testing at both **1080p** (1920x1080) and **720p** (1280x720): even Senior Girls (maximum 21 events) fits 100% within the viewport with zero vertical scrollbars and ample breathing room.
* **Interactive Controls**:
  * <kbd>Space</kbd>: Pause / resume auto-cycling.
  * <kbd>←</kbd> / <kbd>→</kbd>: Step back or forward through age groups.
  * Clickable pills along the footer to jump to any age group.
  * <kbd>R</kbd>: Force an immediate data refresh.
  * Automatic background reload every 3 minutes.

### 4. Physical Raspberry Pi 4 Deployment & Field Verification
* **Hardware Verified**: Raspberry Pi 4 Model B (USB-C power, 2 micro-HDMI, 4 USB-A, Gigabit Ethernet).
* **OS Setup**: Raspberry Pi OS Lite (64-bit Debian Bookworm).
* **Display Output**: Attached to micro-HDMI Port 0 (adjacent to USB-C power port).
* **Issues Diagnosed & Solved**:
  * **UK Keyboard Layout**: Pi OS defaults to UK (`gb`) keymap swapping `"` and `@`. Resolved Wi-Fi connection via `sudo raspi-config` menu.
  * **Systemd Multi-User Target**: Pi OS Lite defaults to `multi-user.target`, leaving services `WantedBy=graphical.target` inactive. Updated unit to `WantedBy=multi-user.target`.
  * **DRM/TTY Takeover**: Added `TTYPath=/dev/tty1`, `StandardInput=tty`, `TTYReset=yes`, `TTYVHangup=yes`, and `TTYVTDisallocate=yes` so Cage successfully switches the Linux kernel VT from text console to DRM graphics mode.
  * **Wayland Ozone Platform**: Added `--ozone-platform=wayland` to Chromium launcher flags, allowing Chromium to run natively on Cage without an X11 server.
  * **Timezone & 12-Hour Clock**: Adjusted system timezone to `America/Chicago` (US Central) and updated live JavaScript clock in `app.py` to 12-hour AM/PM format (`en-US`).
* **Result**: Tested and verified on physical hardware. The Pi boots directly from power-on into full-screen kiosk mode with zero user interaction, zero error dialogs, and continuous 12-second auto-cycling.

### 5. Remote Sync via Tailscale (Pool to Home)
* Addressed constraint that the Pi will be at the pool facility and not on home Wi-Fi.
* Chose **Tailscale** private encrypted mesh network:
  * Bypasses firewalls, NATs, and guest Wi-Fi at the pool.
  * Uses Tailscale SSH (`sudo tailscale up --ssh --hostname=swim-signage`) for keyless, passwordless SSH/rsync.
* **Local Machine Configured**: Tailscale is installed, enabled, and authenticated on this Omarchy machine (`100.99.103.43`, hostname `omarchy`).
* Added `--sync` parameter to `pipeline.py` and created a standalone `./sync.sh` script for 1-command remote updates:
  ```bash
  python3 pipeline.py --meet "meet.cl2" --team MCSC --sync pi@swim-signage:/home/pi/Digital-Signage
  ```

### 6. Version 1 Status: Officially Complete & Locked ✅
* **Milestone Reached**: Version 1 is fully functional and running live on the physical Raspberry Pi 4 kiosk TV display.
* **Key Achievements**:
  * Edge-to-edge full-bleed kiosk display with zero margins or white borders.
  * Native Wayland DRM acceleration via Cage.
  * Chromium spellcheck disabled for swimmer names.
  * Synchronized 12-hour AM/PM clock matching pool facility local time (US Central).
  * 100% offline-capable, automated boot sequence with zero manual intervention.
* **Repository Baseline**: `/home/jrl/Projects/Digital Signage` is frozen and locked as Version 1.

### 7. Next Testing Phase: Virtual Environment Sandbox (Version 2)
* **Strategy**: All further `.cl2` parsing verification and Tailscale sync simulation will take place strictly on the host PC inside `/home/jrl/Projects/Digital Signage V2/.venv`, ensuring the physical Pi remains stable and undisturbed.
* **Testing Objectives**:
  1. Validate `.cl2` ingestion edge cases (scratches, relays, exhibition swims, splits, invalid times).
  2. Verify Tailscale end-to-end sync workflow and conflict handling in a staged environment before touching production.

---

## 🛠️ Update: September 29, 2026 — Diagnostic & Resolution for Pi Periodic Freezing

### ⚠️ Problem Description
The Raspberry Pi kiosk periodically locked up / froze after running for several hours (observed after ~6 hours in boot -3 and ~1.5 hours in boot -1), requiring a hard power-cycle to recover.

### 🔬 Root Cause Analysis
1. **Chromium GPU & Renderer Runaway (~195% CPU continuously)**:
   - `requestAnimationFrame(loop)` in `app.py` continuously updated `progressBar.style.width` at 60 FPS, forcing layout reflow and repaint every 16ms.
   - All 21 `.record-card` elements had `backdrop-filter: blur(8px)`. On the Pi 4's VideoCore VI GPU (Mesa V3D driver), computing multi-pass Gaussian blur shaders across 21 elements during a 60 FPS repaint loop pegged the GPU process at 100% CPU and the renderer at 82% CPU.
2. **Extreme Memory Starvation & Swap Deadlock**:
   - The Pi 4 has 1 GB total RAM (`907 MiB`).
   - The default `dtoverlay=vc4-kms-v3d` reserved **512 MiB for CMA**, leaving only **388 MiB of physical RAM** for the OS, Streamlit, and Chromium.
   - Swap was set to only **200 MiB** (`/var/swap`) and was **99.8% full** (199.7 MiB used).
   - Once memory was exhausted, the kernel entered an uninterruptible I/O paging deadlock against the slow micro-SD card, locking all processes in `D` state.
3. **Shared Memory Forced to SD Card**:
   - Debian's `/etc/chromium.d/dev-shm` injected `--disable-dev-shm-usage` because `/dev/shm` was under 3.8GB, forcing Chromium to write textures and IPC buffers directly to `/tmp/` on the micro-SD card at 60 FPS.
4. **Accessibility Overhead**:
   - Debian's `/etc/chromium.d/00-rpi-vars` injected `--force-renderer-accessibility`, forcing Chromium to build accessibility tree models for all DOM nodes on a screen without assistive software.

### ✅ Solutions Implemented & Deployed
1. **Frontend Optimization ([app.py](file:///home/jrl/Projects/Digital%20Signage%20V2/app.py))**:
   - Replaced the 60 FPS JS animation loop with a compositor-only `transform: scaleX()` CSS transition. Progress bar animation now runs purely on the GPU compositor with zero JavaScript execution during the 12-second cycle.
   - Removed `backdrop-filter: blur(8px)` from `.record-card`, replacing it with a crisp `rgba(13, 21, 38, 0.95)` card background.
   - Cleaned up duplicated CSS and removed continuous `@keyframes pulse-glow` scale transforms.
2. **Reclaimed 384 MB Physical RAM**:
   - Configured `dtoverlay=vc4-kms-v3d,cma-128` in `/boot/firmware/config.txt`. Available memory for the kernel/OS doubled from 388 MB to **781 MB**.
3. **Expanded Swap Space to 1,024 MB**:
   - Updated `/etc/dphys-swapfile` to `CONF_SWAPSIZE=1024`, expanding swap headroom from 200 MB to 1 GB (>950 MB free headroom).
4. **Bypassed SD Card Thrashing in Kiosk Launcher ([systemd/kiosk-browser.sh](file:///home/jrl/Projects/Digital%20Signage%20V2/systemd/kiosk-browser.sh))**:
   - Targeted `/usr/lib/chromium/chromium` directly to bypass Debian wrappers that injected `--disable-dev-shm-usage` and `--force-renderer-accessibility`.
   - Limited disk cache to 10 MB (`--disk-cache-size=10485760`).
5. **Enabled Hardware Watchdog**:
   - Activated Broadcom BCM2835 hardware watchdog (`RuntimeWatchdogSec=15s` in `/etc/systemd/system.conf`), ensuring the board automatically recovers if a kernel lockup ever recurs.

### 📊 Verification & Pre-Deployment Audit Results
- **GPU Process CPU**: Dropped from **100.0%** to **~23.5%**.
- **Renderer Process CPU**: Dropped from **82.4%** to **~11.8%**.
- **Total Combined Chromium CPU**: Dropped from **~195% (2 full cores)** to **~35-45%**.
- **Available RAM**: Increased from 388 MB to **781 MB**.
- **Swap Free**: **939 MB free** out of 1024 MB.
- **Operating Temperature**: Dropped to **47.2°C** with zero thermal throttling (`throttled=0x0`).
- **Screen Blanking Prevention**: Appended `consoleblank=0` to `/boot/firmware/cmdline.txt` and added `--disable-background-timer-throttling` / `--disable-renderer-backgrounding` to [kiosk-browser.sh](file:///home/jrl/Projects/Digital%20Signage%20V2/systemd/kiosk-browser.sh).
- **Log Management**: Configured `SystemMaxUse=100M` in `/etc/systemd/journald.conf` to protect SD card wear and prevent storage leaks.
- **Network Readiness**: Verified NetworkManager profiles for `Pool-WiFi`, home Wi-Fi (`Skynet 2.0`), and wired Ethernet DHCP. Tailscale daemon active for remote updates.
- **Deployment Status**: **PASSED ALL CHECKS — Cleared for physical deployment on pool deck TV.**

---

## 📌 Update: September 29–30, 2026 — 4K UHD Deployment, Zero-Package Capture & GitHub Migration

### 1. 4K Pool TV Scaling & "Top-Left Quarter" Bug Resolved
* **Field Finding**: When plugged into the pool TV, HDMI negotiated native 4K UHD (`3840x2160`). At native resolution, previous 1080p pixel clamps (`clamp(16px, 2.2vh, 23px)`) caused typography and cards to render at 1x scale, taking up only ~35% of the screen.
* **Diagnosed Failed Attempt**: Passing `--force-device-scale-factor=2` to Chromium caused the display to shrink into the **top-left quarter** of the screen.
  - **Root Cause**: The Wayland compositor **Cage** (`/usr/bin/cage -s`) does not upscale client buffers. Chromium rendered a 1920×1080 Wayland surface which Cage placed 1:1 in the top-left quadrant of the 3840×2160 screen.
* **The Solution (Pure CSS Media Queries)**:
  - Reverted `--force-device-scale-factor` from [`systemd/kiosk-browser.sh`](file:///home/jrl/Projects/Digital_Signage/systemd/kiosk-browser.sh) so Chromium creates a native 3840×2160 fullscreen surface.
  - Added `@media (min-width: 2500px) or (min-height: 1400px)` in [`app.py`](file:///home/jrl/Projects/Digital_Signage/app.py):
    - Scaled typography: Event names (28–46px), swimmer names (26–42px), record times (48–80px), team title (42px), active banner (60px), clock (52px), nav pills (22px).
    - Scaled logo height to 110px.
    - Updated JavaScript row balancing in `renderSlide()` to use `minmax(150px, 240px)` on displays where `window.innerHeight > 1400`.
  - Preserved **zero-scroll guarantee** across all 12 age groups (including 21-event Senior Girls) with 100% full-screen coverage.

### 2. Live Verification on Raspberry Pi
* Deployed updated `app.py` and `systemd/kiosk-browser.sh` via SSH/rsync over Tailscale (`pi@swim-signage`).
* Restarted `swim-records-web.service` and `swim-records-kiosk.service`.
* Captured native 4K screen render without installing any extra packages on the Pi (using local Chromium headless via Chrome DevTools Protocol against `http://swim-signage:8501`).
* Saved full-resolution 3840×2160 capture to [`~/Pictures/swim_signage_4k_live.png`](file:///home/jrl/Pictures/swim_signage_4k_live.png).

### 3. GitHub Migration & Directory Consolidation
* Initialized Git repository tracking `main` branch.
* Added clean `.gitignore` (excluding `.venv/`, `__pycache__/`, etc.).
* Generated SSH key (`~/.ssh/id_rsa.pub`) and linked to user's GitHub account (`joshuarlang-eng`).
* Pushed repository to **[https://github.com/joshuarlang-eng/Digital_Signage](https://github.com/joshuarlang-eng/Digital_Signage)**.
* Tagged milestone release **`v2.0`** and pushed tag to GitHub.
* Consolidated workspace: deleted redundant `~/Projects/Digital Signage` and renamed active directory to `~/Projects/Digital_Signage`.

---

## 📢 Update: September 30, 2026 — Live Scrolling Ticker & Telegram Bot Integration

### 1. ESPN-Style Lower-Third Scrolling Ticker
* Added a dedicated announcement ticker (`.ticker-bar`) docked right above the footer navigation in [`app.py`](file:///home/jrl/Projects/Digital_Signage/app.py).
* **Styling**:
  * Glowing left badge (`📢 ANNOUNCEMENT` in electric neon green when active, `MCSC NEWS` in aquatic blue for default motto).
  * Smooth compositor-only CSS marquee animation (`@keyframes ticker-scroll`) with dynamic duration calculation based on message character count for a natural, readable crawl speed.
  * Preserves the **zero-scroll guarantee** on both **1080p** and **4K UHD** displays (adjusted `records-grid` `max-height` so Senior Girls 21 events fit with zero scrollbars).
* **Live In-Place Updates**:
  * Configured Streamlit `enableStaticServing = true` in [`.streamlit/config.toml`](file:///home/jrl/Projects/Digital_Signage/.streamlit/config.toml).
  * Client-side JavaScript polls `/app/static/ticker.json` every 10 seconds. New messages from coaches appear on screen live **without reloading the page or causing flicker**.

### 2. Telegram Bot Daemon (`ticker_bot.py`)
* Developed a lightweight, zero-external-dependency Telegram bot daemon running via standard library `urllib` and `json`.
* **Outbound Long-Polling**: Works behind pool facility guest Wi-Fi, NAT, and firewalls without requiring open router ports or public domains.
* **Commands**:
  * Any plain text message: Instantly posts that announcement to the live TV ticker.
  * `/status`: Displays current message, author, and timestamp.
  * `/clear` or `/stop`: Resets the ticker back to the default team motto.
  * `/motto`: Checks the active default team motto.
  * `/setmotto <text>`: Changes the team motto directly from Telegram and saves to config.
  * `/addcoach <chat_id>`: Whitelists assistant coaches directly from Telegram.
  * `/help`: Displays command guide.
* **Security & Whitelist**:
  * Implemented first-time auto-claim: the first coach to message the bot is registered as primary administrator.
  * Unauthorized users receive their Chat ID with instructions to contact the administrator.
  * `bot_config.json` added to [`.gitignore`](file:///home/jrl/Projects/Digital_Signage/.gitignore) to protect bot API tokens. Template provided in [`bot_config.example.json`](file:///home/jrl/Projects/Digital_Signage/bot_config.example.json).

### 3. Production Readiness & Systemd Service
* Created [`systemd/swim-ticker-bot.service`](file:///home/jrl/Projects/Digital_Signage/systemd/swim-ticker-bot.service) for automatic background launch on Raspberry Pi boot.
* Updated [`sync.sh`](file:///home/jrl/Projects/Digital_Signage/sync.sh) to include static ticker files and bot scripts.
* Verified end-to-end locally in `.venv` with live Telegram messaging. Feature branch `feature/telegram-ticker` staged for field verification on physical pool TV kiosk.

### 4. Pool Field Verification & 1080p @ 60 FPS Switch ✅
* **Field Test Outcome**:
  * Ticker and Telegram bot (`@mcsc_ticker_bot`) verified live on the physical 75" Samsung pool TV.
  * Coach Telegram messages update the screen in real-time within 10 seconds.
  * `/clear`, `/motto`, and `/setmotto` working smoothly.
* **1080p @ 60 FPS Resolution Transition (v2.2)**:
  * Diagnosed that the TV was negotiating 4K @ 30 Hz (`mode: 3840x2160 @ 30.00 Hz`), causing horizontal motion judder in the ticker and slide transitions.
  * Installed `wlr-randr` on the Pi and updated [`systemd/kiosk-browser.sh`](file:///home/jrl/Projects/Digital_Signage/systemd/kiosk-browser.sh) to lock the HDMI-A-1 output to `1920x1080 @ 60.00 Hz`.
  * The TV's internal 4K hardware upscaler automatically stretches the 1080p signal to fill the 75" panel, while animations run at a locked, buttery 60 FPS with low temperature (~50°C) and minimal memory bandwidth.

### 5. Card Layout Redesign & Typography Scaling (v2.3) ✅
* **Problem**: Each record card originally had 3 vertical lines on the left side: Event Name, Swimmer Name, and Full Date (`YYYY-MM-DD`). This squeezed the vertical space and forced the swimmer's name font size down to ~16px, making it difficult to read from 25–30+ feet across the pool deck.
* **Inline Year Formatting**:
  * Extracted the 4-digit record year via `formatRecordYear()` in [`app.py`](file:///home/jrl/Projects/Digital_Signage/app.py) and placed it inline directly beside the swimmer's name (e.g. `Brooks Lang (2024)`).
  * Styled `.swimmer-year` in muted slate (`var(--text-muted)` at `0.72em`) to keep the primary visual focus on the swimmer's name while keeping the achievement year cleanly identifiable.
* **Typography & Spacing**:
  * Bumped `.swimmer-name` font size up to `clamp(18px, 2.7vh, 27px)` (and up to `48px` in 4K).
  * Expanded spacing gap between name and year to `clamp(14px, 1.4vw, 22px)` (and `28px` in 4K) for clear visual separation.
  * Widened `.event-info` maximum width from `58%` to `65%` to prevent premature truncation of longer names, while retaining `flex-shrink: 0` on `.time-info`.
  * Preserves the **zero-scroll guarantee** on the dense 21-event Senior Girls slide.

* **Milestone Releases Summary**:
  * **[`v2.1`](https://github.com/joshuarlang-eng/Digital_Signage/releases/tag/v2.1)**: Live ESPN-style scrolling ticker, Web Animations API GPU compositor rendering, and Telegram bot daemon (`@mcsc_ticker_bot`).
  * **[`v2.2`](https://github.com/joshuarlang-eng/Digital_Signage/releases/tag/v2.2)**: 1080p @ 60 FPS output locking via `wlr-randr` in [`systemd/kiosk-browser.sh`](file:///home/jrl/Projects/Digital_Signage/systemd/kiosk-browser.sh) for silky-smooth physical TV animations.
  * **[`v2.3`](https://github.com/joshuarlang-eng/Digital_Signage/releases/tag/v2.3)**: Card layout redesign: date formatted as 4-digit year inline with swimmer name (`Brooks Lang (2024)`), increased spacing gap, and enlarged swimmer typography for visibility from across the pool deck.

---

## 🏊 Update: October 5, 2026 — 2026 Spooky Splash Meet Ingestion, Mixed-Event Gender Fix & Gage Martin Alias

### 1. 2026 SES WAKE-CTA Spooky Splash Meet Ingestion
* Ingested meet results file [`Meet Results-2026 SES WAKE-CTA Spooky Splash-03Oct2026-001.cl2`](file:///home/jrl/Projects/Digital_Signage/Meet%20Results-2026%20SES%20WAKE-CTA%20Spooky%20Splash-03Oct2026-001.cl2) (held October 3–4, 2026).
* Extracted **129 valid swims** across **24 MCSC swimmers**.
* Detected and verified **19 new or newly established team records**:
  * **8U Girls**: Finley T Lewis broke 7 records (50 Free @ 35.17, 100 Free @ 1:21.80, 50 Back @ 42.55, 100 Back @ 1:32.97, 100 Breast @ 1:59.84, 100 Fly @ 1:46.90, 100 IM @ 1:35.68).
  * **9-10 Girls**: Peri L Davis (100 Breast @ 1:43.87, 200 Back @ 2:58.10), Yhana B Maxilom (200 IM @ 3:12.72).
  * **11-12 Girls**: Tessa T Cook (200 Back @ 2:44.42).
  * **11-12 Boys**: Jace C Duncan (50 Fly @ 28.09, 100 Fly @ 1:03.96, 100 Back @ 1:05.56).
  * **13-14 Boys**: Gage Martin (50 Back @ 27.42, 50 Fly @ 27.66, 100 IM @ 1:01.48), Michael W Alred (100 Fly @ 58.69, 400 IM @ 4:43.89).

### 2. CL2 Mixed/Open Event Gender Fix (Column 66 vs 67)
* **Root Cause**: The 2026 meet operated with open/mixed events, putting `'X'` in Column 67 (0-indexed 66).
  * Hy-Tek CL2 `D0` specification defines Column 66 (0-indexed 65) as the **swimmer's biological/competition gender** (`'M'` or `'F'`), and Column 67 (0-indexed 66) as the **event gender category** (`'M'`, `'F'`, or `'X'`).
  * The legacy parser previously read index 66, which returned `'X'` and caused all swims from mixed-event meets to be skipped.
* **Fix Applied**: Updated both [`pipeline.py`](file:///home/jrl/Projects/Digital_Signage/pipeline.py) and [`cl2 parser.py`](file:///home/jrl/Projects/Digital_Signage/cl2%20parser.py) to read swimmer gender from index 65 first, with fallback to index 66.

### 3. Preferred Swimmer Name Aliases (`Gage Martin`)
* Added `SWIMMER_NAME_ALIASES` mapping to cleanly support swimmers who compete under their legal first name but go by their middle name or nickname on the record board:
  * `"Bransen G Martin"` / `"Martin, Bransen G"` -> **`"Gage Martin"`**.
* Integrated into [`pipeline.py`](file:///home/jrl/Projects/Digital_Signage/pipeline.py) and [`cl2 parser.py`](file:///home/jrl/Projects/Digital_Signage/cl2%20parser.py).

### 4. Virtual Board Verification
* Verified board rendering locally in `.venv` via headless Chromium and live browser at `http://localhost:8501`.
* Confirmed Gage Martin and Michael W Alred on the 13-14 Boys slide displaying correct typography, inline years `(2026)`, and electric neon green `NEW!` pulsing badges.
* Staged on feature branch `feature/spooky-splash-2026-updates` prior to physical pool TV deployment.

---

## 🔮 Next Steps & Future Ideas

1. **Web-Based Meet Upload Portal (Next Priority)**:
   - Build a lightweight web upload page (e.g. `/admin` or dedicated route) accessible from any phone or laptop over the pool Wi-Fi / Tailscale.
   - Allows coaches to drag and drop a new Hy-Tek `.cl2` meet file directly.
   - Displays an instant in-browser preview of all broken records and time drops.
   - Includes a one-click **"Approve & Update Board"** button that executes `pipeline.py` and refreshes the live TV board automatically, completely eliminating the need for terminal commands or SSH.
   - Optional PIN or simple admin password protection.
2. **Retired Record Styling**: For the 9-10 girls 25 back record (Brooklyn Williams), add a distinctive teal border, a "RETIRED" badge, and update `pipeline.py` to prevent overwriting.
3. **LCM (Long Course Meters)**: Support for summer 50m long course season.

---

## 🚀 Quick Commands for Daily Operations

### General Operations
* **Activate Virtualenv**:
  ```bash
  source "/home/jrl/Projects/Digital_Signage/.venv/bin/activate"
  ```
* **Run Web App Locally**:
  ```bash
  streamlit run app.py
  ```
* **Process a New Swim Meet**:
  ```bash
  python3 pipeline.py --meet "/path/to/meet_results.cl2" --team MCSC
  ```
* **Sync Records to the Raspberry Pi**:
  ```bash
  ./sync.sh
  ```
* **Git Workflow (Push Updates to GitHub)**:
  ```bash
  git add .
  git commit -m "Describe your update"
  git push origin main
  ```

### Telegram Bot Management (`@mcsc_ticker_bot`)
* **Add an Assistant Coach**:
  1. Have the assistant coach message `@mcsc_ticker_bot` on Telegram and copy their Chat ID from the "Access Denied" reply.
  2. In your own chat with the bot, send:
     ```text
     /addcoach <Chat_ID>
     ```
  3. The bot immediately updates `bot_config.json` on the Pi and authorizes the coach.
* **Post an Announcement**: Simply type the text message directly in Telegram.
* **Reset Ticker**: Send `/clear` or `/stop` to return to the default team motto.
* **Change Default Motto**: Send `/setmotto <New Motto Text>`.

### Raspberry Pi Service Diagnostics (via SSH)
```bash
# Check status of all digital signage services
ssh pi@swim-signage "systemctl status swim-records-web swim-records-kiosk swim-ticker-bot"

# Restart all services
ssh pi@swim-signage "sudo systemctl restart swim-records-web swim-records-kiosk swim-ticker-bot"

# View live web app logs
ssh pi@swim-signage "journalctl -u swim-records-web.service -f"

# View live Telegram ticker bot logs
ssh pi@swim-signage "journalctl -u swim-ticker-bot.service -f"
```


