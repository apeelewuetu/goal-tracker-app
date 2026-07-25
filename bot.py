import os
import time
import json
import requests
import subprocess
import sys
import io

# -------------------------------------------------------------------
# Stream Encoding Configuration (UTF-8 Protection)
# -------------------------------------------------------------------
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')
except Exception:
    pass

from datetime import datetime, timedelta

# -------------------------------------------------------------------
# Configuration & Credentials
# -------------------------------------------------------------------
API_KEY = "36df2896f3ae0a6d33cd502d3a8hfaae"  # Your API-Sports Key
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "8911441513:AAGeoHoTDnIbjFEYaViqbF1fgDShcZV7YSA"
TELEGRAM_CHAT_ID = "6999628595"

# Polling interval during active matches (300s = 5 mins = ~12 calls/hr)
LIVE_POLL_INTERVAL = 300

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------
def log(msg):
    """Logs messages safely across all OS terminal encodings (e.g., Windows cp1252)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    try:
        print(formatted_msg)
    except UnicodeEncodeError:
        safe_msg = formatted_msg.encode(sys.stdout.encoding or 'utf-8', errors='ignore').decode('utf-8', errors='ignore')
        print(safe_msg)

def send_telegram_alert(message):
    """Sends a notification message to your Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log(f"⚠️ Telegram Alert Error: {e}")

def push_to_github():
    """Pushes matches.json updates directly to GitHub."""
    try:
        subprocess.run(["git", "add", "matches.json"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Auto-update live matches"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("🚀 Pushed updated 'matches.json' to GitHub repository!")
    except Exception:
        # Silently pass if no changes to commit or git process completes with code 1
        pass

def parse_int(val, default=0):
    """Safely convert numbers, strings, or None to integer."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# -------------------------------------------------------------------
# Core API Logic
# -------------------------------------------------------------------
def get_today_fixtures():
    """Fetch today's full match schedule to get kickoff times (1 API Call)."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures?date={today_str}"
    
    log(f"Fetching daily schedule for {today_str}...")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        remaining = res.headers.get("x-ratelimit-requests-remaining", "N/A")
        log(f"Daily API Quota Remaining: {remaining}")

        if res.status_code == 200:
            return res.json().get("response", [])
        elif res.status_code == 429:
            log("❌ Daily API quota limit reached.")
            send_telegram_alert("⚠️ <b>API-Sports Quota Alert:</b> Daily 100-request limit reached!")
            return None
        else:
            log(f"❌ API Error {res.status_code}: {res.text}")
            return None
    except Exception as e:
        log(f"❌ Network error fetching schedule: {e}")
        return None

def fetch_and_update_matches():
    """Fetches live matches from API-Sports, formats them, and updates matches.json."""
    url = f"{BASE_URL}/fixtures?live=all"
    
    try:
        log("🔄 Fetching live data from API-Sports...")
        res = requests.get(url, headers=HEADERS, timeout=15)

        if res.status_code != 200:
            log(f"❌ API Error: HTTP {res.status_code}")
            return False

        raw_data = res.json()
        matches_list = raw_data.get("response", [])
        
        if not matches_list:
            log("ℹ️ No live matches currently in progress.")
            # Save empty array so UI reflects zero live matches
            with open("matches.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            push_to_github()
            return False

        log(f"Found {len(matches_list)} live matches!")
        formatted_matches = []

        for idx, item in enumerate(matches_list):
            if not isinstance(item, dict):
                continue

            fixture = item.get("fixture", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})
            league = item.get("league", {})

            fixture_id = fixture.get("id") or (idx + 1)
            
            # Teams
            home_team = teams.get("home", {}).get("name", "Home Team")
            away_team = teams.get("away", {}).get("name", "Away Team")
            
            # Scores
            home_score = parse_int(goals.get("home"), 0)
            away_score = parse_int(goals.get("away"), 0)
            
            # Timing & Status
            status_obj = fixture.get("status", {})
            elapsed = parse_int(status_obj.get("elapsed"), 0)
            status_short = status_obj.get("short", "1H")
            
            # League & Country
            league_name = league.get("name", "Global League")
            country_name = league.get("country", "World")
            
            # Dynamic Live Odds Calculation for Over 0.5 Goals
            odds = float(round(1.08 + (elapsed * 0.005), 2))
            
            formatted_matches.append({
                "id": fixture_id,
                "league": league_name,
                "country": country_name,
                "home": home_team,
                "away": away_team,
                "elapsed": elapsed,
                "homeScore": home_score,
                "awayScore": away_score,
                "statusShort": status_short,
                "odds": odds,
                "conf": 80
            })

        # Write formatted match array to JSON
        with open("matches.json", "w", encoding="utf-8") as f:
            json.dump(formatted_matches, f, indent=2)

        log(f"Successfully updated 'matches.json' with {len(formatted_matches)} live games.")
        
        # Auto-push updates to GitHub repo
        push_to_github()
        return True

    except Exception as e:
        log(f"❌ Error during execution: {e}")
        return False

# -------------------------------------------------------------------
# Smart Execution Loop
# -------------------------------------------------------------------
def run_smart_scanner():
    log("🚀 Starting Match-Aware API-Sports Goal Scanner Bot...")
    send_telegram_alert("🚀 <b>Goal Scanner Bot Active</b>\nMonitoring live matches with API-Sports...")

    while True:
        fixtures = get_today_fixtures()
        
        if fixtures is None:
            log("Failed to retrieve schedule or quota limit hit. Waiting 1 hour...")
            time.sleep(3600)
            continue

        now = datetime.now()
        upcoming_kickoffs = []

        for f in fixtures:
            status = f.get("fixture", {}).get("status", {}).get("short", "")
            # NS = Not Started, 1H/2H/HT = Active Game
            if status in ["NS", "1H", "2H", "HT", "ET", "BT", "P"]:
                ts = f.get("fixture", {}).get("timestamp")
                if ts:
                    upcoming_kickoffs.append(datetime.fromtimestamp(ts))

        if not upcoming_kickoffs:
            log("All scheduled matches for today are complete. Sleeping until midnight...")
            tomorrow = datetime.now() + timedelta(days=1)
            midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 5, 0)
            sleep_time = (midnight - datetime.now()).total_seconds()
            time.sleep(max(sleep_time, 3600))
            continue

        earliest_kickoff = min(upcoming_kickoffs)
        
        # If games haven't started yet, sleep until 5 minutes before the first kickoff
        if earliest_kickoff > now:
            seconds_until_start = (earliest_kickoff - now).total_seconds() - 300
            if seconds_until_start > 0:
                mins = int(seconds_until_start // 60)
                log(f"Next match starts at {earliest_kickoff.strftime('%H:%M')}. Sleeping for {mins} minutes...")
                time.sleep(seconds_until_start)

        # Active Match Polling Loop
        log("Entering Active Match Monitoring Phase...")
        while True:
            has_live = fetch_and_update_matches()
            
            # Exit loop when no live matches remain
            if not has_live:
                log("No active live matches remaining. Re-checking daily schedule...")
                break
                
            time.sleep(LIVE_POLL_INTERVAL)

if __name__ == "__main__":
    run_smart_scanner()