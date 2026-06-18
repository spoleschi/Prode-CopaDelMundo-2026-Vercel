from collections import OrderedDict
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from services.group_service import (
    get_group_by_id,
    get_groups_by_user,
    get_user_ids_by_group,
    is_user_member_of_group,
)
from services.match_service import get_matches, get_match_with_teams
from services.policy_service import can_predict, can_publish_predictions
from services.prediction_service import (
    get_prediction_detail_by_user,
    get_predictions_by_match,
    get_predictions_by_user,
)
from services.scoring_service import get_prediction_result_label, get_ranking
from utils import ARG_TZ, annotate_match_datetime, get_day_label, login_required, parse_supabase_datetime


main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("main.fixture"))

    return redirect(url_for("auth.login"))


@main_bp.route("/fixture")
@login_required
def fixture():
    matches = get_matches()
    predictions = get_predictions_by_user(session["user_id"])
    predictions_by_match = {p["match_id"]: p for p in predictions}

    state_filter = request.args.get("state", "partidos").lower()
    allowed_states = {"partidos", "cargados", "pendientes", "cerrados", "finalizados", "hoy"}
    if state_filter not in allowed_states:
        state_filter = "partidos"

    now_utc = datetime.now(timezone.utc)
    today_arg = now_utc.astimezone(ARG_TZ).date()
    grouped_matches = OrderedDict()
    summary = {
        "total_matches": 0,
        "loaded_predictions": 0,
        "pending_predictions": 0,
        "closed_matches": 0,
        "finished_matches": 0,
        "today_matches": 0,
    }

    for match in matches:
        summary["total_matches"] += 1
        day_label = annotate_match_datetime(match)
        match_dt = parse_supabase_datetime(match.get("match_date"))
        match["can_predict"] = can_predict(match, now=now_utc)[0]
        match["has_started"] = (
            bool(match_dt) and now_utc >= match_dt.astimezone(timezone.utc)
        )
        match["is_today"] = bool(match_dt and match_dt.astimezone(ARG_TZ).date() == today_arg)
        if match["is_today"]:
            summary["today_matches"] += 1

        pred = predictions_by_match.get(match["id"])
        has_prediction = pred is not None
        match["has_prediction"] = has_prediction
        match["filter_states"] = []

        if match.get("is_finished"):
            summary["finished_matches"] += 1
            match["prediction_status"] = "FINISHED"
            match["prediction_status_text"] = "Finalizado"
            match["prediction_status_badge"] = "bg-primary"
            match["filter_states"].append("finalizados")
        elif not match["can_predict"]:
            summary["closed_matches"] += 1
            match["filter_states"].append("cerrados")
            if has_prediction:
                match["prediction_status"] = "LOADED_CLOSED"
                match["prediction_status_text"] = "Cargado / cerrado"
                match["prediction_status_badge"] = "bg-secondary"
                match["filter_states"].append("cargados")
            else:
                match["prediction_status"] = "MISSING_CLOSED"
                match["prediction_status_text"] = "Sin cargar / cerrado"
                match["prediction_status_badge"] = "bg-danger"
        else:
            if has_prediction:
                summary["loaded_predictions"] += 1
                match["prediction_status"] = "LOADED"
                match["prediction_status_text"] = "Cargado"
                match["prediction_status_badge"] = "bg-success"
                match["filter_states"].append("cargados")
            else:
                summary["pending_predictions"] += 1
                match["prediction_status"] = "PENDING"
                match["prediction_status_text"] = "Pendiente"
                match["prediction_status_badge"] = "bg-warning text-dark"
                match["filter_states"].append("pendientes")

        if state_filter == "partidos" or state_filter in match["filter_states"] or (
            state_filter == "hoy" and match["is_today"]
        ):
            grouped_matches.setdefault(day_label, []).append(match)

    return render_template(
        "fixture.html",
        grouped_matches=grouped_matches,
        predictions_by_match=predictions_by_match,
        summary=summary,
        selected_state=state_filter,
    )


@main_bp.route("/mis-pronosticos")
@login_required
def mis_pronosticos():
    predictions = get_prediction_detail_by_user(session["user_id"])
    grouped_predictions = OrderedDict()

    total_points = 0
    exact_count = 0
    result_count = 0
    miss_count = 0
    pending_count = 0

    for prediction in predictions:
        match = prediction.get("match") or {}
        match_dt = parse_supabase_datetime(match.get("match_date"))

        if match_dt:
            match_dt_arg = match_dt.astimezone(ARG_TZ)
            day_label = get_day_label(match_dt_arg)
            prediction["match_date_arg"] = match_dt_arg
            prediction["match_time_arg"] = match_dt_arg.strftime("%H:%M")
            prediction["match_day_label"] = day_label
        else:
            day_label = "Sin fecha"
            prediction["match_date_arg"] = None
            prediction["match_time_arg"] = "-"
            prediction["match_day_label"] = day_label

        if match.get("is_finished"):
            real_home = match.get("home_score")
            real_away = match.get("away_score")
            result_label = get_prediction_result_label(
                prediction["home_score"],
                prediction["away_score"],
                real_home,
                real_away,
            )

            prediction["result_label"] = result_label
            total_points += prediction.get("points") or 0

            if result_label == "EXACT":
                exact_count += 1
                prediction["result_label_text"] = "Exacto"
                prediction["result_badge_class"] = "bg-success"
            elif result_label == "RESULT":
                result_count += 1
                prediction["result_label_text"] = "Ganador/Empate"
                prediction["result_badge_class"] = "bg-primary"
            else:
                miss_count += 1
                prediction["result_label_text"] = "Fallado"
                prediction["result_badge_class"] = "bg-danger"
        else:
            pending_count += 1
            prediction["result_label"] = "PENDING"
            prediction["result_label_text"] = "Pendiente"
            prediction["result_badge_class"] = "bg-secondary"

        grouped_predictions.setdefault(day_label, []).append(prediction)

    summary = {
        "total_points": total_points,
        "exact_count": exact_count,
        "result_count": result_count,
        "miss_count": miss_count,
        "pending_count": pending_count,
        "total_predictions": len(predictions),
    }

    return render_template(
        "mis_pronosticos.html",
        grouped_predictions=grouped_predictions,
        summary=summary,
    )


@main_bp.route("/ranking")
@login_required
def ranking():
    group_id_raw = request.args.get("group_id")
    selected_group = None
    group_id = None

    if group_id_raw:
        try:
            group_id = int(group_id_raw)
            selected_group = get_group_by_id(group_id)

            if not selected_group:
                flash("El grupo seleccionado no existe.", "warning")
                return redirect(url_for("main.ranking"))

            if not is_user_member_of_group(session["user_id"], group_id):
                flash("No perteneces al grupo seleccionado.", "danger")
                return redirect(url_for("main.ranking"))

        except ValueError:
            flash("El grupo seleccionado no es valido.", "warning")
            return redirect(url_for("main.ranking"))

    user_groups = get_groups_by_user(session["user_id"])
    ranking_data = get_ranking(group_id=group_id)

    return render_template(
        "ranking.html",
        ranking=ranking_data,
        user_groups=user_groups,
        selected_group=selected_group,
        selected_group_id=group_id,
    )

@main_bp.route("/reglamento")
@login_required
def reglamento():
    return render_template("reglamento.html")

@main_bp.route("/partidos/<int:match_id>/pronosticos")
@login_required
def pronosticos_partido(match_id):
    match = get_match_with_teams(match_id)

    if not match:
        flash("El partido no existe.", "danger")
        return redirect(url_for("main.fixture"))

    if not can_publish_predictions(match):
        flash("Los pronósticos de este partido estaran disponibles cuando el partido haya comenzado.", "warning")
        return redirect(url_for("main.fixture"))

    match_dt = parse_supabase_datetime(match.get("match_date"))
    if not match_dt:
        flash("El partido no tiene fecha configurada.", "danger")
        return redirect(url_for("main.fixture"))

    match_dt_arg = match_dt.astimezone(ARG_TZ)
    match["match_date_arg"] = match_dt_arg
    match["match_time_arg"] = match_dt_arg.strftime("%H:%M")
    match["match_day_label"] = get_day_label(match_dt_arg)

    group_id_raw = request.args.get("group_id")
    selected_group = None
    group_id = None
    user_ids = None

    if group_id_raw:
        try:
            group_id = int(group_id_raw)
            selected_group = get_group_by_id(group_id)

            if not selected_group:
                flash("El grupo seleccionado no existe.", "warning")
                return redirect(url_for("main.pronosticos_partido", match_id=match_id))

            if not is_user_member_of_group(session["user_id"], group_id):
                flash("No perteneces al grupo seleccionado.", "danger")
                return redirect(url_for("main.pronosticos_partido", match_id=match_id))

            user_ids = get_user_ids_by_group(group_id)

        except ValueError:
            flash("El grupo seleccionado no es valido.", "warning")
            return redirect(url_for("main.pronosticos_partido", match_id=match_id))

    user_groups = get_groups_by_user(session["user_id"])
    predictions = get_predictions_by_match(match_id, user_ids=user_ids)

    return render_template(
        "pronosticos_partido.html",
        match=match,
        predictions=predictions,
        user_groups=user_groups,
        selected_group=selected_group,
        selected_group_id=group_id,
    )
