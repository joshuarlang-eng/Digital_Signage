# Project Context:
I am building a local digital signage solution for a swim team record board on a Raspberry Pi OS Lite (64-bit). The goal is to replace a manual Google Sheets/Slides workflow with a fully localized, offline-capable Python pipeline.

# Provided Assets:
I have placed two existing Python scripts in your working directory:
1. A script that parses a .cl2 swim meet results file and converts it to a CSV.
2. A script that compares that CSV against my master records file and updates the records when broken.
3. I also included my current records CSV

# The Tech Stack:
* Language: Python 3
* Web Framework: Streamlit (preferred for fast data dashboards) or Flask.
* Display Manager: cage (Wayland compositor) running chromium-browser in kiosk mode.
* OS: Raspberry Pi OS Lite (Debian-based).

# Agent Task List & Deliverables:

## Phase 1: Refactor the Data Pipeline
Please analyze the two Python scripts I provided.
* Merge them into a single, clean pipeline script.
* Instead of outputting a standalone CSV for a secondary script to read, pass the data directly in memory to the record-checking logic.
* Output the final updated records into a clean records.json or SQLite database that a web app can easily consume. 

## Phase 2: Build the Web App (Streamlit)
Please create a lightweight web application (app.py) that:
* Reads the new records.json or SQLite database output from Phase 1.
* Displays a dark-mode, high-contrast UI suitable for a TV.
* Automatically cycles/paginates through the different age groups and gender combinations every 10-15 seconds.

## Phase 3: System Configuration (systemd)
Please provide the exact shell commands and systemd .service file contents to:
* Set up a Python virtual environment and install dependencies.
* Create a systemd service that automatically launches the Python web app on boot.
* Create a second systemd service that launches cage and opens Chromium in fullscreen, locked to http://localhost:8501, ensuring no error dialogs or infobars appear.

# Working Guidelines:
* Write clean, modular code. Use standard libraries where possible.
* Do not rely on any external cloud APIs; this entire system must run locally on the Pi.
