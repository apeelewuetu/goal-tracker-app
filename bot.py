import os
import time
import json
import requests
import subprocess

# -------------------------------------------------------------------
# Configuration & Credentials
# -------------------------------------------------------------------
RAPIDAPI_KEY = "48b9cd5744msh1445ae0d46782f7p1508c9jsn24c99c098d0a"
RAPIDAPI_HOST = "free-api-live-football-data.p.rapidapi.com"
ENDPOINT_PATH = "football-current-live"

API_URL = f"https://{RAPIDAPI_HOST}/{ENDPOINT_PATH}"

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "8911441513:AAGeoHoTDnIbjFEYaViqbF1fgDShcZV7YSA"
TELEGRAM_CHAT_ID = "6999628595"

CHECK_INTERVAL = 60

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------
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
        print(f"⚠️ Telegram Alert Error: {e}")

def push_to_github():
    """Pushes matches.json updates directly to GitHub."""
    try:
        subprocess.run(["git", "add", "matches.json"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Auto-update live matches"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("🚀 Pushed updated 'matches.json' to GitHub repository!")
    except Exception as e:
        # Silently log git failure if no changes or no remote configured
        pass

def parse_elapsed_time(status_dict):
    """Extracts live minute from liveTime dictionary."""
    if not isinstance(status_dict, dict):
        return 0
    live_time = status_dict.get("liveTime", {})
    if isinstance(live_time, dict):
        long_time = live_time.get("long", "")
        if ":" in str(long_time):
            try:
                return int(str(long_time).split(":")[0])
            except ValueError:
                pass
        short_time = live_time.get("short", "")
        clean_short = "".join(filter(str.isdigit, str(short_time)))
        if clean_short:
            return int(clean_short)
    return 0

def fetch_and_update_matches():
    """Fetches live matches safely based on API response structure."""
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    print(f"🔄 Fetching live data from {API_URL}...")

    try:
        response = requests.get(API_URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ API Error: HTTP {response.status_code} - {response.text}")
            return

        data = response.json()
        
        # Extract live games from the nested payload
        raw_matches = []
        if isinstance(data, dict):
            raw_matches = (
                data.get("response", {}).get("live") 
                or data.get("response", []) 
                or data.get("live") 
                or []
            )
        elif isinstance(data, list):
            raw_matches = data

        formatted_matches = []

        for idx, item in enumerate(raw_matches):
            if not isinstance(item, dict):
                continue

            fixture_id = item.get("id") or (idx + 1)
            
            # League Details
            league_name = item.get("leagueName") or "Global League"
            country_name = item.get("country") or "World"
            
            # Teams
            home_obj = item.get("home", {})
            away_obj = item.get("away", {})
            
            home_team = home_obj.get("name") or home_obj.get("longName") or "Home Team"
            away_team = away_obj.get("name") or away_obj.get("longName") or "Away Team"
            
            home_score = home_obj.get("score", 0)
            away_score = away_obj.get("score", 0)
            
            # Match Status & Timing
            status_obj = item.get("status", {})
            elapsed = parse_elapsed_time(status_obj)
            
            status_short = "2H" if elapsed > 45 else "1H"
            
            # Calculated Live Odds for Over 0.5 Goals
            odds = float(round(1.08 + (elapsed * 0.005), 2))
            
            formatted_matches.append({
                "id": fixture_id,
                "league": league_name,
                "country": country_name,
                "home": home_team,
                "away": away_team,
                "elapsed": elapsed,
                "homeScore": int(home_score) if home_score is not None else 0,
                "awayScore": int(away_score) if away_score is not None else 0,
                "statusShort": status_short,
                "odds": odds,
                "conf": 80
            })

        with open("matches.json", "w") as f:
            json.dump(formatted_matches, f, indent=2)

        print(f"✅ Successfully updated 'matches.json' with {len(formatted_matches)} live games.")
        
        # Auto-push updates to GitHub repo
        if len(formatted_matches) > 0:
            push_to_github()

    except Exception as e:
        print(f"❌ Error during execution: {e}")

# -------------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Starting Live Football Goal Scanner Bot...")
    send_telegram_alert("🚀 <b>Goal Scanner Bot Active</b>\nMonitoring live matches...")
    
    while True:
        fetch_and_update_matches()
        time.sleep(CHECK_INTERVAL)