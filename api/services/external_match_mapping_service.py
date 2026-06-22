from datetime import timedelta

from services.match_service import get_matches
from services.supabase_service import get_supabase_admin_client
from services.football_data_service import (
    get_competition_matches,
    simplify_matches_response,
)
from utils import parse_supabase_datetime


def normalize_team_code(code: str | None) -> str | None:
    if not code:
        return None

    return code.strip().upper()


def get_local_match_key(match: dict):
    """
    Genera una clave comparable para un partido local:
    fecha UTC aproximada + código local + código visitante.
    """

    match_dt = parse_supabase_datetime(match.get("match_date"))

    if not match_dt:
        return None

    home_team = match.get("home_team") or {}
    away_team = match.get("away_team") or {}

    home_code = normalize_team_code(home_team.get("code"))
    away_code = normalize_team_code(away_team.get("code"))

    if not home_code or not away_code:
        return None

    return {
        "id": match.get("id"),
        "utc_datetime": match_dt,
        "home_code": home_code,
        "away_code": away_code,
    }


def get_external_match_key(match: dict):
    """
    Genera una clave comparable para un partido de football-data.
    """

    external_dt = parse_supabase_datetime(match.get("utc_date"))

    if not external_dt:
        return None

    home_team = match.get("home_team") or {}
    away_team = match.get("away_team") or {}

    home_code = normalize_team_code(home_team.get("tla"))
    away_code = normalize_team_code(away_team.get("tla"))

    if not home_code or not away_code:
        return None

    return {
        "external_id": match.get("external_id"),
        "utc_datetime": external_dt,
        "home_code": home_code,
        "away_code": away_code,
        "status": match.get("status"),
        "raw": match,
    }


def are_datetimes_close(dt1, dt2, tolerance_minutes: int = 10) -> bool:
    diff = abs(dt1 - dt2)
    return diff <= timedelta(minutes=tolerance_minutes)


def find_external_match_for_local(local_key: dict, external_keys: list[dict]):
    """
    Busca coincidencia exacta por:
    - home_code
    - away_code
    - fecha/hora cercana
    """

    candidates = []

    for external_key in external_keys:
        same_teams = (
            local_key["home_code"] == external_key["home_code"]
            and local_key["away_code"] == external_key["away_code"]
        )

        if not same_teams:
            continue

        same_time = are_datetimes_close(
            local_key["utc_datetime"],
            external_key["utc_datetime"],
            tolerance_minutes=10
        )

        if same_time:
            candidates.append(external_key)

    if len(candidates) == 1:
        return candidates[0]

    return None


def preview_worldcup_mapping():
    """
    No actualiza base.
    Solo muestra qué partidos locales matchean con football-data.
    """

    local_matches = get_matches()

    external_data = get_competition_matches(
        competition_code="WC",
        params={
            "season": "2026"
        }
    )

    external_summary = simplify_matches_response(external_data)
    external_matches = external_summary.get("matches", [])

    external_keys = []

    for external_match in external_matches:
        key = get_external_match_key(external_match)
        if key:
            external_keys.append(key)

    matched = []
    unmatched = []

    for local_match in local_matches:
        local_key = get_local_match_key(local_match)

        if not local_key:
            unmatched.append({
                "local_match_id": local_match.get("id"),
                "reason": "No se pudo generar clave local",
                "local_match": local_match,
            })
            continue

        external_key = find_external_match_for_local(local_key, external_keys)

        if external_key:
            matched.append({
                "local_match_id": local_match.get("id"),
                "external_match_id": external_key["external_id"],
                "external_status": external_key["status"],
                "home_code": local_key["home_code"],
                "away_code": local_key["away_code"],
                "local_utc": local_key["utc_datetime"].isoformat(),
                "external_utc": external_key["utc_datetime"].isoformat(),
            })
        else:
            unmatched.append({
                "local_match_id": local_match.get("id"),
                "reason": "No se encontró coincidencia por equipos y horario",
                "home_code": local_key["home_code"],
                "away_code": local_key["away_code"],
                "local_utc": local_key["utc_datetime"].isoformat(),
            })

    return {
        "local_count": len(local_matches),
        "external_count": len(external_matches),
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "matched": matched,
        "unmatched": unmatched,
    }


def apply_worldcup_mapping():
    """
    Actualiza matches.external_* con el ID de football-data.
    """

    preview = preview_worldcup_mapping()

    supabase = get_supabase_admin_client()

    updated = []
    errors = []

    for item in preview["matched"]:
        try:
            response = (
                supabase
                .table("matches")
                .update({
                    "external_provider": "football-data",
                    "external_match_id": str(item["external_match_id"]),
                    "external_status": item["external_status"],
                })
                .eq("id", item["local_match_id"])
                .execute()
            )

            updated.append({
                "local_match_id": item["local_match_id"],
                "external_match_id": item["external_match_id"],
                "response": response.data,
            })

        except Exception as e:
            errors.append({
                "local_match_id": item["local_match_id"],
                "external_match_id": item["external_match_id"],
                "error": str(e),
            })

    return {
        "preview": preview,
        "updated_count": len(updated),
        "error_count": len(errors),
        "updated": updated,
        "errors": errors,
    }