import os
import time
import requests

# Hardcoded API Credentials
RAPIDAPI_KEY = "48b9cd5744msh1445ae0d46782f7p1508c9jsn24c99c098d0a"
RAPIDAPI_HOST = "free-api-live-football-data.p.rapidapi.com"

# Target Endpoint
ENDPOINT_PATH = "football-current-live"

# Telegram Credentials (keep inside quotes)
TELEGRAM_BOT_TOKEN = "8911441513:AAGeoHoTDnIbjFEYaViqbFlfGDshcZV7YSA"
TELEGRAM_CHAT_ID = "6999628595"

CHECK_INTERVAL = 30
notified_matches = set()

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Telegram Bot Token or Chat ID missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"[ERR] Failed to send Telegram alert: {e}")

def scan_live_fixtures():
    if not RAPIDAPI_KEY:
        print("[WARN] RAPIDAPI_KEY is missing in script.")
        return

    url = f"https://{RAPIDAPI_HOST}/{ENDPOINT_PATH}"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY.strip(),
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"[ERR] API returned status {res.status_code}")
            return

        json_data = res.json()
        
        # Safely extract match array from the API response
        raw_data = json_data.get("response", [])
        if isinstance(raw_data, dict):
            data = raw_data.get("matches", raw_data.get("live", []))
        elif isinstance(raw_data, list):
            data = raw_data
        else:
            data = []

        print(f"[INFO] Connection Successful (Status 200)! Checking {len(data)} live matches...")

        for item in data:
            status = item.get("status", {})
            
            # Extract live match minute
            live_time = status.get("liveTime", {})
            elapsed_raw = live_time.get("short", 0) if isinstance(live_time, dict) else 0
            
            try:
                elapsed = int(elapsed_raw)
            except (ValueError, TypeError):
                elapsed = 0

            fixture_id = item.get("id")
            home_team = item.get("home", {}).get("name", "Home")
            away_team = item.get("away", {}).get("name", "Away")
            home_score = item.get("home", {}).get("score", 0)
            away_score = item.get("away", {}).get("score", 0)
            league_name = item.get("league", {}).get("name", "League")

            # Odds Estimation Model
            estimated_odds = round(1.05 + (elapsed * 0.0035), 2)

            # Strategy Criteria
            is_scoreless = (home_score == 0 or home_score is None) and (away_score == 0 or away_score is None)
            is_time_window = 15 <= elapsed <= 35
            is_odds_target = 1.15 <= estimated_odds <= 1.20

            if is_scoreless and is_time_window and is_odds_target:
                if fixture_id and fixture_id not in notified_matches:
                    msg = (
                        f"🚨 *OVER 0.5 GOAL OPPORTUNITY* 🚨\n\n"
                        f"🏆 *League:* {league_name}\n"
                        f"⚽ *Match:* {home_team} vs {away_team}\n"
                        f"⏱ *Time:* {elapsed}' (1st Half)\n"
                        f"📊 *Score:* {home_score} - {away_score}\n"
                        f"📈 *Estimated Odds:* {estimated_odds:.2f}\n\n"
                        f"⚡ *Action:* Check statistics before entry."
                    )
                    send_telegram_alert(msg)
                    notified_matches.add(fixture_id)
                    print(f"[ALERT SENT] {home_team} vs {away_team} ({elapsed}')")

    except Exception as e:
        print(f"[ERR] Scanning loop error: {e}")

def main():
    print("🚀 Over 0.5 Scanner Bot started...")
    send_telegram_alert("🚀 *Over 0.5 Goal Scanner online.* 24/7 Monitoring Active.")
    
    while True:
        scan_live_fixtures()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()