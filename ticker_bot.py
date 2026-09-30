#!/usr/bin/env python3
"""
MCSC Swim Team Record Board - Telegram Ticker Bot
=================================================
A lightweight, zero-dependency background daemon that receives Telegram messages
from authorized coaches/admins and updates the live scrolling ticker on the pool display.

Commands:
    /start or /help   - Display usage and available commands
    /status           - Show current ticker text and timestamp
    /clear or /stop   - Clear the announcement and reset to default team motto
    <Any Message>     - Send any plain message to instantly update the ticker

Configuration:
    Loads from `bot_config.json` in the same directory, or environment variables:
    - TELEGRAM_BOT_TOKEN
    - TELEGRAM_ALLOWED_IDS (comma-separated chat IDs)
"""

import os
import sys
import json
import time
import signal
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "bot_config.json")
EXAMPLE_CONFIG_FILE = os.path.join(SCRIPT_DIR, "bot_config.example.json")
DEFAULT_TICKER_PATH = os.path.join(SCRIPT_DIR, "static", "ticker.json")

# Graceful shutdown flag
running = True


def signal_handler(signum, frame):
    global running
    print(f"\n[*] Received signal {signum}, stopping ticker bot...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_config() -> Dict[str, Any]:
    """Loads configuration from bot_config.json or environment."""
    config = {
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "allowed_chat_ids": [],
        "default_message": "🏊 Welcome to Marshall County Swim Club • Home of the Fly • Hard Work Pays Off • Go MCSC!",
        "ticker_file": DEFAULT_TICKER_PATH
    }

    env_ids = os.environ.get("TELEGRAM_ALLOWED_IDS")
    if env_ids:
        config["allowed_chat_ids"] = [int(x.strip()) for x in env_ids.split(",") if x.strip().isdigit()]

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
                config.update(file_cfg)
        except Exception as e:
            print(f"[!] Warning reading {CONFIG_FILE}: {e}")
    elif not config["bot_token"]:
        print(f"[!] Configuration file '{CONFIG_FILE}' not found.")
        print(f"[i] Copy '{EXAMPLE_CONFIG_FILE}' to '{CONFIG_FILE}' and enter your bot token from @BotFather.")

    # Resolve relative ticker path
    if not os.path.isabs(config["ticker_file"]):
        config["ticker_file"] = os.path.join(SCRIPT_DIR, config["ticker_file"])

    return config


def get_current_ticker(ticker_file: str) -> Dict[str, Any]:
    """Reads current ticker data from disk."""
    if os.path.exists(ticker_file):
        try:
            with open(ticker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error reading ticker file: {e}")
    return {
        "text": "",
        "active": False,
        "is_default": True,
        "updated_at": "",
        "author": ""
    }


def write_ticker(ticker_file: str, text: str, author: str, is_default: bool = False) -> bool:
    """Safely writes updated ticker data to disk."""
    os.makedirs(os.path.dirname(ticker_file), exist_ok=True)
    payload = {
        "text": text.strip(),
        "active": bool(text.strip()),
        "is_default": is_default,
        "updated_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "author": author
    }
    tmp_file = f"{ticker_file}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, ticker_file)
        return True
    except Exception as e:
        print(f"[!] Error saving ticker file: {e}")
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass
        return False


def telegram_api_call(token: str, method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 35) -> Optional[Dict[str, Any]]:
    """Makes a Telegram Bot API request using the standard library."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        data = None
        headers = {"User-Agent": "MCSC-Signage-Bot/1.0"}
        if params:
            data = json.dumps(params).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
            if result.get("ok"):
                return result
            else:
                print(f"[!] Telegram API error in {method}: {result.get('description')}")
                return None
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        print(f"[!] HTTP error {e.code} in {method}: {err_msg}")
        return None
    except Exception as e:
        # Network timeout or DNS glitch
        return None


def send_telegram_reply(token: str, chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    """Sends a reply message to a Telegram chat."""
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    telegram_api_call(token, "sendMessage", params=params, timeout=10)


def process_message(config: Dict[str, Any], message: Dict[str, Any]) -> None:
    """Handles an incoming message from Telegram."""
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    from_user = message.get("from", {})
    first_name = from_user.get("first_name", "Coach")
    username = from_user.get("username", "")
    author = f"{first_name} (@{username})" if username else first_name

    text = message.get("text", "").strip()
    if not text or not chat_id:
        return

    allowed_ids = config.get("allowed_chat_ids", [])
    ticker_file = config.get("ticker_file", DEFAULT_TICKER_PATH)
    default_msg = config.get("default_message", "")

    # First-time auto-claim: if no IDs configured yet, the first user to message becomes primary admin
    if not allowed_ids:
        config["allowed_chat_ids"] = [chat_id]
        allowed_ids = config["allowed_chat_ids"]
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    file_cfg = json.load(f)
                file_cfg["allowed_chat_ids"] = [chat_id]
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(file_cfg, f, indent=2)
                print(f"[✓] Auto-claimed primary admin Chat ID: {chat_id} ({author})")
            except Exception as e:
                print(f"[!] Error saving claimed admin ID to config: {e}")

    # Security check: authorization
    if allowed_ids and (chat_id not in allowed_ids and str(chat_id) not in [str(x) for x in allowed_ids]):
        reply = (
            f"⛔ *Access Denied*\n\n"
            f"Your Telegram Chat ID is: `{chat_id}`\n\n"
            f"Share this ID with the MCSC Signage administrator to be added to the authorized coaches list."
        )
        send_telegram_reply(config["bot_token"], chat_id, reply)
        print(f"[!] Unauthorized attempt from ID {chat_id} ({author})")
        return

    # Help / Start command
    if text.startswith("/start") or text.startswith("/help"):
        help_msg = (
            f"🏊 *MCSC Record Board — Ticker Bot* 📢\n\n"
            f"Hi *{first_name}*! You are authorized to update the live board.\n\n"
            f"Simply type any message here and it will appear on the pool display within seconds!\n\n"
            f"*Commands:*\n"
            f"• Simply type your announcement (e.g. `Practice tomorrow 7am! Bring caps & fins.`)\n"
            f"• `/status` — View what's currently showing on the TV\n"
            f"• `/clear` — Reset ticker to default team motto\n"
            f"• `/motto` — View the current default team motto\n"
            f"• `/setmotto <text>` — Change the default team motto\n"
            f"• `/addcoach <id>` — Authorize another coach's Chat ID\n"
            f"• `/help` — Show this guide\n\n"
            f"_Your Chat ID:_ `{chat_id}`"
        )
        send_telegram_reply(config["bot_token"], chat_id, help_msg)
        return

    # Add another coach command
    if text.startswith("/addcoach"):
        parts = text.split()
        if len(parts) > 1 and parts[1].strip().isdigit():
            new_id = int(parts[1].strip())
            if new_id not in config["allowed_chat_ids"]:
                config["allowed_chat_ids"].append(new_id)
                if os.path.exists(CONFIG_FILE):
                    try:
                        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                            file_cfg = json.load(f)
                        file_cfg["allowed_chat_ids"] = config["allowed_chat_ids"]
                        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                            json.dump(file_cfg, f, indent=2)
                    except Exception:
                        pass
                send_telegram_reply(config["bot_token"], chat_id, f"✅ Added coach ID `{new_id}` to authorized list!")
                print(f"[✓] Coach ID {new_id} added by {author}")
            else:
                send_telegram_reply(config["bot_token"], chat_id, f"ℹ️ Coach ID `{new_id}` is already authorized.")
        else:
            send_telegram_reply(config["bot_token"], chat_id, "Usage: `/addcoach <Chat_ID>` (ask the coach to message this bot to get their Chat ID).")
        return

    # Set or view default team motto command
    if text.startswith("/setmotto") or text.startswith("/motto"):
        new_motto = text
        if new_motto.startswith("/setmotto"):
            new_motto = new_motto[len("/setmotto"):].strip()
        elif new_motto.startswith("/motto"):
            new_motto = new_motto[len("/motto"):].strip()

        if not new_motto:
            cur_motto = config.get("default_message", "")
            send_telegram_reply(
                config["bot_token"],
                chat_id,
                f"🏊 *Current Default Motto:*\n\n_{cur_motto}_\n\nTo update it, send:\n`/setmotto Your new team motto here`"
            )
            return

        config["default_message"] = new_motto
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    file_cfg = json.load(f)
                file_cfg["default_message"] = new_motto
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(file_cfg, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[!] Error saving new motto: {e}")

        # If board is currently showing default motto, update screen immediately
        current = get_current_ticker(ticker_file)
        if current.get("is_default", True):
            write_ticker(ticker_file, new_motto, author=author, is_default=True)

        reply = (
            f"✅ *Default Team Motto Updated!*\n\n"
            f"🏊 \"{new_motto}\"\n\n"
            f"_This will display whenever the ticker is cleared or when there are no active announcements._"
        )
        send_telegram_reply(config["bot_token"], chat_id, reply)
        print(f"[✓] Default motto updated by {author}: {new_motto}")
        return

    # Status command
    if text.startswith("/status"):
        current = get_current_ticker(ticker_file)
        c_text = current.get("text", "(None)")
        c_author = current.get("author", "Unknown")
        c_date = current.get("updated_at", "Unknown")
        is_def = current.get("is_default", False)
        status_label = "🟡 Default Team Motto" if is_def else "🟢 Active Announcement"

        status_msg = (
            f"📊 *Current Pool TV Ticker Status*\n\n"
            f"*Status:* {status_label}\n"
            f"*Message:* \"{c_text}\"\n"
            f"*Updated:* {c_date}\n"
            f"*Author:* {c_author}"
        )
        send_telegram_reply(config["bot_token"], chat_id, status_msg)
        return

    # Clear / Stop command
    if text.startswith("/clear") or text.startswith("/stop"):
        write_ticker(ticker_file, default_msg, author=author, is_default=True)
        reply = (
            f"✅ *Ticker Cleared*\n\n"
            f"The pool board has been reset to the default team motto:\n"
            f"_{default_msg}_"
        )
        send_telegram_reply(config["bot_token"], chat_id, reply)
        print(f"[✓] Ticker cleared by {author}")
        return

    # Update announcement text
    # Strip optional /ticker prefix
    new_text = text
    if new_text.startswith("/ticker"):
        new_text = new_text[len("/ticker"):].strip()

    if not new_text:
        send_telegram_reply(config["bot_token"], chat_id, "⚠️ Please provide message text, e.g. `/ticker Practice starts at 7am`")
        return

    # Save to ticker file
    if write_ticker(ticker_file, new_text, author=author, is_default=False):
        reply = (
            f"🎉 *Pool TV Ticker Updated!*\n\n"
            f"📢 *Displaying:*\n\"{new_text}\"\n\n"
            f"👤 *Author:* {author}\n"
            f"🕒 *Time:* {datetime.now().strftime('%I:%M %p')}\n\n"
            f"_The live board will display this message immediately._"
        )
        send_telegram_reply(config["bot_token"], chat_id, reply)
        print(f"[✓] Ticker updated by {author}: {new_text}")
    else:
        send_telegram_reply(config["bot_token"], chat_id, "❌ Error saving announcement to disk. Please check server logs.")


def main():
    print("=" * 60)
    print("🏊 MCSC Swim Signage — Telegram Ticker Bot Daemon")
    print("=" * 60)

    config = load_config()
    token = config.get("bot_token")

    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("[!] ERROR: No valid Telegram bot token configured.")
        print(f"[i] Open '{CONFIG_FILE}' and enter your bot token from @BotFather.")
        print("[i] Or run with: TELEGRAM_BOT_TOKEN='xxx' python3 ticker_bot.py")
        sys.exit(1)

    # Test bot credentials
    me_resp = telegram_api_call(token, "getMe")
    if not me_resp or not me_resp.get("result"):
        print("[!] Failed to connect to Telegram API. Check your bot token and internet connection.")
        sys.exit(1)

    bot_info = me_resp["result"]
    bot_username = bot_info.get("username", "Unknown")
    print(f"[✓] Connected successfully to Telegram bot: @{bot_username}")
    allowed = config.get("allowed_chat_ids", [])
    if allowed:
        print(f"[✓] Whitelisted Chat IDs: {allowed}")
    else:
        print("[!] NOTICE: No chat IDs in whitelist yet. The first message received will display your Chat ID.")

    print(f"[✓] Writing ticker updates to: {config['ticker_file']}")
    print("[*] Listening for incoming messages (long-polling)... Press Ctrl+C to stop.\n")

    offset = 0

    while running:
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset

        res = telegram_api_call(token, "getUpdates", params=params, timeout=40)
        if not running:
            break

        if res and "result" in res:
            updates = res["result"]
            for upd in updates:
                offset = max(offset, upd["update_id"] + 1)
                if "message" in upd:
                    process_message(config, upd["message"])
        else:
            # Short sleep if API error or connection glitch
            time.sleep(2)

    print("[*] Ticker bot stopped cleanly.")


if __name__ == "__main__":
    main()
