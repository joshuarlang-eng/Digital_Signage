#!/usr/bin/env python3
"""
Swim Team Record Pipeline
=========================
Parses Hy-Tek .cl2 swim meet results files, compares individual swims against
team records in-memory, updates broken records, and outputs clean data to
records.json, SQLite database, and CSV.

Designed for offline Raspberry Pi digital signage.
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Agegroup Bins: [0, 7) -> 6U, [7, 9) -> 8U, [9, 11) -> 9-10, [11, 13) -> 11-12, [13, 15) -> 13-14, 15+ -> Senior
AGE_BINS = [
    (0, 7, '6U'),
    (7, 9, '8U'),
    (9, 11, '9-10'),
    (11, 13, '11-12'),
    (13, 15, '13-14'),
    (15, 120, 'Senior')
]

AGE_ORDER = ['6U', '8U', '9-10', '11-12', '13-14', 'Senior']
GENDER_ORDER = ['F', 'M']

GENDER_DISPLAY = {
    'F': 'Girls',
    'M': 'Boys'
}

STROKE_TABLE = {
    '1': 'Free',
    '2': 'Back',
    '3': 'Breast',
    '4': 'Fly',
    '5': 'IM',
    '6': 'Free Relay',
    '7': 'Medley Relay'
}

STROKE_ORDER = {
    'Free': 1,
    'Back': 2,
    'Breast': 3,
    'Fly': 4,
    'IM': 5,
    'Free Relay': 6,
    'Medley Relay': 7
}


def parse_time_str(time_str: Optional[str]) -> Optional[float]:
    """
    Parses a swim time string into float seconds.
    Examples:
        '18.99' -> 18.99
        '1:04.42Y' -> 64.42
        '19:34.22' -> 1174.22
        'DQ', 'NS', 'SCR', '' -> None
    """
    if not time_str:
        return None

    clean = ''
    for char in time_str.strip():
        if char.isdigit() or char in ':.':
            clean += char
        elif char in ('Y', 'L', 'S', 'y', 'l', 's'):
            # Standard swim course suffixes
            continue

    if not clean or clean.count('.') > 1:
        return None

    try:
        if ':' in clean:
            parts = clean.split(':')
            if len(parts) == 2:
                mins = int(parts[0])
                secs = float(parts[1])
                return round(mins * 60.0 + secs, 2)
            elif len(parts) == 3:
                hrs = int(parts[0])
                mins = int(parts[1])
                secs = float(parts[2])
                return round(hrs * 3600.0 + mins * 60.0 + secs, 2)
        else:
            return round(float(clean), 2)
    except (ValueError, TypeError):
        return None


def format_time_display(seconds: Optional[float]) -> str:
    """
    Formats numeric seconds into standard swim time notation:
    18.99 -> '18.99'
    64.92 -> '1:04.92'
    1174.22 -> '19:34.22'
    """
    if seconds is None:
        return '--'
    if seconds < 60.0:
        return f"{seconds:.2f}"
    minutes = int(seconds // 60)
    rem_secs = seconds - (minutes * 60.0)
    return f"{minutes}:{rem_secs:05.2f}"


def get_agegroup(age: int) -> str:
    """Returns the age group bucket for a given swimmer age."""
    for low, high, label in AGE_BINS:
        if low <= age < high:
            return label
    return 'Senior'


def event_sort_key(event_name: str) -> Tuple[int, int]:
    """Sorts swim events by standard order: Free, Back, Breast, Fly, IM, then distance."""
    parts = event_name.strip().split(' ', 1)
    try:
        dist = int(parts[0])
    except (ValueError, IndexError):
        dist = 9999
    stroke = parts[1] if len(parts) > 1 else ''
    return (STROKE_ORDER.get(stroke, 99), dist)


# Preferred swimmer name overrides (for swimmers who go by middle names or nicknames)
SWIMMER_NAME_ALIASES = {
    'Bransen G Martin': 'Gage Martin',
    'Bransen Martin': 'Gage Martin',
    'Martin, Bransen G': 'Gage Martin',
    'Martin, Bransen': 'Gage Martin',
}


def clean_swimmer_name(raw_name: str) -> str:
    """
    Converts 'Last, First' into 'First Last' while stripping suffixes like ', Jr',
    and applying preferred swimmer name aliases.
    """
    cleaned = raw_name.strip()
    if cleaned in SWIMMER_NAME_ALIASES:
        return SWIMMER_NAME_ALIASES[cleaned]

    for suffix in [', Jr.', ', Jr', ', III', ', II', ', IV']:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)].strip()
    
    if ', ' in cleaned:
        parts = cleaned.split(', ', 1)
        formatted = f"{parts[1].strip()} {parts[0].strip()}"
    else:
        formatted = cleaned

    return SWIMMER_NAME_ALIASES.get(formatted, formatted)


def parse_cl2_meet(file_path: str, team_code: str = 'MCSC') -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parses a single .cl2 file for a specific team.
    Returns:
        meet_info: { 'name': str, 'start_date': str, 'end_date': str }
        swims: list of swim dicts
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CL2 file not found: {file_path}")

    with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
        lines = f.readlines()

    meet_name = "Swim Meet"
    meet_start = datetime.today().strftime('%Y-%m-%d')
    meet_end = meet_start

    # 1. Parse B1 Header for Meet Info
    for line in lines:
        if line.startswith('B1'):
            raw_name = line[11:41].strip()
            if raw_name:
                meet_name = raw_name

            raw_start = line[121:129].strip()
            if len(raw_start) == 8 and raw_start.isdigit():
                # Format: MMDDYYYY
                m, d, y = raw_start[0:2], raw_start[2:4], raw_start[4:8]
                meet_start = f"{y}-{m}-{d}"

            raw_end = line[129:137].strip()
            if len(raw_end) == 8 and raw_end.isdigit():
                m, d, y = raw_end[0:2], raw_end[2:4], raw_end[4:8]
                meet_end = f"{y}-{m}-{d}"
            break

    # 2. Parse D0 records for the target team
    in_team = False
    swims: List[Dict[str, Any]] = []

    for line in lines:
        if line.startswith('C1'):
            # Team header: team code is typically at [13:17] or in line[11:30]
            team_field = line[13:17].strip()
            in_team = (team_field.upper() == team_code.upper())
        elif line.startswith('Z0'):
            in_team = False
        elif in_team and line.startswith('D0'):
            swimmer_raw = line[11:39].strip()
            if not swimmer_raw:
                continue

            swimmer_name = clean_swimmer_name(swimmer_raw)
            age_raw = line[63:65].strip()
            try:
                age = int(age_raw)
            except ValueError:
                continue

            # Swimmer gender is at index 65 (col 66); event gender is at index 66 (col 67)
            # which can be 'X' in mixed/open-format meets.
            gender = line[65].strip().upper()
            if gender not in ('M', 'F'):
                gender = line[66].strip().upper()
            if gender not in ('M', 'F'):
                continue

            dist_raw = line[67:71].strip()
            stroke_code = line[71:72].strip()
            stroke = STROKE_TABLE.get(stroke_code, '')
            if not stroke or not dist_raw.isdigit():
                continue

            distance = int(dist_raw)
            event_name = f"{distance} {stroke}"
            agegroup = get_agegroup(age)

            entry_time_str = line[88:96].strip()
            prelim_time_str = line[97:106].strip()
            final_time_str = line[115:124].strip()

            entry_secs = parse_time_str(entry_time_str)
            prelim_secs = parse_time_str(prelim_time_str)
            final_secs = parse_time_str(final_time_str)

            valid_times = [t for t in (prelim_secs, final_secs) if t is not None]
            if not valid_times:
                continue

            fastest_secs = min(valid_times)

            swims.append({
                'name': swimmer_name,
                'age': age,
                'agegroup': agegroup,
                'gender': gender,
                'distance': distance,
                'stroke': stroke,
                'event': event_name,
                'entry_secs': entry_secs,
                'prelim_secs': prelim_secs,
                'final_secs': final_secs,
                'fastest_secs': fastest_secs,
                'meet_name': meet_name,
                'date': meet_start
            })

    meet_info = {
        'name': meet_name,
        'start_date': meet_start,
        'end_date': meet_end,
        'team_code': team_code,
        'total_swims_parsed': len(swims)
    }

    return meet_info, swims


def load_master_records_from_csv(csv_path: str) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """
    Loads master records from CSV.
    Expected CSV columns: Agegroup,Gender,Event,Time,Name,Date
    """
    records = {}
    if not os.path.exists(csv_path):
        return records

    import csv
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agegroup = row['Agegroup'].strip()
            gender = row['Gender'].strip().upper()
            event = row['Event'].strip()
            try:
                time_sec = float(row['Time'].strip())
            except ValueError:
                continue
            name = row['Name'].strip()
            date = row.get('Date', '').strip()

            key = (agegroup, gender, event)
            records[key] = {
                'agegroup': agegroup,
                'gender': gender,
                'event': event,
                'time_seconds': round(time_sec, 2),
                'name': name,
                'date': date,
                'is_new': False
            }
    return records


def update_records_in_memory(
    records: Dict[Tuple[str, str, str], Dict[str, Any]],
    swims: List[Dict[str, Any]],
    meet_name: str,
    meet_date: str
) -> List[Dict[str, Any]]:
    """
    Compares swims from meet against master records in-memory.
    Returns list of newly broken records.
    """
    # 1. Group swims by event to find fastest swim at this meet
    meet_best: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for s in swims:
        key = (s['agegroup'], s['gender'], s['event'])
        if key not in meet_best or s['fastest_secs'] < meet_best[key]['fastest_secs']:
            meet_best[key] = s

    broken_records = []

    # 2. Compare against current records
    for key, best_swim in meet_best.items():
        swim_time = best_swim['fastest_secs']
        swimmer = best_swim['name']
        agegroup, gender, event = key

        if key in records:
            current = records[key]
            current_time = current['time_seconds']
            if swim_time < current_time:
                # Record broken!
                record_info = {
                    'agegroup': agegroup,
                    'gender': gender,
                    'event': event,
                    'new_time': swim_time,
                    'new_time_formatted': format_time_display(swim_time),
                    'previous_time': current_time,
                    'previous_time_formatted': format_time_display(current_time),
                    'new_swimmer': swimmer,
                    'previous_swimmer': current['name'],
                    'previous_date': current['date'],
                    'meet_name': meet_name,
                    'date': meet_date,
                    'time_drop': round(current_time - swim_time, 2)
                }
                broken_records.append(record_info)

                # Update in-memory record
                records[key] = {
                    'agegroup': agegroup,
                    'gender': gender,
                    'event': event,
                    'time_seconds': swim_time,
                    'name': swimmer,
                    'date': meet_date,
                    'is_new': True
                }
        else:
            # First time record established
            record_info = {
                'agegroup': agegroup,
                'gender': gender,
                'event': event,
                'new_time': swim_time,
                'new_time_formatted': format_time_display(swim_time),
                'previous_time': None,
                'previous_time_formatted': None,
                'new_swimmer': swimmer,
                'previous_swimmer': 'None',
                'previous_date': '',
                'meet_name': meet_name,
                'date': meet_date,
                'time_drop': 0.0
            }
            broken_records.append(record_info)

            records[key] = {
                'agegroup': agegroup,
                'gender': gender,
                'event': event,
                'time_seconds': swim_time,
                'name': swimmer,
                'date': meet_date,
                'is_new': True
            }

    return broken_records


def build_records_json_structure(
    records: Dict[Tuple[str, str, str], Dict[str, Any]],
    team_name: str = "MCSC",
    meet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds structured dictionary for records.json optimized for digital signage.
    """
    groups_data = []

    for agegroup in AGE_ORDER:
        for gender in GENDER_ORDER:
            group_title = f"{agegroup} {GENDER_DISPLAY.get(gender, gender)}"
            
            # Find all records for this group
            group_records = []
            for (ag, gen, ev), rec in records.items():
                if ag == agegroup and gen == gender:
                    parts = ev.split(' ', 1)
                    dist = int(parts[0]) if parts[0].isdigit() else 0
                    stroke = parts[1] if len(parts) > 1 else ''

                    group_records.append({
                        'event': ev,
                        'stroke': stroke,
                        'distance': dist,
                        'time': rec['time_seconds'],
                        'time_formatted': format_time_display(rec['time_seconds']),
                        'name': rec['name'],
                        'date': rec['date'],
                        'is_new': rec.get('is_new', False)
                    })

            # Sort group records standard order
            group_records.sort(key=lambda r: event_sort_key(r['event']))

            groups_data.append({
                'agegroup': agegroup,
                'gender': gender,
                'gender_name': GENDER_DISPLAY.get(gender, gender),
                'title': group_title,
                'count': len(group_records),
                'records': group_records
            })

    # Flat records list
    flat_records = []
    for rec in records.values():
        flat_records.append({
            'agegroup': rec['agegroup'],
            'gender': rec['gender'],
            'event': rec['event'],
            'time': rec['time_seconds'],
            'time_formatted': format_time_display(rec['time_seconds']),
            'name': rec['name'],
            'date': rec['date'],
            'is_new': rec.get('is_new', False)
        })

    flat_records.sort(key=lambda r: (
        AGE_ORDER.index(r['agegroup']) if r['agegroup'] in AGE_ORDER else 99,
        GENDER_ORDER.index(r['gender']) if r['gender'] in GENDER_ORDER else 99,
        event_sort_key(r['event'])
    ))

    return {
        'last_updated': datetime.now().isoformat(),
        'team': team_name,
        'meet_processed': meet_name or "Initial Import",
        'total_records': len(records),
        'groups': groups_data,
        'records': flat_records
    }


def save_to_sqlite(
    db_path: str,
    records: Dict[Tuple[str, str, str], Dict[str, Any]],
    broken_records: List[Dict[str, Any]],
    meet_info: Optional[Dict[str, Any]] = None
) -> None:
    """Saves records and history log to SQLite database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agegroup TEXT NOT NULL,
            gender TEXT NOT NULL,
            event TEXT NOT NULL,
            time_seconds REAL NOT NULL,
            time_formatted TEXT NOT NULL,
            name TEXT NOT NULL,
            date TEXT,
            is_new INTEGER DEFAULT 0,
            UNIQUE(agegroup, gender, event)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS broken_records_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            meet_name TEXT,
            meet_date TEXT,
            agegroup TEXT NOT NULL,
            gender TEXT NOT NULL,
            event TEXT NOT NULL,
            new_time REAL NOT NULL,
            new_time_formatted TEXT NOT NULL,
            previous_time REAL,
            previous_time_formatted TEXT,
            new_swimmer TEXT NOT NULL,
            previous_swimmer TEXT,
            time_drop REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meet_name TEXT NOT NULL,
            meet_date TEXT,
            team_code TEXT,
            processed_at TEXT NOT NULL,
            records_broken_count INTEGER
        )
    """)

    # Insert or replace records
    for rec in records.values():
        cur.execute("""
            INSERT INTO records (agegroup, gender, event, time_seconds, time_formatted, name, date, is_new)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agegroup, gender, event) DO UPDATE SET
                time_seconds=excluded.time_seconds,
                time_formatted=excluded.time_formatted,
                name=excluded.name,
                date=excluded.date,
                is_new=excluded.is_new
        """, (
            rec['agegroup'],
            rec['gender'],
            rec['event'],
            rec['time_seconds'],
            format_time_display(rec['time_seconds']),
            rec['name'],
            rec['date'],
            1 if rec.get('is_new', False) else 0
        ))

    # Log broken records
    now_iso = datetime.now().isoformat()
    for b in broken_records:
        cur.execute("""
            INSERT INTO broken_records_history (
                timestamp, meet_name, meet_date, agegroup, gender, event,
                new_time, new_time_formatted, previous_time, previous_time_formatted,
                new_swimmer, previous_swimmer, time_drop
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now_iso,
            b.get('meet_name', ''),
            b.get('date', ''),
            b['agegroup'],
            b['gender'],
            b['event'],
            b['new_time'],
            b['new_time_formatted'],
            b.get('previous_time'),
            b.get('previous_time_formatted'),
            b['new_swimmer'],
            b.get('previous_swimmer', ''),
            b.get('time_drop', 0.0)
        ))

    if meet_info:
        cur.execute("""
            INSERT INTO meets (meet_name, meet_date, team_code, processed_at, records_broken_count)
            VALUES (?, ?, ?, ?, ?)
        """, (
            meet_info.get('name', 'Unknown Meet'),
            meet_info.get('start_date', ''),
            meet_info.get('team_code', ''),
            now_iso,
            len(broken_records)
        ))

    conn.commit()
    conn.close()


def save_master_records_to_csv(csv_path: str, records: Dict[Tuple[str, str, str], Dict[str, Any]]) -> None:
    """Exports master records back to CSV format for backup and spreadsheets."""
    import csv
    fieldnames = ['Agegroup', 'Gender', 'Event', 'Time', 'Name', 'Date']
    
    rows = []
    for rec in records.values():
        rows.append({
            'Agegroup': rec['agegroup'],
            'Gender': rec['gender'],
            'Event': rec['event'],
            'Time': rec['time_seconds'],
            'Name': rec['name'],
            'Date': rec['date']
        })

    # Sort CSV neatly
    rows.sort(key=lambda r: (
        AGE_ORDER.index(r['Agegroup']) if r['Agegroup'] in AGE_ORDER else 99,
        GENDER_ORDER.index(r['Gender']) if r['Gender'] in GENDER_ORDER else 99,
        event_sort_key(r['Event'])
    ))

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sync_to_pi(target: str, files: List[str]) -> bool:
    """
    Syncs generated files to the Raspberry Pi using rsync.
    Example target: 'pi@raspberrypi.local:/home/pi/Digital-Signage'
    """
    import subprocess
    print(f"\n[*] Syncing data to Raspberry Pi: {target}...")
    existing_files = [f for f in files if os.path.exists(f)]
    if not existing_files:
        print("[!] No files found to sync.")
        return False

    cmd = ["rsync", "-avz", "--progress"] + existing_files + [target]
    try:
        subprocess.run(cmd, check=True)
        print("[✓] Successfully synced records to Raspberry Pi!")

        # Trigger service restart on target host to refresh the TV kiosk display
        target_host = target.split(":")[0] if ":" in target else None
        if target_host:
            print(f"[*] Refreshing live TV display on {target_host}...")
            subprocess.run(
                ["ssh", "-o", "ConnectTimeout=10", target_host, "sudo systemctl restart swim-records-web swim-records-kiosk"],
                check=False
            )
            print("[✓] Live TV display refreshed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] rsync failed with return code {e.returncode}. Ensure SSH key access is configured.", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[!] 'rsync' command not found. Please install rsync (e.g. sudo apt install rsync).", file=sys.stderr)
        return False


def update_index_html_embedded_records(index_html_path: str, json_data: Dict[str, Any]) -> bool:
    """
    Updates the fallback embedded JSON block inside index.html so that local file:// viewing
    also reflects the latest meet data.
    """
    if not os.path.exists(index_html_path):
        return False
    try:
        with open(index_html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        start_tag = '<script id="embeddedRecords" type="application/json">'
        end_tag = '</script>'
        start_idx = content.find(start_tag)
        if start_idx == -1:
            return False

        end_idx = content.find(end_tag, start_idx + len(start_tag))
        if end_idx == -1:
            return False

        pretty_json = "\n" + json.dumps(json_data, indent=2) + "\n"
        new_content = content[:start_idx + len(start_tag)] + pretty_json + content[end_idx:]

        with open(index_html_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[✓] Synced embedded records inside: {index_html_path}")
        return True
    except Exception as e:
        print(f"[!] Note: Could not update embedded records in {index_html_path}: {e}")
        return False


def push_to_github(meet_name: Optional[str] = None, files_to_stage: Optional[List[str]] = None) -> bool:
    """
    Commits and pushes updated records files to GitHub so that GitHub Pages
    deploys the latest data to the live website (www.swimmcsc.com/scyrecords).
    """
    import subprocess
    print("\n[*] Pushing updated records to GitHub Pages...")
    if files_to_stage is None:
        files_to_stage = ["records.json", "records.sqlite", "SCY-Records.csv", "index.html"]

    # Check if inside git repo
    res = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if res.returncode != 0:
        print("[!] Not in a git repository. Skipping git push.")
        return False

    existing_files = [f for f in files_to_stage if os.path.exists(f)]
    if not existing_files:
        print("[!] No files found to stage for git push.")
        return False

    try:
        subprocess.run(["git", "add"] + existing_files, check=True)
        # Check if anything changed
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff.returncode == 0:
            print("[i] No git changes detected. GitHub Pages is already up to date.")
            return True

        commit_title = f"data: update team records from {meet_name}" if meet_name else "data: update team records"
        subprocess.run(["git", "commit", "-m", commit_title], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("[✓] Pushed to GitHub! Website (swimmcsc.com/scyrecords) will update in ~25 seconds.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Git push failed with return code {e.returncode}. (Check network or GitHub credentials)", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[!] Error during git push: {e}", file=sys.stderr)
        return False


def run_pipeline(
    meet_path: Optional[str] = None,
    master_csv: str = 'SCY-Records - 2-25-26.csv',
    team_code: str = 'MCSC',
    output_json: str = 'records.json',
    output_sqlite: str = 'records.sqlite',
    output_csv: str = 'SCY-Records.csv',
    index_html: str = 'index.html',
    pi_target: Optional[str] = None,
    push_github: bool = False
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Executes the entire data pipeline:
    1. Loads master records.
    2. If meet_path provided, parses .cl2 file, updates records in-memory.
    3. Writes records.json, SQLite database, and updated CSV.
    4. Updates embedded JSON in index.html.
    5. Optionally syncs files to Raspberry Pi.
    6. Optionally commits and pushes to GitHub Pages.
    """
    print("=" * 60)
    print("🏊 Swim Team Digital Signage Pipeline")
    print("=" * 60)

    # 1. Load current master records
    csv_to_load = master_csv if os.path.exists(master_csv) else output_csv
    if not os.path.exists(csv_to_load):
        raise FileNotFoundError(f"Master records CSV not found: {master_csv} or {output_csv}")

    print(f"[*] Loading master records from: {csv_to_load}")
    records = load_master_records_from_csv(csv_to_load)
    print(f"[✓] Loaded {len(records)} existing team records.")

    broken_records: List[Dict[str, Any]] = []
    meet_info: Optional[Dict[str, Any]] = None

    # 2. Process meet if provided
    if meet_path:
        print(f"[*] Parsing CL2 meet file: {meet_path}")
        print(f"[*] Filtering for team code: '{team_code}'")
        meet_info, swims = parse_cl2_meet(meet_path, team_code=team_code)
        print(f"[✓] Meet: '{meet_info['name']}' ({meet_info['start_date']})")
        print(f"[✓] Extracted {len(swims)} valid swims for team {team_code}.")

        print("[*] Comparing meet swims against master records in-memory...")
        broken_records = update_records_in_memory(
            records=records,
            swims=swims,
            meet_name=meet_info['name'],
            meet_date=meet_info['start_date']
        )

        if broken_records:
            print("\n🎉 NEW TEAM RECORDS BROKEN!")
            print("-" * 60)
            for b in broken_records:
                prev = f"{b['previous_time_formatted']} ({b['previous_swimmer']})" if b['previous_time'] else "None"
                print(f" • {b['agegroup']} {b['gender']} {b['event']:<12}: {b['new_swimmer']} -> {b['new_time_formatted']}  (Prev: {prev})")
            print("-" * 60)
            print(f"[✓] Total records broken/established: {len(broken_records)}\n")
        else:
            print("[i] No records broken at this meet.")

    # 3. Export to JSON
    json_data = build_records_json_structure(
        records=records,
        team_name=team_code,
        meet_name=meet_info['name'] if meet_info else "Manual Sync"
    )
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    print(f"[✓] Saved JSON dashboard records to: {output_json}")

    # 4. Export to SQLite
    save_to_sqlite(output_sqlite, records, broken_records, meet_info)
    print(f"[✓] Saved SQLite database to: {output_sqlite}")

    # 5. Export updated CSV
    save_master_records_to_csv(output_csv, records)
    print(f"[✓] Exported updated master CSV to: {output_csv}")

    # 6. Update embedded records in index.html
    update_index_html_embedded_records(index_html, json_data)

    # 7. Optional Sync to Pi
    if pi_target:
        sync_to_pi(pi_target, [output_json, output_sqlite, output_csv, "logo_transparent.png"])

    # 8. Optional Push to GitHub
    if push_github:
        push_to_github(
            meet_name=meet_info['name'] if meet_info else None,
            files_to_stage=[output_json, output_sqlite, output_csv, index_html]
        )

    print("=" * 60)

    return json_data, broken_records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Swim Team Records Pipeline")
    parser.add_argument('-m', '--meet', help="Path to .cl2 meet results file", default=None)
    parser.add_argument('-t', '--team', help="Team code (default: MCSC)", default="MCSC")
    parser.add_argument('-r', '--records', help="Path to current master records CSV", default="SCY-Records - 2-25-26.csv")
    parser.add_argument('--json', help="Output JSON path", default="records.json")
    parser.add_argument('--db', help="Output SQLite DB path", default="records.sqlite")
    parser.add_argument('--csv', help="Output updated CSV path", default="SCY-Records.csv")
    parser.add_argument('--html', help="Path to web records index.html", default="index.html")
    parser.add_argument('--init-only', action='store_true', help="Only initialize JSON and SQLite from CSV without processing a meet")
    parser.add_argument('--sync', metavar="USER@HOST:PATH", help="Sync output files to Raspberry Pi (e.g. pi@swim-signage:/home/pi/Digital-Signage)", default=None)
    parser.add_argument('--push', action=argparse.BooleanOptionalAction, default=True, help="Auto commit and push updated records to GitHub Pages (default: True)")

    args = parser.parse_args()

    meet_target = None if args.init_only else args.meet
    should_push = args.push if not args.init_only else False

    try:
        run_pipeline(
            meet_path=meet_target,
            master_csv=args.records,
            team_code=args.team,
            output_json=args.json,
            output_sqlite=args.db,
            output_csv=args.csv,
            index_html=args.html,
            pi_target=args.sync,
            push_github=should_push
        )
    except Exception as e:
        print(f"[!] Error running pipeline: {e}", file=sys.stderr)
        sys.exit(1)
