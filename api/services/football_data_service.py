import requests

from config import Config


BASE_URL = "https://api.football-data.org/v4"


class FootballDataApiError(Exception):
    pass


def football_data_get(path: str, params: dict | None = None):
    if not Config.FOOTBALL_DATA_TOKEN:
        raise FootballDataApiError("Falta configurar FOOTBALL_DATA_TOKEN.")

    url = f"{BASE_URL}{path}"

    headers = {
        "X-Auth-Token": Config.FOOTBALL_DATA_TOKEN
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15
        )
    except requests.RequestException as e:
        raise FootballDataApiError(
            f"Error de conexión con football-data.org: {e}"
        )

    if response.status_code == 429:
        raise FootballDataApiError("Rate limit alcanzado en football-data.org.")

    if response.status_code == 403:
        raise FootballDataApiError(
            "Token inválido o sin permisos para este recurso."
        )

    if response.status_code == 404:
        raise FootballDataApiError(
            "Recurso no encontrado en football-data.org."
        )

    if not response.ok:
        raise FootballDataApiError(
            f"Error football-data.org HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    return response.json()


def get_today_matches():
    return football_data_get("/matches")


def get_competitions():
    return football_data_get("/competitions")


def get_competition_matches(competition_code: str, params: dict | None = None):
    return football_data_get(
        f"/competitions/{competition_code}/matches",
        params=params
    )


def simplify_matches_response(data: dict):
    matches = data.get("matches", [])

    simplified = []

    for match in matches:
        score = match.get("score") or {}
        home_team = match.get("homeTeam") or {}
        away_team = match.get("awayTeam") or {}

        simplified.append({
            "external_id": match.get("id"),
            "utc_date": match.get("utcDate"),
            "status": match.get("status"),
            "stage": match.get("stage"),
            "group": match.get("group"),
            "matchday": match.get("matchday"),
            "home_team": {
                "id": home_team.get("id"),
                "name": home_team.get("name"),
                "short_name": home_team.get("shortName"),
                "tla": home_team.get("tla"),
            },
            "away_team": {
                "id": away_team.get("id"),
                "name": away_team.get("name"),
                "short_name": away_team.get("shortName"),
                "tla": away_team.get("tla"),
            },
            "score": {
                "winner": score.get("winner"),
                "duration": score.get("duration"),
                "full_time": score.get("fullTime"),
                "half_time": score.get("halfTime"),
            }
        })

    return {
        "count": len(simplified),
        "matches": simplified
    }