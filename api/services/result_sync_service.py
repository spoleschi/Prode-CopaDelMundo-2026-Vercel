from datetime import datetime, timezone

from services.football_data_service import (
    get_competition_matches,
    simplify_matches_response,
)
from services.supabase_service import get_supabase_admin_client
from services.scoring_service import recalculate_points_for_match


FINISHED_STATUSES = {"FINISHED"}


def build_external_matches_index():
    """
    Trae partidos de football-data y los indexa por external_id.
    """

    data = get_competition_matches(
        competition_code="WC",
        params={
            "season": "2026"
        }
    )

    summary = simplify_matches_response(data)

    external_matches = summary.get("matches", [])

    index = {}

    for match in external_matches:
        external_id = match.get("external_id")

        if external_id is None:
            continue

        index[str(external_id)] = match

    return index


def extract_full_time_score(external_match: dict):
    score = external_match.get("score") or {}
    full_time = score.get("full_time") or {}

    home_score = full_time.get("home")
    away_score = full_time.get("away")

    return home_score, away_score


def get_local_mapped_matches():
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("matches")
        .select("""
            id,
            external_provider,
            external_match_id,
            external_status,
            home_score,
            away_score,
            is_finished,
            match_date,
            home_team:home_team_id(id, name, code),
            away_team:away_team_id(id, name, code)
        """)
        .eq("external_provider", "football-data")
        .not_.is_("external_match_id", "null")
        .order("match_date")
        .execute()
    )

    return response.data or []


def preview_result_sync():
    """
    Compara resultados externos contra partidos locales.
    No actualiza la base.
    """

    external_index = build_external_matches_index()
    local_matches = get_local_mapped_matches()

    to_update = []
    already_updated = []
    not_finished = []
    missing_external = []
    invalid_score = []

    for local_match in local_matches:
        external_match_id = str(local_match.get("external_match_id"))
        external_match = external_index.get(external_match_id)

        if not external_match:
            missing_external.append({
                "local_match_id": local_match.get("id"),
                "external_match_id": external_match_id,
                "reason": "No existe en la respuesta actual de football-data."
            })
            continue

        external_status = external_match.get("status")

        if external_status not in FINISHED_STATUSES:
            not_finished.append({
                "local_match_id": local_match.get("id"),
                "external_match_id": external_match_id,
                "external_status": external_status,
                "home": (local_match.get("home_team") or {}).get("code"),
                "away": (local_match.get("away_team") or {}).get("code"),
            })
            continue

        external_home_score, external_away_score = extract_full_time_score(external_match)

        if external_home_score is None or external_away_score is None:
            invalid_score.append({
                "local_match_id": local_match.get("id"),
                "external_match_id": external_match_id,
                "external_status": external_status,
                "reason": "El partido figura finalizado pero no tiene score full_time completo."
            })
            continue

        local_home_score = local_match.get("home_score")
        local_away_score = local_match.get("away_score")
        local_is_finished = local_match.get("is_finished")

        same_result = (
            local_home_score == external_home_score
            and local_away_score == external_away_score
            and local_is_finished is True
            and local_match.get("external_status") == external_status
        )

        item = {
            "local_match_id": local_match.get("id"),
            "external_match_id": external_match_id,
            "external_status": external_status,
            "home": (local_match.get("home_team") or {}).get("code"),
            "away": (local_match.get("away_team") or {}).get("code"),
            "local_score": {
                "home": local_home_score,
                "away": local_away_score,
                "is_finished": local_is_finished,
            },
            "external_score": {
                "home": external_home_score,
                "away": external_away_score,
            }
        }

        if same_result:
            already_updated.append(item)
        else:
            to_update.append(item)

    return {
        "local_mapped_count": len(local_matches),
        "external_count": len(external_index),
        "to_update_count": len(to_update),
        "already_updated_count": len(already_updated),
        "not_finished_count": len(not_finished),
        "missing_external_count": len(missing_external),
        "invalid_score_count": len(invalid_score),
        "to_update": to_update,
        "already_updated": already_updated,
        "not_finished": not_finished,
        "missing_external": missing_external,
        "invalid_score": invalid_score,
    }


def apply_result_sync():
    """
    Actualiza resultados locales usando football-data.
    Solo actualiza partidos FINISHED con score válido.
    Recalcula puntos después de cada actualización.
    """

    preview = preview_result_sync()

    supabase = get_supabase_admin_client()

    updated = []
    errors = []

    now_iso = datetime.now(timezone.utc).isoformat()

    for item in preview["to_update"]:
        try:
            local_match_id = item["local_match_id"]
            external_score = item["external_score"]

            response = (
                supabase
                .table("matches")
                .update({
                    "home_score": external_score["home"],
                    "away_score": external_score["away"],
                    "is_finished": True,
                    "external_status": item["external_status"],
                    "last_synced_at": now_iso,
                })
                .eq("id", local_match_id)
                .execute()
            )

            recalculate_points_for_match(local_match_id)

            updated.append({
                "local_match_id": local_match_id,
                "external_match_id": item["external_match_id"],
                "home": item["home"],
                "away": item["away"],
                "score": external_score,
                "response": response.data,
            })

        except Exception as e:
            errors.append({
                "local_match_id": item.get("local_match_id"),
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