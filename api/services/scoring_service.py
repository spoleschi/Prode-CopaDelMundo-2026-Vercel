def get_result_type(home: int, away: int) -> str:
    if home > away:
        return "HOME"
    if home < away:
        return "AWAY"
    return "DRAW"


def calculate_points(pred_home: int, pred_away: int, real_home: int, real_away: int) -> int:
    """
    Regla inicial:
    - 3 puntos: resultado exacto
    - 1 punto: acierta ganador o empate
    - 0 puntos: no acierta
    """

    if pred_home == real_home and pred_away == real_away:
        return 3

    pred_result = get_result_type(pred_home, pred_away)
    real_result = get_result_type(real_home, real_away)

    if pred_result == real_result:
        return 1

    return 0


def get_prediction_result_label(pred_home: int, pred_away: int, real_home: int, real_away: int) -> str:
    """
    Devuelve una etiqueta semántica para estadísticas:
    - EXACT
    - RESULT
    - MISS
    """

    if pred_home == real_home and pred_away == real_away:
        return "EXACT"

    pred_result = get_result_type(pred_home, pred_away)
    real_result = get_result_type(real_home, real_away)

    if pred_result == real_result:
        return "RESULT"

    return "MISS"


def sort_ranking_rows(ranking: list[dict]) -> list[dict]:
    ranking.sort(
        key=lambda x: (
            x["points"],
            x["exact_count"],
            x["result_count"],
            -x["miss_count"],
        ),
        reverse=True,
    )

    for index, row in enumerate(ranking, start=1):
        row["position"] = index

    return ranking


def recalculate_points_for_match(match_id: int):
    from services.match_service import get_match
    from services.supabase_service import get_supabase_admin_client

    supabase = get_supabase_admin_client()

    match = get_match(match_id)

    if not match:
        raise ValueError("El partido no existe.")

    if not match.get("is_finished"):
        raise ValueError("El partido todavía no está finalizado.")

    real_home = match.get("home_score")
    real_away = match.get("away_score")

    predictions_response = (
        supabase
        .table("predictions")
        .select("*")
        .eq("match_id", match_id)
        .execute()
    )

    predictions = predictions_response.data or []

    for prediction in predictions:
        points = calculate_points(
            prediction["home_score"],
            prediction["away_score"],
            real_home,
            real_away
        )

        (
            supabase
            .table("predictions")
            .update({"points": points})
            .eq("id", prediction["id"])
            .execute()
        )


def get_ranking(group_id: int | None = None):
    """
    Ranking general o filtrado por grupo.

    Si group_id es None:
        muestra todos los usuarios.

    Si group_id tiene valor:
        muestra únicamente usuarios miembros de ese grupo.
    """

    from services.group_service import get_user_ids_by_group
    from services.supabase_service import get_supabase_admin_client

    supabase = get_supabase_admin_client()

    allowed_user_ids = None

    if group_id is not None:
        allowed_user_ids = set(get_user_ids_by_group(group_id))

        # Si el grupo no tiene miembros, devolvemos ranking vacío.
        if not allowed_user_ids:
            return []

    profiles_response = (
        supabase
        .table("profiles")
        .select("id, email, display_name")
        .order("display_name")
        .execute()
    )

    profiles = profiles_response.data or []

    ranking_dict = {}

    for profile in profiles:
        user_id = profile["id"]

        # FILTRO CLAVE
        if allowed_user_ids is not None and user_id not in allowed_user_ids:
            continue

        ranking_dict[user_id] = {
            "user_id": user_id,
            "display_name": profile.get("display_name") or profile.get("email"),
            "email": profile.get("email"),
            "points": 0,
            "exact_count": 0,
            "result_count": 0,
            "miss_count": 0,
            "computed_predictions": 0
        }

    predictions_response = (
        supabase
        .table("predictions")
        .select("""
            id,
            user_id,
            home_score,
            away_score,
            points,
            match:match_id(
                id,
                home_score,
                away_score,
                is_finished
            )
        """)
        .execute()
    )

    predictions = predictions_response.data or []

    for prediction in predictions:
        user_id = prediction["user_id"]

        # FILTRO CLAVE
        if allowed_user_ids is not None and user_id not in allowed_user_ids:
            continue

        if user_id not in ranking_dict:
            continue

        match = prediction.get("match") or {}

        if not match.get("is_finished"):
            continue

        real_home = match.get("home_score")
        real_away = match.get("away_score")

        if real_home is None or real_away is None:
            continue

        points = prediction.get("points") or 0

        result_label = get_prediction_result_label(
            prediction["home_score"],
            prediction["away_score"],
            real_home,
            real_away
        )

        ranking_dict[user_id]["points"] += points
        ranking_dict[user_id]["computed_predictions"] += 1

        if result_label == "EXACT":
            ranking_dict[user_id]["exact_count"] += 1
        elif result_label == "RESULT":
            ranking_dict[user_id]["result_count"] += 1
        else:
            ranking_dict[user_id]["miss_count"] += 1

    return sort_ranking_rows(list(ranking_dict.values()))

def reset_points_for_match(match_id: int):
    """
    Cuando se limpia el resultado de un partido,
    los puntos de sus predicciones vuelven a 0.
    """

    from services.supabase_service import get_supabase_admin_client

    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("predictions")
        .update({"points": 0})
        .eq("match_id", match_id)
        .execute()
    )

    return response.data
