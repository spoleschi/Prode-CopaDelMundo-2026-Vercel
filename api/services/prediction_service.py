from services.match_service import get_match
from services.policy_service import can_predict, validate_score
from services.supabase_service import get_supabase_admin_client


def get_predictions_by_user(user_id: str):
    supabase = get_supabase_admin_client()

    response = (
        supabase.table("predictions")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []


def save_prediction(user_id: str, match_id: int, home_score: int, away_score: int):
    supabase = get_supabase_admin_client()

    match = get_match(match_id)
    home_score = validate_score(home_score, "goles local")
    away_score = validate_score(away_score, "goles visitante")

    allowed, reason = can_predict(match)
    if not allowed:
        raise ValueError(reason)

    data = {
        "user_id": user_id,
        "match_id": match_id,
        "home_score": home_score,
        "away_score": away_score,
    }

    response = (
        supabase.table("predictions")
        .upsert(data, on_conflict="user_id,match_id")
        .execute()
    )

    return response.data


def save_predictions_batch(user_id: str, predictions: list[dict]):
    saved_count = 0
    errors = []

    for item in predictions:
        match_id = item["match_id"]
        home_score = item["home_score"]
        away_score = item["away_score"]

        try:
            save_prediction(
                user_id=user_id,
                match_id=match_id,
                home_score=home_score,
                away_score=away_score,
            )
            saved_count += 1

        except Exception as e:
            errors.append({"match_id": match_id, "error": str(e)})

    return {"saved_count": saved_count, "errors": errors}


def get_prediction_detail_by_user(user_id: str):
    supabase = get_supabase_admin_client()

    response = (
        supabase.table("predictions")
        .select(
            """
            id,
            user_id,
            match_id,
            home_score,
            away_score,
            points,
            created_at,
            updated_at,
            match:match_id(
                id,
                match_date,
                stage,
                home_score,
                away_score,
                is_finished,
                home_team:home_team_id(id, name, code, url_flag),
                away_team:away_team_id(id, name, code, url_flag)
            )
        """
        )
        .eq("user_id", user_id)
        .execute()
    )

    data = response.data or []
    return sorted(
        data,
        key=lambda item: (item.get("match") or {}).get("match_date") or "",
    )


def get_predictions_by_match(match_id: int, user_ids: list[str] | None = None):
    supabase = get_supabase_admin_client()

    if user_ids is not None and len(user_ids) == 0:
        return []

    query = (
        supabase.table("predictions")
        .select(
            """
            id,
            user_id,
            match_id,
            home_score,
            away_score,
            points,
            created_at,
            updated_at,
            profile:user_id(
                id,
                email,
                display_name
            )
        """
        )
        .eq("match_id", match_id)
    )

    if user_ids is not None:
        query = query.in_("user_id", user_ids)

    response = query.order("points", desc=True).execute()
    return response.data or []
