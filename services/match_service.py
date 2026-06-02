from services.policy_service import can_admin_update_result, validate_score
from services.supabase_service import get_supabase_admin_client


def get_matches():
    supabase = get_supabase_admin_client()

    response = (
        supabase.table("matches")
        .select(
            """
            id,
            match_date,
            stage,
            home_score,
            away_score,
            is_finished,
            home_team:home_team_id(id, name, code, url_flag),
            away_team:away_team_id(id, name, code, url_flag)
        """
        )
        .order("match_date")
        .execute()
    )

    return response.data or []


def get_match(match_id: int):
    supabase = get_supabase_admin_client()

    response = (
        supabase.table("matches")
        .select("*")
        .eq("id", match_id)
        .single()
        .execute()
    )

    return response.data


def update_match_result(match_id: int, home_score: int, away_score: int):
    supabase = get_supabase_admin_client()
    match = get_match(match_id)
    home_score = validate_score(home_score, "goles local")
    away_score = validate_score(away_score, "goles visitante")

    allowed, reason = can_admin_update_result(match)
    if not allowed:
        raise ValueError(reason)

    response = (
        supabase.table("matches")
        .update(
            {
                "home_score": home_score,
                "away_score": away_score,
                "is_finished": True,
            }
        )
        .eq("id", match_id)
        .execute()
    )

    return response.data


def clear_match_result(match_id: int):
    supabase = get_supabase_admin_client()

    response = (
        supabase.table("matches")
        .update({"home_score": None, "away_score": None, "is_finished": False})
        .eq("id", match_id)
        .execute()
    )

    return response.data


def get_match_with_teams(match_id: int):
    supabase = get_supabase_admin_client()

    response = (
        supabase.table("matches")
        .select(
            """
            id,
            match_date,
            stage,
            home_score,
            away_score,
            is_finished,
            home_team:home_team_id(id, name, code, url_flag),
            away_team:away_team_id(id, name, code, url_flag)
        """
        )
        .eq("id", match_id)
        .single()
        .execute()
    )

    return response.data
