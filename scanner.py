import json
import re
import time
import requests

# --- CONFIGURATION ---
API_KEY = "48b9cd5744msh1445ae0d46782f7p1508c9jsn24c99c098d0a"
HOST = "free-api-live-football-data.p.rapidapi.com"
API_URL = f"https://{HOST}/football-current-live"

HEADERS = {
    "x-rapidapi-host": HOST,
    "x-rapidapi-key": API_KEY,
    "Content-Type": "application/json",
}


def parse_score_value(val):
    """Safely convert any score representation into an integer."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def fetch_live_matches():
    try:
        print("[*] Fetching live scores from RapidAPI...")
        res = requests.get(API_URL, headers=HEADERS, timeout=10)

        if res.status_code != 200:
            print(f"[!] API Error: {res.status_code}")
            return []

        raw_data = res.json()

        # Extract live array
        response_obj = raw_data.get("response", {})
        if isinstance(response_obj, dict):
            matches_list = response_obj.get("live", [])
        elif isinstance(response_obj, list):
            matches_list = response_obj
        else:
            matches_list = []

        print(f"[*] Found {len(matches_list)} live matches!")

        output_matches = []

        for match in matches_list:
            if not isinstance(match, dict):
                continue

            fixture_id = match.get("id", match.get("matchId", 0))

            # 1. Parse Home & Away Team Names
            home_data = match.get("home", {})
            away_data = match.get("away", {})

            if isinstance(home_data, dict):
                home_team = home_data.get("name") or home_data.get("shortName") or "Home"
            else:
                home_team = str(home_data) if home_data else "Home"

            if isinstance(away_data, dict):
                away_team = away_data.get("name") or away_data.get("shortName") or "Away"
            else:
                away_team = str(away_data) if away_data else "Away"

            # 2. Robust Multi-Fallback Score Parsing
            home_score = None
            away_score = None

            # Fallback A: Direct score field in team object
            if isinstance(home_data, dict) and "score" in home_data:
                home_score = home_data.get("score")
            if isinstance(away_data, dict) and "score" in away_data:
                away_score = away_data.get("score")

            # Fallback B: Embedded scores object
            scores_obj = match.get("scores", match.get("score", {}))
            if isinstance(scores_obj, dict):
                if home_score is None:
                    home_score = scores_obj.get("home") or scores_obj.get("homeScore")
                if away_score is None:
                    away_score = scores_obj.get("away") or scores_obj.get("awayScore")

            # Fallback C: String score like "2 - 1" or "2-1"
            if home_score is None or away_score is None:
                score_str = match.get("scoreStr") or match.get("statusReason") or ""
                if isinstance(score_str, str) and "-" in score_str:
                    parts = score_str.split("-")
                    if len(parts) == 2:
                        home_score = parts[0].strip()
                        away_score = parts[1].strip()

            # Final integer formatting
            home_score = parse_score_value(home_score)
            away_score = parse_score_value(away_score)

            # 3. Parse Elapsed Time & Half
            status_data = match.get("status", {})
            elapsed = 0
            status_short = "1H"

            if isinstance(status_data, dict):
                elapsed = status_data.get("elapsed") or status_data.get("liveTime") or 0
                reason = status_data.get("reason", {})
                if isinstance(reason, dict):
                    status_short = reason.get("short", "1H")
                elif isinstance(status_data.get("short"), str):
                    status_short = status_data.get("short")
            elif isinstance(status_data, (int, str)):
                elapsed = status_data

            # Try to pull numbers from elapsed if formatted as "32'"
            if isinstance(elapsed, str):
                match_digits = re.search(r"\d+", elapsed)
                elapsed = int(match_digits.group()) if match_digits else 0

            # 4. Parse Odds
            odds_val = match.get("odds", 1.24)
            try:
                real_odd = float(odds_val)
            except (ValueError, TypeError):
                real_odd = 1.24

            # 5. Parse League & Country
            league_name = (
                match.get("leagueName")
                or match.get("league", {}).get("name")
                if isinstance(match.get("league"), dict)
                else "Global League"
            )
            country_name = (
                match.get("countryName")
                or match.get("league", {}).get("country")
                if isinstance(match.get("league"), dict)
                else "World"
            )

            match_entry = {
                "id": fixture_id,
                "league": league_name or "Global League",
                "country": country_name or "World",
                "home": home_team,
                "away": away_team,
                "elapsed": elapsed,
                "homeScore": home_score,
                "awayScore": away_score,
                "statusShort": status_short or "1H",
                "odds": round(real_odd, 2),
                "conf": 80,
            }

            output_matches.append(match_entry)

        return output_matches

    except Exception as e:
        print(f"[!] Error processing data: {e}")
        return []


def save_to_json():
    matches = fetch_live_matches()
    if matches:
        with open("matches.json", "w", encoding="utf-8") as f:
            json.dump(matches, f, indent=2)
        print(
            f"[{time.strftime('%H:%M:%S')}] Successfully saved {len(matches)} live matches to matches.json!"
        )
    else:
        print(f"[{time.strftime('%H:%M:%S')}] No live matches returned.")


if __name__ == "__main__":
    save_to_json()