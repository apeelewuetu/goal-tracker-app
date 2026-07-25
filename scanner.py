import json
import time
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_KEY = "36df2896f3ae0a6d33cd502d3a8bfaae"  # Replace with your direct API-Sports Key
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# Polling interval during live matches (300s = 5 mins = ~12 calls/hr during games)
LIVE_POLL_INTERVAL = 300 

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def parse_int(val, default=0):
    """Safely convert numbers, strings, or None to integer."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

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
            log("[!] Daily quota exceeded or rate limit hit.")
            return None
        else:
            log(f"[!] API Error {res.status_code}: {res.text}")
            return None
    except Exception as e:
        log(f"[!] Network error fetching schedule: {e}")
        return None

def fetch_and_save_live_matches():
    """Fetch live matches, format data to match your UI schema, and update matches.json."""
    url = f"{BASE_URL}/fixtures?live=all"
    
    try:
        log("Fetching live scores from API-Sports...")
        res = requests.get(url, headers=HEADERS, timeout=10)

        if res.status_code != 200:
            log(f"[!] API Error: {res.status_code}")
            return False

        raw_data = res.json()
        matches_list = raw_data.get("response", [])
        
        if not matches_list:
            log("No live matches currently in progress.")
            # Clear or update matches.json with an empty list
            with open("matches.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            return False

        log(f"Found {len(matches_list)} live matches!")
        output_matches = []

        for match in matches_list:
            fixture = match.get("fixture", {})
            teams = match.get("teams", {})
            goals = match.get("goals", {})
            league = match.get("league", {})

            # 1. Parse Teams
            home_team = teams.get("home", {}).get("name", "Home")
            away_team = teams.get("away", {}).get("name", "Away")

            # 2. Parse Scores
            home_score = parse_int(goals.get("home"), 0)
            away_score = parse_int(goals.get("away"), 0)

            # 3. Parse Status & Time
            status_obj = fixture.get("status", {})
            elapsed = parse_int(status_obj.get("elapsed"), 0)
            status_short = status_obj.get("short", "1H")

            # 4. Parse League & Country
            league_name = league.get("name", "Global League")
            country_name = league.get("country", "World")

            # 5. Build Standard JSON Output Structure
            match_entry = {
                "id": fixture.get("id", 0),
                "league": league_name,
                "country": country_name,
                "home": home_team,
                "away": away_team,
                "elapsed": elapsed,
                "homeScore": home_score,
                "awayScore": away_score,
                "statusShort": status_short,
                "odds": 1.24,  # Standard fallback or placeholder
                "conf": 80,
            }

            output_matches.append(match_entry)

        # Save directly to matches.json for your dashboard/app
        with open("matches.json", "w", encoding="utf-8") as f:
            json.dump(output_matches, f, indent=2)
            
        log(f"Successfully saved {len(output_matches)} live matches to matches.json!")
        return True

    except Exception as e:
        log(f"[!] Error processing live data: {e}")
        return False

def run_smart_scanner():
    log("=== Starting Match-Aware API-Sports Scanner ===")
    
    while True:
        fixtures = get_today_fixtures()
        
        if fixtures is None:
            log("Failed to retrieve schedule. Waiting 1 hour before retry...")
            time.sleep(3600)
            continue

        now = datetime.now()
        upcoming_kickoffs = []

        for f in fixtures:
            status = f.get("fixture", {}).get("status", {}).get("short", "")
            # Active or upcoming status codes
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
        
        # If games haven't started yet, sleep until 5 minutes before kickoff
        if earliest_kickoff > now:
            seconds_until_start = (earliest_kickoff - now).total_seconds() - 300
            if seconds_until_start > 0:
                mins = int(seconds_until_start // 60)
                log(f"Next match starts at {earliest_kickoff.strftime('%H:%M')}. Sleeping for {mins} minutes...")
                time.sleep(seconds_until_start)

        # Active Match Polling Loop
        log("Entering Active Match Monitoring Phase...")
        while True:
            has_live = fetch_and_save_live_matches()
            
            # Exit loop when no live matches remain
            if not has_live:
                log("No active live matches remaining. Re-checking daily schedule...")
                break
                
            time.sleep(LIVE_POLL_INTERVAL)

if __name__ == "__main__":
    run_smart_scanner()