from datetime import timedelta

from services.football_data_service import (
    get_competition_matches,
    simplify_matches_response,
)
from services.supabase_service import get_supabase_admin_client
from utils import parse_supabase_datetime


# Mapeo defensivo por si football-data usa un código distinto al tuyo.
# Ajustalo según tus teams.code reales si aparece algún "team_not_found".
TEAM_CODE_ALIASES = {
    "DZA": "ALG",   # Argelia, si tu tabla usa ALG
    "HTI": "HAI",   # Haití, si tu tabla usa HAI
}


def normalize_code(code: str | None) -> str | None:
    if not code:
        return None

    code = code.strip().upper()

    if not code or code == "TBD":
        return None

    return TEAM_CODE_ALIASES.get(code, code)


def is_defined_external_team(team: dict | None) -> bool:
    if not team:
        return False

    name = (team.get("name") or "").strip().upper()
    tla = (team.get("tla") or "").strip().upper()

    if not tla or tla == "TBD":
        return False

    if "TBD" in name:
        return False

    return True


def are_datetimes_close(dt1, dt2, tolerance_minutes: int = 10) -> bool:
    return abs(dt1 - dt2) <= timedelta(minutes=tolerance_minutes)


def get_team_code_id_map():
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("teams")
        .select("id, name, code")
        .execute()
    )

    rows = response.data or []

    return {
        normalize_code(row.get("code")): row
        for row in rows
        if normalize_code(row.get("code"))
    }


def get_local_knockout_matches():
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("matches")
        .select("""
            id,
            fifa_match_no,
            external_provider,
            external_match_id,
            external_status,
            match_date,
            stage,
            home_team_id,
            away_team_id,
            home_placeholder,
            away_placeholder,
            home_team:home_team_id(id, name, code),
            away_team:away_team_id(id, name, code)
        """)
        .gte("fifa_match_no", 73)
        .lte("fifa_match_no", 104)
        .order("fifa_match_no")
        .execute()
    )

    return response.data or []


def build_external_worldcup_index():
    data = get_competition_matches(
        competition_code="WC",
        params={
            "season": "2026"
        }
    )

    summary = simplify_matches_response(data)

    external_matches = summary.get("matches", [])

    by_external_id = {}
    knockout_candidates = []

    for match in external_matches:
        external_id = match.get("external_id")
        utc_date = match.get("utc_date")

        if external_id is not None:
            by_external_id[str(external_id)] = match

        dt = parse_supabase_datetime(utc_date)
        if not dt:
            continue

        # Nos interesan los partidos desde 16avos en adelante.
        # No dependemos del nombre exacto del stage externo.
        if dt.date().isoformat() >= "2026-06-28":
            knockout_candidates.append(match)

    return {
        "by_external_id": by_external_id,
        "knockout_candidates": knockout_candidates,
        "external_count": len(external_matches),
    }


def find_external_match_for_local(local_match: dict, external_index: dict):
    """
    Busca el partido externo.

    Prioridad:
    1. Si ya tiene external_match_id, usa ese.
    2. Si no, busca por fecha/hora UTC.
    """

    external_match_id = local_match.get("external_match_id")

    if external_match_id:
        match = external_index["by_external_id"].get(str(external_match_id))
        if match:
            return match

    local_dt = parse_supabase_datetime(local_match.get("match_date"))

    if not local_dt:
        return None

    candidates = []

    for external_match in external_index["knockout_candidates"]:
        external_dt = parse_supabase_datetime(external_match.get("utc_date"))

        if not external_dt:
            continue

        if are_datetimes_close(local_dt, external_dt, tolerance_minutes=10):
            candidates.append(external_match)

    if len(candidates) == 1:
        return candidates[0]

    return None


def preview_knockout_team_sync():
    """
    Compara los cruces locales contra football-data.
    No actualiza la base.
    """

    local_matches = get_local_knockout_matches()
    external_index = build_external_worldcup_index()
    team_map = get_team_code_id_map()

    to_update = []
    already_ok = []
    not_defined_yet = []
    missing_external = []
    team_not_found = []

    for local_match in local_matches:
        external_match = find_external_match_for_local(local_match, external_index)

        if not external_match:
            missing_external.append({
                "local_match_id": local_match.get("id"),
                "fifa_match_no": local_match.get("fifa_match_no"),
                "match_date": local_match.get("match_date"),
                "reason": "No se encontró partido externo por external_match_id ni por fecha/hora."
            })
            continue

        home_external = external_match.get("home_team") or {}
        away_external = external_match.get("away_team") or {}

        external_home_defined = is_defined_external_team(home_external)
        external_away_defined = is_defined_external_team(away_external)

        if not external_home_defined and not external_away_defined:
            not_defined_yet.append({
                "local_match_id": local_match.get("id"),
                "fifa_match_no": local_match.get("fifa_match_no"),
                "external_match_id": external_match.get("external_id"),
                "external_status": external_match.get("status"),
                "home_placeholder": local_match.get("home_placeholder"),
                "away_placeholder": local_match.get("away_placeholder"),
                "reason": "Todavía no hay equipos definidos en football-data."
            })
            continue

        home_code = normalize_code(home_external.get("tla"))
        away_code = normalize_code(away_external.get("tla"))

        home_team = team_map.get(home_code) if home_code else None
        away_team = team_map.get(away_code) if away_code else None

        missing_teams = []

        if external_home_defined and not home_team:
            missing_teams.append({
                "side": "home",
                "external_code": home_external.get("tla"),
                "normalized_code": home_code,
                "name": home_external.get("name"),
            })

        if external_away_defined and not away_team:
            missing_teams.append({
                "side": "away",
                "external_code": away_external.get("tla"),
                "normalized_code": away_code,
                "name": away_external.get("name"),
            })

        if missing_teams:
            team_not_found.append({
                "local_match_id": local_match.get("id"),
                "fifa_match_no": local_match.get("fifa_match_no"),
                "external_match_id": external_match.get("external_id"),
                "missing_teams": missing_teams,
            })
            continue

        new_home_team_id = home_team["id"] if home_team else local_match.get("home_team_id")
        new_away_team_id = away_team["id"] if away_team else local_match.get("away_team_id")

        same_home = local_match.get("home_team_id") == new_home_team_id
        same_away = local_match.get("away_team_id") == new_away_team_id
        same_external = str(local_match.get("external_match_id")) == str(external_match.get("external_id"))

        item = {
            "local_match_id": local_match.get("id"),
            "fifa_match_no": local_match.get("fifa_match_no"),
            "external_match_id": external_match.get("external_id"),
            "external_status": external_match.get("status"),
            "current": {
                "home_team_id": local_match.get("home_team_id"),
                "away_team_id": local_match.get("away_team_id"),
                "home": (local_match.get("home_team") or {}).get("code"),
                "away": (local_match.get("away_team") or {}).get("code"),
            },
            "external": {
                "home_code": home_external.get("tla"),
                "home_name": home_external.get("name"),
                "away_code": away_external.get("tla"),
                "away_name": away_external.get("name"),
            },
            "new": {
                "home_team_id": new_home_team_id,
                "away_team_id": new_away_team_id,
                "home_code": home_team.get("code") if home_team else None,
                "away_code": away_team.get("code") if away_team else None,
            }
        }

        if same_home and same_away and same_external:
            already_ok.append(item)
        else:
            to_update.append(item)

    return {
        "local_knockout_count": len(local_matches),
        "external_count": external_index["external_count"],
        "to_update_count": len(to_update),
        "already_ok_count": len(already_ok),
        "not_defined_yet_count": len(not_defined_yet),
        "missing_external_count": len(missing_external),
        "team_not_found_count": len(team_not_found),
        "to_update": to_update,
        "already_ok": already_ok,
        "not_defined_yet": not_defined_yet,
        "missing_external": missing_external,
        "team_not_found": team_not_found,
    }


def apply_knockout_team_sync():
    """
    Actualiza home_team_id / away_team_id de cruces eliminatorios.
    """

    preview = preview_knockout_team_sync()

    supabase = get_supabase_admin_client()

    updated = []
    errors = []

    for item in preview["to_update"]:
        try:
            update_data = {
                "external_provider": "football-data",
                "external_match_id": str(item["external_match_id"]),
                "external_status": item["external_status"],
            }

            # Solo seteamos el equipo si viene definido.
            if item["new"].get("home_team_id"):
                update_data["home_team_id"] = item["new"]["home_team_id"]

            if item["new"].get("away_team_id"):
                update_data["away_team_id"] = item["new"]["away_team_id"]

            response = (
                supabase
                .table("matches")
                .update(update_data)
                .eq("id", item["local_match_id"])
                .execute()
            )

            updated.append({
                "local_match_id": item["local_match_id"],
                "fifa_match_no": item["fifa_match_no"],
                "external_match_id": item["external_match_id"],
                "home_code": item["new"].get("home_code"),
                "away_code": item["new"].get("away_code"),
                "response": response.data,
            })

        except Exception as e:
            errors.append({
                "local_match_id": item.get("local_match_id"),
                "fifa_match_no": item.get("fifa_match_no"),
                "external_match_id": item.get("external_match_id"),
                "error": str(e),
            })

    return {
        "preview": preview,
        "updated_count": len(updated),
        "error_count": len(errors),
        "updated": updated,
        "errors": errors,
    }