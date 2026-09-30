#!/usr/bin/env python3
"""
Swim Team Record Board - Digital Signage Web App
================================================
A high-contrast, dark-mode TV digital signage dashboard built with Streamlit.
Cycles automatically through age groups and genders every 12 seconds.
Reads from records.json or records.sqlite.

Branded with:
- MCSC Fly Logo
- Blue: Pantone 299 C (#00A3E0)
- Green: Pantone 802 C (#44D62C)
"""

import os
import json
import base64
import sqlite3
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List

# Streamlit Page Config - Must be first Streamlit command
st.set_page_config(
    page_title="MCSC Swim Records Board",
    page_icon="🏊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(SCRIPT_DIR, "records.json")
DB_PATH = os.path.join(SCRIPT_DIR, "records.sqlite")
TICKER_PATH = os.path.join(SCRIPT_DIR, "static", "ticker.json")
LOGO_PNG_PATH = os.path.join(SCRIPT_DIR, "logo_transparent.png")
ORIG_LOGO_PATH = os.path.join(SCRIPT_DIR, "MCSC Fly Logo2.png")
CYCLE_INTERVAL_SEC = 12  # Seconds per age group on screen


def load_ticker_data() -> Dict[str, Any]:
    """Loads ticker announcement data from static/ticker.json."""
    if os.path.exists(TICKER_PATH):
        try:
            with open(TICKER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "text": "🏊 Welcome to Marshall County Swim Club • Home of the Fly • Hard Work Pays Off • Go MCSC!",
        "active": True,
        "is_default": True,
        "updated_at": "",
        "author": "System"
    }


@st.cache_data
def get_logo_base64() -> str:
    """Loads and caches the base64-encoded logo for self-contained HTML rendering."""
    # Ensure transparent logo exists
    if not os.path.exists(LOGO_PNG_PATH) and os.path.exists(ORIG_LOGO_PATH):
        try:
            from PIL import Image
            import numpy as np
            img = Image.open(ORIG_LOGO_PATH).convert('RGBA')
            data = np.array(img)
            r, g, b, a = data.T
            white_areas = (r > 240) & (g > 240) & (b > 240)
            data[..., 3][white_areas.T] = 0
            Image.fromarray(data).save(LOGO_PNG_PATH, 'PNG')
        except Exception:
            pass

    path_to_use = LOGO_PNG_PATH if os.path.exists(LOGO_PNG_PATH) else ORIG_LOGO_PATH
    if os.path.exists(path_to_use):
        try:
            with open(path_to_use, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return ""
    return ""


def load_records_data() -> Dict[str, Any]:
    """Loads records data from records.json, falling back to SQLite if needed."""
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error loading records.json: {e}. Falling back to SQLite...")

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT agegroup, gender, event, time_seconds, time_formatted, name, date, is_new
                FROM records
                ORDER BY agegroup, gender, id
            """)
            rows = cur.fetchall()
            conn.close()

            # Construct groups dictionary
            groups_map = {}
            for row in rows:
                ag, gen, ev, t_sec, t_fmt, name, dt, is_new = row
                key = (ag, gen)
                if key not in groups_map:
                    gender_name = "Girls" if gen == "F" else "Boys"
                    groups_map[key] = {
                        "agegroup": ag,
                        "gender": gen,
                        "gender_name": gender_name,
                        "title": f"{ag} {gender_name}",
                        "records": []
                    }
                groups_map[key]["records"].append({
                    "event": ev,
                    "time": t_sec,
                    "time_formatted": t_fmt,
                    "name": name,
                    "date": dt or "",
                    "is_new": bool(is_new)
                })

            groups = list(groups_map.values())
            return {
                "last_updated": datetime.now().isoformat(),
                "team": "MCSC",
                "meet_processed": "SQLite Database",
                "groups": groups,
                "total_records": len(rows)
            }
        except Exception as e:
            st.error(f"Error reading SQLite database: {e}")

    return {
        "team": "MCSC",
        "last_updated": datetime.now().isoformat(),
        "meet_processed": "No Data Found",
        "groups": [],
        "total_records": 0
    }


def render_kiosk_app():
    """Renders the fullscreen digital signage application."""
    data = load_records_data()
    groups = data.get("groups", [])
    team = data.get("team", "MCSC")
    last_updated = data.get("last_updated", "")
    logo_b64 = get_logo_base64()
    
    # Format date for display
    try:
        updated_dt = datetime.fromisoformat(last_updated).strftime("%b %d, %Y")
    except Exception:
        updated_dt = last_updated[:10] if last_updated else "Current"

    # Convert groups data to JSON for client-side rotation
    groups_json = json.dumps(groups)

    # Load ticker data
    ticker_data = load_ticker_data()
    ticker_json = json.dumps(ticker_data)
    initial_ticker_text = ticker_data.get("text", "")

    # Logo HTML
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="MCSC Logo" class="team-logo-img" />'
    else:
        logo_html = f'<div class="team-logo-fallback">{team}</div>'

    # HTML/CSS/JavaScript Signage Engine
    kiosk_html = f"""
    <!DOCTYPE html>
    <html lang="en" spellcheck="false">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{
                /* Official Pantone Colors */
                --pantone-blue: #00A3E0;    /* Pantone 299 C */
                --pantone-green: #44D62C;   /* Pantone 802 C */
                --blue-glow: rgba(0, 163, 224, 0.4);
                --green-glow: rgba(68, 214, 44, 0.45);

                /* Dark Theme Palette */
                --bg-primary: #070c18;
                --bg-card: rgba(13, 21, 38, 0.88);
                --border-color: rgba(0, 163, 224, 0.22);
                --border-card-hover: rgba(68, 214, 44, 0.5);
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
            }}

            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                user-select: none;
                -webkit-user-select: none;
            }}

            body, html {{
                width: 100%;
                height: 100%;
                overflow: hidden;
                background-color: var(--bg-primary);
                background-image: 
                    radial-gradient(circle at 15% 10%, rgba(0, 163, 224, 0.12) 0%, transparent 40%),
                    radial-gradient(circle at 85% 90%, rgba(68, 214, 44, 0.08) 0%, transparent 45%);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: var(--text-main);
            }}

            /* Top Progress Bar */
            #progress-bar-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 5px;
                background: rgba(255, 255, 255, 0.08);
                z-index: 1000;
            }}

            #progress-bar {{
                height: 100%;
                width: 100%;
                transform-origin: left center;
                transform: scaleX(0);
                background: linear-gradient(90deg, var(--pantone-blue), var(--pantone-green));
                box-shadow: 0 0 10px var(--green-glow);
                will-change: transform;
            }}

            /* Main Board Wrapper */
            #board-wrapper {{
                display: flex;
                flex-direction: column;
                height: 100vh;
                padding: 10px 28px 24px 28px;
            }}

            /* Header Section */
            header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding-bottom: 12px;
                border-bottom: 2px solid rgba(0, 163, 224, 0.28);
                margin-bottom: 12px;
                flex-shrink: 0;
            }}

            .team-brand {{
                display: flex;
                align-items: center;
                gap: 16px;
            }}

            .team-logo-img {{
                height: clamp(60px, 6.5vh, 76px);
                width: auto;
                max-width: 140px;
                object-fit: contain;
                filter: drop-shadow(0 2px 8px rgba(0, 163, 224, 0.4));
            }}

            .team-logo-fallback {{
                font-size: clamp(26px, 3.0vh, 32px);
                background: linear-gradient(135deg, var(--pantone-blue), #0077b6);
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 900;
                letter-spacing: 1.5px;
                color: #ffffff;
                box-shadow: 0 4px 15px var(--blue-glow);
            }}

            .team-title h1 {{
                font-size: clamp(21px, 2.5vh, 26px);
                font-weight: 900;
                letter-spacing: 1.2px;
                text-transform: uppercase;
                color: #ffffff;
            }}

            .team-title p {{
                font-size: clamp(12px, 1.4vh, 15px);
                color: var(--pantone-green);
                font-weight: 700;
                letter-spacing: 2px;
                text-transform: uppercase;
                text-shadow: 0 0 10px rgba(68, 214, 44, 0.3);
            }}

            /* Active Slide Title Banner */
            .group-banner {{
                display: flex;
                align-items: center;
                background: linear-gradient(135deg, rgba(0, 163, 224, 0.25), rgba(68, 214, 44, 0.15));
                border: 2px solid var(--pantone-blue);
                border-radius: 12px;
                padding: clamp(6px, 0.9vh, 10px) clamp(20px, 2.2vw, 32px);
                gap: 14px;
                box-shadow: 0 0 24px rgba(0, 163, 224, 0.25);
            }}

            .group-banner h2 {{
                font-size: clamp(28px, 3.6vh, 38px);
                font-weight: 900;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                color: #ffffff;
                text-shadow: 0 2px 10px rgba(0,0,0,0.6);
            }}

            .group-gender-tag {{
                font-size: clamp(13px, 1.5vh, 16px);
                font-weight: 900;
                padding: 4px 14px;
                border-radius: 6px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}

            .gender-f {{
                background: #ec4899;
                color: #ffffff;
                box-shadow: 0 0 10px rgba(236, 72, 153, 0.4);
            }}

            .gender-m {{
                background: var(--pantone-blue);
                color: #ffffff;
                box-shadow: 0 0 10px var(--blue-glow);
            }}

            .meta-info {{
                text-align: right;
            }}

            .clock-display {{
                font-size: clamp(25px, 3.2vh, 32px);
                font-weight: 800;
                font-variant-numeric: tabular-nums;
                color: var(--pantone-green);
                letter-spacing: 1px;
                text-shadow: 0 0 10px rgba(68, 214, 44, 0.4);
            }}

            .meta-sub {{
                font-size: clamp(11px, 1.3vh, 14px);
                color: var(--text-muted);
                letter-spacing: 1px;
            }}

            /* Grid Content */
            #slide-content {{
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                overflow: hidden;
                opacity: 1;
                transition: opacity 0.35s ease-in-out, transform 0.35s ease-in-out;
            }}

            .fade-out {{
                opacity: 0 !important;
                transform: translateY(8px);
            }}

            .records-grid {{
                display: grid;
                grid-auto-flow: column;
                grid-template-columns: repeat(3, 1fr);
                gap: clamp(6px, 1vh, 12px) clamp(12px, 1.4vw, 18px);
                width: 100%;
                height: 100%;
                max-height: calc(100vh - 195px);
            }}

            /* Record Card */
            .record-card {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: rgba(13, 21, 38, 0.95);
                border: 1px solid var(--border-color);
                border-radius: 10px;
                padding: clamp(6px, 1.2vh, 14px) clamp(12px, 1.4vw, 18px);
                position: relative;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
                transition: border-color 0.2s ease;
                min-height: 0;
            }}

            .record-card.is-new-record {{
                border: 1.5px solid var(--pantone-green);
                background: linear-gradient(135deg, rgba(68, 214, 44, 0.16), rgba(13, 21, 38, 0.95));
                box-shadow: 0 0 18px rgba(68, 214, 44, 0.35);
            }}

            .event-info {{
                display: flex;
                flex-direction: column;
                gap: 2px;
                max-width: 58%;
            }}

            .event-name {{
                font-size: clamp(17px, 2.5vh, 26px);
                font-weight: 800;
                color: var(--pantone-blue);
                letter-spacing: 0.5px;
                text-shadow: 0 1px 3px rgba(0,0,0,0.4);
            }}

            .swimmer-name {{
                font-size: clamp(16px, 2.3vh, 24px);
                font-weight: 700;
                color: #ffffff;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}

            .swimmer-date {{
                font-size: clamp(11px, 1.4vh, 15px);
                color: var(--text-muted);
                letter-spacing: 0.5px;
            }}

            .time-info {{
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
            }}

            .record-time {{
                font-size: clamp(28px, 4.2vh, 46px);
                font-weight: 900;
                font-variant-numeric: tabular-nums;
                color: var(--pantone-green);
                letter-spacing: 0.5px;
                text-shadow: 0 0 16px var(--green-glow);
            }}

            .new-badge {{
                display: inline-block;
                background: var(--pantone-green);
                color: #070c18;
                font-size: clamp(11px, 1.4vh, 13px);
                font-weight: 900;
                letter-spacing: 1px;
                padding: 2px 8px;
                border-radius: 4px;
                text-transform: uppercase;
                box-shadow: 0 0 10px var(--green-glow);
            }}

            /* Scrolling Announcement Ticker */
            .ticker-bar {{
                display: flex;
                align-items: center;
                height: clamp(30px, 3.5vh, 38px);
                background: rgba(13, 21, 38, 0.95);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 0 10px;
                margin-top: 6px;
                gap: 12px;
                flex-shrink: 0;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
            }}

            .ticker-badge {{
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 3px 10px;
                border-radius: 5px;
                font-size: clamp(10px, 1.2vh, 12px);
                font-weight: 900;
                letter-spacing: 1px;
                text-transform: uppercase;
                flex-shrink: 0;
                z-index: 2;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.4);
            }}

            .badge-announcement {{
                background: linear-gradient(135deg, var(--pantone-green), #2db51a);
                color: #070c18;
                box-shadow: 0 0 12px var(--green-glow);
            }}

            .badge-default {{
                background: linear-gradient(135deg, var(--pantone-blue), #0077b6);
                color: #ffffff;
                box-shadow: 0 0 10px var(--blue-glow);
            }}

            .pulse-dot {{
                width: 7px;
                height: 7px;
                background-color: #ef4444;
                border-radius: 50%;
                display: inline-block;
                box-shadow: 0 0 6px #ef4444;
            }}

            .ticker-track {{
                flex: 1;
                overflow: hidden;
                position: relative;
                display: flex;
                align-items: center;
                mask-image: linear-gradient(to right, transparent 0%, black 15px, black calc(100% - 15px), transparent 100%);
                -webkit-mask-image: linear-gradient(to right, transparent 0%, black 15px, black calc(100% - 15px), transparent 100%);
            }}

            .ticker-content {{
                display: inline-block;
                white-space: nowrap;
                padding-left: 100%;
                font-size: clamp(13px, 1.6vh, 17px);
                font-weight: 700;
                color: #f1f5f9;
                letter-spacing: 0.5px;
                will-change: transform;
            }}

            @keyframes ticker-scroll {{
                0% {{
                    transform: translate3d(0, 0, 0);
                }}
                100% {{
                    transform: translate3d(-100%, 0, 0);
                }}
            }}

            /* Navigation Pills Footer */
            footer {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding-top: 10px;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                margin-top: 10px;
                flex-shrink: 0;
            }}

            .pill-list {{
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }}

            .nav-pill {{
                font-size: clamp(11px, 1.3vh, 14px);
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.06);
                color: var(--text-muted);
                border: 1px solid rgba(255, 255, 255, 0.05);
                cursor: pointer;
                transition: all 0.2s ease;
            }}

            .nav-pill.active {{
                background: linear-gradient(135deg, var(--pantone-blue), var(--pantone-green));
                color: #070c18;
                border-color: var(--pantone-green);
                box-shadow: 0 0 12px var(--green-glow);
                font-weight: 900;
            }}

            .controls-hint {{
                font-size: 11px;
                color: rgba(148, 163, 184, 0.7);
                letter-spacing: 0.5px;
            }}

            /* Empty state */
            .no-records {{
                text-align: center;
                padding: 60px;
                font-size: 20px;
                color: var(--text-muted);
            }}

            /* 4K Ultra HD Scaling */
            @media (min-width: 2500px) or (min-height: 1400px) {{
                #board-wrapper {{
                    padding: 20px 48px 36px 48px;
                }}
                header {{
                    padding-bottom: 20px;
                    margin-bottom: 20px;
                }}
                .team-brand {{
                    gap: 28px;
                }}
                .team-logo-img {{
                    height: 110px !important;
                    max-width: 200px !important;
                }}
                .team-title h1 {{
                    font-size: 42px !important;
                    letter-spacing: 2px !important;
                }}
                .team-title p {{
                    font-size: 24px !important;
                    letter-spacing: 3px !important;
                }}
                .group-banner {{
                    padding: 12px 42px !important;
                    border-radius: 18px !important;
                    border-width: 3px !important;
                    gap: 24px !important;
                }}
                .group-banner h2 {{
                    font-size: 60px !important;
                    letter-spacing: 2.5px !important;
                }}
                .group-gender-tag {{
                    font-size: 24px !important;
                    padding: 6px 22px !important;
                    border-radius: 10px !important;
                }}
                .clock-display {{
                    font-size: 52px !important;
                }}
                .meta-sub {{
                    font-size: 22px !important;
                }}
                .records-grid {{
                    gap: clamp(12px, 1.2vh, 24px) clamp(20px, 1.4vw, 36px) !important;
                    max-height: calc(100vh - 350px) !important;
                }}
                .record-card {{
                    border-radius: 16px !important;
                    border-width: 2px !important;
                    padding: clamp(12px, 1.2vh, 22px) clamp(22px, 1.4vw, 34px) !important;
                }}
                .event-name {{
                    font-size: clamp(28px, 2.2vh, 46px) !important;
                }}
                .swimmer-name {{
                    font-size: clamp(26px, 2.0vh, 42px) !important;
                }}
                .swimmer-date {{
                    font-size: clamp(18px, 1.3vh, 26px) !important;
                }}
                .record-time {{
                    font-size: clamp(48px, 3.6vh, 80px) !important;
                }}
                .new-badge {{
                    font-size: 20px !important;
                    padding: 4px 14px !important;
                    border-radius: 6px !important;
                }}
                .ticker-bar {{
                    height: 56px !important;
                    border-radius: 12px !important;
                    padding: 0 18px !important;
                    margin-top: 12px !important;
                    gap: 18px !important;
                }}
                .ticker-badge {{
                    font-size: 20px !important;
                    padding: 6px 18px !important;
                    border-radius: 8px !important;
                }}
                .pulse-dot {{
                    width: 12px !important;
                    height: 12px !important;
                }}
                .ticker-content {{
                    font-size: 26px !important;
                    letter-spacing: 1px !important;
                }}
                footer {{
                    padding-top: 18px !important;
                    margin-top: 18px !important;
                }}
                .pill-list {{
                    gap: 14px !important;
                }}
                .nav-pill {{
                    font-size: 22px !important;
                    padding: 8px 18px !important;
                    border-radius: 10px !important;
                }}
                .controls-hint {{
                    font-size: 20px !important;
                }}
            }}
        </style>
    </head>
    <body spellcheck="false">
        <div id="progress-bar-container">
            <div id="progress-bar"></div>
        </div>

        <div id="board-wrapper">
            <header>
                <div class="team-brand">
                    {logo_html}
                    <div class="team-title">
                        <h1>Marshall County Swim Club</h1>
                        <p>Team Record Board • Short Course Yards</p>
                    </div>
                </div>

                <div class="group-banner">
                    <span id="gender-tag" class="group-gender-tag gender-f">Girls</span>
                    <h2 id="group-title">Loading...</h2>
                </div>

                <div class="meta-info">
                    <div id="clock" class="clock-display">00:00:00</div>
                    <div class="meta-sub">Updated: {updated_dt}</div>
                </div>
            </header>

            <main id="slide-content">
                <div id="records-container" class="records-grid"></div>
            </main>

            <div id="ticker-bar" class="ticker-bar">
                <div id="ticker-badge" class="ticker-badge badge-default">MCSC NEWS</div>
                <div class="ticker-track">
                    <div id="ticker-text" class="ticker-content">{initial_ticker_text}</div>
                </div>
            </div>

            <footer>
                <div id="pills-container" class="pill-list"></div>
                <div class="controls-hint">
                    <span id="pause-status">▶ Auto-Cycling</span> | [Space] Pause | [←/→] Navigate
                </div>
            </footer>
        </div>

        <script>
            const groups = {groups_json};
            const cycleDuration = {CYCLE_INTERVAL_SEC} * 1000;
            let currentIndex = 0;
            let isPaused = false;
            let startTime = Date.now();
            let timerAnimationId = null;

            // DOM Elements
            const groupTitleEl = document.getElementById("group-title");
            const genderTagEl = document.getElementById("gender-tag");
            const recordsContainer = document.getElementById("records-container");
            const slideContent = document.getElementById("slide-content");
            const progressBar = document.getElementById("progress-bar");
            const clockEl = document.getElementById("clock");
            const pillsContainer = document.getElementById("pills-container");
            const pauseStatusEl = document.getElementById("pause-status");

            // Live Clock
            function updateClock() {{
                const now = new Date();
                clockEl.textContent = now.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true }});
            }}
            setInterval(updateClock, 1000);
            updateClock();

            // Build Navigation Pills
            function createPills() {{
                pillsContainer.innerHTML = "";
                groups.forEach((g, idx) => {{
                    const pill = document.createElement("div");
                    pill.className = "nav-pill" + (idx === currentIndex ? " active" : "");
                    pill.textContent = `${{g.agegroup}} ${{g.gender}}`;
                    pill.onclick = () => {{
                        goToSlide(idx);
                    }};
                    pillsContainer.appendChild(pill);
                }});
            }}

            function updatePillActive() {{
                const pills = pillsContainer.children;
                for (let i = 0; i < pills.length; i++) {{
                    if (i === currentIndex) {{
                        pills[i].classList.add("active");
                    }} else {{
                        pills[i].classList.remove("active");
                    }}
                }}
            }}

            // Render Current Slide
            function renderSlide(index) {{
                if (!groups || groups.length === 0) {{
                    recordsContainer.innerHTML = "<div class='no-records'>No records found. Run pipeline.py to initialize.</div>";
                    return;
                }}

                const group = groups[index];
                groupTitleEl.textContent = group.title;
                
                // Gender styling
                genderTagEl.textContent = group.gender_name;
                genderTagEl.className = "group-gender-tag " + (group.gender === 'F' ? 'gender-f' : 'gender-m');

                // Dynamic row balancing for column-flow grid
                const recCount = (group.records && group.records.length) ? group.records.length : 0;
                const numRows = Math.max(1, Math.ceil(recCount / 3));
                const is4K = window.innerHeight > 1400;
                const minH = is4K ? "minmax(150px, 240px)" : "minmax(75px, 120px)";
                if (numRows >= 5) {{
                    recordsContainer.style.gridTemplateRows = "repeat(" + numRows + ", 1fr)";
                    recordsContainer.style.alignContent = "stretch";
                }} else {{
                    recordsContainer.style.gridTemplateRows = "repeat(" + numRows + ", " + minH + ")";
                    recordsContainer.style.alignContent = "center";
                }}

                // Generate cards
                let html = "";
                if (group.records && group.records.length > 0) {{
                    group.records.forEach(rec => {{
                        const newClass = rec.is_new ? " is-new-record" : "";
                        const newBadge = rec.is_new ? "<span class='new-badge'>NEW!</span>" : "";
                        const dateStr = rec.date ? rec.date : "";

                        html += `
                            <div class="record-card${{newClass}}">
                                <div class="event-info">
                                    <div class="event-name">${{rec.event}}</div>
                                    <div class="swimmer-name" title="${{rec.name}}">${{rec.name}}</div>
                                    <div class="swimmer-date">${{dateStr}}</div>
                                </div>
                                <div class="time-info">
                                    <div class="record-time">${{rec.time_formatted}}</div>
                                    ${{newBadge}}
                                </div>
                            </div>
                        `;
                    }});
                }} else {{
                    html = "<div class='no-records'>No records recorded for this group.</div>";
                }}

                recordsContainer.innerHTML = html;
                updatePillActive();
            }}

            // Progress Bar & Auto-Cycle Engine (Zero 60fps JS loops, GPU Compositor Only)
            let slideTimer = null;

            function startProgressBar() {{
                progressBar.style.transition = "none";
                progressBar.style.transform = "scaleX(0)";
                void progressBar.offsetWidth; // Force layout reflow so transition restarts cleanly
                if (!isPaused && groups.length > 1) {{
                    progressBar.style.transition = `transform ${{cycleDuration}}ms linear`;
                    progressBar.style.transform = "scaleX(1)";
                }}
            }}

            function scheduleNextSlide() {{
                clearTimeout(slideTimer);
                if (!isPaused && groups.length > 1) {{
                    slideTimer = setTimeout(() => {{
                        nextSlide();
                    }}, cycleDuration);
                }}
            }}

            function resetSlideTimer() {{
                clearTimeout(slideTimer);
                startProgressBar();
                scheduleNextSlide();
            }}

            function goToSlide(newIndex) {{
                if (groups.length === 0) return;
                clearTimeout(slideTimer);
                progressBar.style.transition = "none";
                progressBar.style.transform = "scaleX(0)";
                slideContent.classList.add("fade-out");
                setTimeout(() => {{
                    currentIndex = (newIndex + groups.length) % groups.length;
                    renderSlide(currentIndex);
                    slideContent.classList.remove("fade-out");
                    resetSlideTimer();
                }}, 350);
            }}

            function nextSlide() {{
                goToSlide(currentIndex + 1);
            }}

            function prevSlide() {{
                goToSlide(currentIndex - 1);
            }}

            // Keyboard Navigation
            document.addEventListener("keydown", (e) => {{
                if (e.code === "Space") {{
                    e.preventDefault();
                    isPaused = !isPaused;
                    pauseStatusEl.textContent = isPaused ? "⏸ PAUSED" : "▶ Auto-Cycling";
                    pauseStatusEl.style.color = isPaused ? "var(--pantone-green)" : "inherit";
                    if (isPaused) {{
                        clearTimeout(slideTimer);
                        const currentTransform = window.getComputedStyle(progressBar).transform;
                        progressBar.style.transition = "none";
                        progressBar.style.transform = currentTransform;
                    }} else {{
                        resetSlideTimer();
                    }}
                }} else if (e.code === "ArrowRight") {{
                    e.preventDefault();
                    nextSlide();
                }} else if (e.code === "ArrowLeft") {{
                    e.preventDefault();
                    prevSlide();
                }} else if (e.code === "KeyR") {{
                    window.location.reload();
                }}
            }});

            // Periodic auto-reload every 30 minutes to seamlessly pick up synced records
            setTimeout(() => {{
                window.location.reload();
            }}, 30 * 60 * 1000);

            // Scrolling Ticker Management
            const tickerTextEl = document.getElementById("ticker-text");
            const tickerBadgeEl = document.getElementById("ticker-badge");
            const initialTickerData = {ticker_json};
            let currentTickerText = initialTickerData.text || "";

            function applyTickerData(data) {{
                if (!data || !data.text || !data.active) {{
                    tickerTextEl.textContent = "🏊 Welcome to Marshall County Swim Club • Home of the Fly • Hard Work Pays Off • Go MCSC!";
                    tickerBadgeEl.textContent = "MCSC NEWS";
                    tickerBadgeEl.className = "ticker-badge badge-default";
                }} else {{
                    tickerTextEl.textContent = data.text;
                    if (data.is_default) {{
                        tickerBadgeEl.textContent = "MCSC NEWS";
                        tickerBadgeEl.className = "ticker-badge badge-default";
                    }} else {{
                        tickerBadgeEl.innerHTML = '<span class="pulse-dot"></span> ANNOUNCEMENT';
                        tickerBadgeEl.className = "ticker-badge badge-announcement";
                    }}
                }}

                // Adaptive speed: comfortable reading pace (~14 characters per second across screen)
                const charLen = Math.max(30, tickerTextEl.textContent.length);
                const duration = Math.max(16, Math.min(65, Math.round(charLen / 3.5)));

                tickerTextEl.style.animation = "none";
                void tickerTextEl.offsetWidth; // Force reflow to cleanly restart animation
                tickerTextEl.style.animation = `ticker-scroll ${{duration}}s linear infinite`;
            }}

            async function checkTickerUpdates() {{
                try {{
                    const resp = await fetch('/app/static/ticker.json?t=' + Date.now());
                    if (resp.ok) {{
                        const data = await resp.json();
                        const newText = (data.text || "").trim();
                        if (newText !== currentTickerText) {{
                            currentTickerText = newText;
                            applyTickerData(data);
                        }}
                    }}
                }} catch (e) {{
                    // Quietly ignore network failures in offline / kiosk mode
                }}
            }}

            // Initialize ticker & poll for updates every 10 seconds
            applyTickerData(initialTickerData);
            setInterval(checkTickerUpdates, 10000);

            // Initialize
            createPills();
            renderSlide(currentIndex);
            resetSlideTimer();
        </script>
    </body>
    </html>
    """

    # Inject CSS to hide all default Streamlit chrome for true kiosk TV display
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden; display: none !important;}
            footer {visibility: hidden; display: none !important;}
            header {visibility: hidden; display: none !important;}
            [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
            [data-testid="stDecoration"] {visibility: hidden; display: none !important;}
            [data-testid="stStatusWidget"] {visibility: hidden; display: none !important;}
            
            html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
                background-color: #070c18 !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
                width: 100vw !important;
                height: 100vh !important;
            }
            .main {
                background-color: #070c18 !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            .main > div {
                padding: 0 !important;
                margin: 0 !important;
                max-width: 100vw !important;
            }
            .block-container {
                padding: 0 !important;
                margin: 0 !important;
                max-width: 100vw !important;
                width: 100vw !important;
                height: 100vh !important;
            }
            [data-testid="stCustomComponentV1"] {
                width: 100vw !important;
                height: 100vh !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                z-index: 999999 !important;
            }
            iframe {
                border: none !important;
                width: 100vw !important;
                height: 100vh !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                outline: none !important;
                background-color: #070c18 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Render fullscreen kiosk HTML component
    st.components.v1.html(kiosk_html, height=1080, scrolling=False)


if __name__ == "__main__":
    render_kiosk_app()
