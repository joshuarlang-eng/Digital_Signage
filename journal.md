# 🏊 Swim Team Digital Signage — Project Journal

**Date**: September 27, 2026  
**Project**: MCSC Swim Team Digital Signage Board  
**Target Device**: Raspberry Pi OS Lite (64-bit Debian Bookworm), Wayland (`cage`), Chromium Kiosk  
**Working Directory**: `/home/jrl/Projects/Digital Signage V2` (Version 2)  
**Baseline Directory**: `/home/jrl/Projects/Digital Signage` (Version 1 — preserved intact)

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

## 🔮 Ideas & Potential Focus Areas for Version 2

When resuming work on Version 2, here are the top directions and feature ideas:
1. **Scrolling Announcement Ticker**: Add an ESPN-style scrolling ticker above the footer for practice updates, meet schedules, and announcements. Can be updated directly from a smartphone browser via Tailscale!
2. **Retired Record**: The 9-10 girls 25 back record held by Brooklyn Williams has been retired.  Add a teal border similar to the green new record border to this record card and update the pipeline script so this record is never updated.
3. **LCM (Long Course Meters) vs. SCY (Short Course Yards)**: Toggle or separate mode for summer long-course season vs. winter short-course season.

---

## 🚀 Quick Commands for Version 2

* **Activate V2 Virtualenv**:
  ```bash
  source "/home/jrl/Projects/Digital Signage V2/.venv/bin/activate"
  ```
* **Run Web App**:
  ```bash
  streamlit run app.py
  ```
* **Run Pipeline**:
  ```bash
  python3 pipeline.py --init-only
  # or with a meet file:
  python3 pipeline.py --meet "/path/to/meet.cl2" --team MCSC
  ```

