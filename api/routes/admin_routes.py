from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify

from services.match_service import clear_match_result, get_matches, get_match, update_match_result
from services.policy_service import can_admin_update_result, validate_score
from services.scoring_service import recalculate_points_for_match, reset_points_for_match
from utils import admin_required, group_matches_by_day
from services.football_data_service import (
    get_today_matches,
    get_competitions,
    get_competition_matches,
    FootballDataApiError,
    simplify_matches_response
)

from services.external_match_mapping_service import (
    preview_worldcup_mapping,
    apply_worldcup_mapping,
)

from services.result_sync_service import (
    preview_result_sync,
    apply_result_sync,
)

from services.knockout_sync_service import (
    preview_knockout_team_sync,
    apply_knockout_team_sync,
)




admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/resultados", methods=["GET", "POST"])
@admin_required
def resultados():
    if request.method == "POST":
        try:
            match_id = int(request.form.get("match_id"))
            home_score = validate_score(request.form.get("home_score"), "goles local")
            away_score = validate_score(request.form.get("away_score"), "goles visitante")

            update_match_result(
                match_id=match_id,
                home_score=home_score,
                away_score=away_score,
            )
            recalculate_points_for_match(match_id)

            flash("Resultado actualizado y puntajes recalculados.", "success")
            return redirect(url_for("admin.resultados"))

        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("admin.resultados"))

        except Exception:
            flash("No se pudo actualizar el resultado.", "danger")
            return redirect(url_for("admin.resultados"))

    matches = get_matches()
    for match in matches:
        can_load, reason = can_admin_update_result(match)
        match["can_load_result"] = can_load
        match["load_result_reason"] = reason

    grouped_matches = group_matches_by_day(matches)

    return render_template(
        "admin_resultados.html",
        grouped_matches=grouped_matches,
    )


@admin_bp.route("/resultados/limpiar", methods=["POST"])
@admin_required
def limpiar_resultado():
    try:
        match_id = int(request.form.get("match_id"))

        if not get_match(match_id):
            raise ValueError("El partido no existe.")

        clear_match_result(match_id)
        reset_points_for_match(match_id)

        flash("Resultado limpiado y puntajes del partido reiniciados.", "success")

    except ValueError as e:
        flash(str(e), "danger")

    except Exception:
        flash("No se pudo limpiar el resultado.", "danger")

    return redirect(url_for("admin.resultados"))

# Api para obtener resultados desde football-data.org
@admin_bp.route("/api-test/football-data/today")
@admin_required
def football_data_today_test():
    try:
        data = get_today_matches()
        return jsonify(data)

    except FootballDataApiError as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400

    except Exception as e:
        print("ERROR FOOTBALL DATA TODAY:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error inesperado consultando football-data.org."
        }), 500


@admin_bp.route("/api-test/football-data/competitions")
@admin_required
def football_data_competitions_test():
    try:
        data = get_competitions()
        return jsonify(data)

    except FootballDataApiError as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400

    except Exception as e:
        print("ERROR FOOTBALL DATA COMPETITIONS:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error inesperado consultando football-data.org."
        }), 500


@admin_bp.route("/api-test/football-data/competition/<competition_code>")
@admin_required
def football_data_competition_matches_test(competition_code):
    try:
        season = request.args.get("season", "2026")

        data = get_competition_matches(
            competition_code=competition_code.upper(),
            params={
                "season": season
            }
        )

        return jsonify(data)

    except FootballDataApiError as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400

    except Exception as e:
        print("ERROR FOOTBALL DATA COMPETITION:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error inesperado consultando football-data.org."
        }), 500


@admin_bp.route("/api-test/football-data/competition/<competition_code>/summary")
@admin_required
def football_data_competition_matches_summary_test(competition_code):
    try:
        season = request.args.get("season", "2026")

        data = get_competition_matches(
            competition_code=competition_code.upper(),
            params={
                "season": season
            }
        )

        simplified = simplify_matches_response(data)

        return jsonify(simplified)

    except FootballDataApiError as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400

    except Exception as e:
        print("ERROR FOOTBALL DATA COMPETITION SUMMARY:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error inesperado consultando football-data.org."
        }), 500

@admin_bp.route("/api-test/football-data/mapping/preview")
@admin_required
def football_data_mapping_preview():
    try:
        data = preview_worldcup_mapping()
        return jsonify(data)

    except Exception as e:
        print("ERROR FOOTBALL DATA MAPPING PREVIEW:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error generando preview de mapeo.",
            "detail": str(e)
        }), 500


@admin_bp.route("/api-test/football-data/mapping/apply", methods=["POST"])
# @admin_bp.route("/api-test/football-data/mapping/apply", methods=["GET", "POST"])
@admin_required
def football_data_mapping_apply():
    try:
        data = apply_worldcup_mapping()
        return jsonify(data)

    except Exception as e:
        print("ERROR FOOTBALL DATA MAPPING APPLY:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error aplicando mapeo.",
            "detail": str(e)
        }), 500

@admin_bp.route("/api-test/football-data/results/preview")
@admin_required
def football_data_results_preview():
    try:
        data = preview_result_sync()
        return jsonify(data)

    except Exception as e:
        print("ERROR FOOTBALL DATA RESULTS PREVIEW:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error generando preview de sincronización de resultados.",
            "detail": str(e)
        }), 500


@admin_bp.route("/api-test/football-data/results/apply", methods=["POST"])
# @admin_bp.route("/api-test/football-data/results/apply", methods=["GET", "POST"])
@admin_required
def football_data_results_apply():
    try:
        data = apply_result_sync()
        return jsonify(data)

    except Exception as e:
        print("ERROR FOOTBALL DATA RESULTS APPLY:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error aplicando sincronización de resultados.",
            "detail": str(e)
        }), 500
        
@admin_bp.route("/resultados/sincronizar", methods=["POST"])
@admin_required
def sincronizar_resultados():
    try:
        result = apply_result_sync()

        updated_count = result.get("updated_count", 0)
        error_count = result.get("error_count", 0)

        preview = result.get("preview", {})
        already_updated_count = preview.get("already_updated_count", 0)
        not_finished_count = preview.get("not_finished_count", 0)
        invalid_score_count = preview.get("invalid_score_count", 0)
        missing_external_count = preview.get("missing_external_count", 0)

        if updated_count > 0:
            flash(
                f"Sincronización completada. "
                f"Partidos actualizados: {updated_count}. "
                f"Ya estaban actualizados: {already_updated_count}. "
                f"No finalizados: {not_finished_count}.",
                "success"
            )
        else:
            flash(
                f"Sincronización completada sin nuevos resultados. "
                f"Ya estaban actualizados: {already_updated_count}. "
                f"No finalizados: {not_finished_count}.",
                "info"
            )

        if invalid_score_count > 0:
            flash(
                f"Atención: {invalid_score_count} partido(s) figuran finalizados en la API "
                f"pero no tienen score completo.",
                "warning"
            )

        if missing_external_count > 0:
            flash(
                f"Atención: {missing_external_count} partido(s) locales no se encontraron "
                f"en la respuesta de football-data.",
                "warning"
            )

        if error_count > 0:
            flash(
                f"La sincronización tuvo {error_count} error(es). Revisá los logs.",
                "danger"
            )

    except Exception as e:
        print("ERROR SINCRONIZAR RESULTADOS:")
        print(type(e))
        print(repr(e))

        flash("No se pudo sincronizar resultados desde football-data.", "danger")

    return redirect(url_for("admin.resultados"))

@admin_bp.route("/api-test/football-data/knockout-teams/preview")
@admin_required
def football_data_knockout_teams_preview():
    try:
        data = preview_knockout_team_sync()
        return jsonify(data)

    except Exception as e:
        print("ERROR FOOTBALL DATA KNOCKOUT TEAMS PREVIEW:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error generando preview de cruces eliminatorios.",
            "detail": str(e)
        }), 500


@admin_bp.route("/api-test/football-data/knockout-teams/apply", methods=["GET", "POST"])
# @admin_bp.route("/api-test/football-data/knockout-teams/apply", methods=["POST"])
@admin_required
def football_data_knockout_teams_apply():
    try:
        data = apply_knockout_team_sync()
        return jsonify(data)

    except Exception as e:
        print("ERROR FOOTBALL DATA KNOCKOUT TEAMS APPLY:")
        print(type(e))
        print(repr(e))

        return jsonify({
            "ok": False,
            "error": "Error aplicando sincronización de cruces eliminatorios.",
            "detail": str(e)
        }), 500
        
@admin_bp.route("/resultados/sincronizar-cruces", methods=["POST"])
@admin_required
def sincronizar_cruces():
    try:
        result = apply_knockout_team_sync()

        updated_count = result.get("updated_count", 0)
        error_count = result.get("error_count", 0)

        preview = result.get("preview", {})

        already_ok_count = preview.get("already_ok_count", 0)
        not_defined_yet_count = preview.get("not_defined_yet_count", 0)
        missing_external_count = preview.get("missing_external_count", 0)
        team_not_found_count = preview.get("team_not_found_count", 0)

        if updated_count > 0:
            flash(
                f"Cruces sincronizados correctamente. "
                f"Partidos actualizados: {updated_count}. "
                f"Ya estaban correctos: {already_ok_count}. "
                f"Todavía sin definir: {not_defined_yet_count}.",
                "success"
            )
        else:
            flash(
                f"Sincronización de cruces completada sin nuevos cambios. "
                f"Ya estaban correctos: {already_ok_count}. "
                f"Todavía sin definir: {not_defined_yet_count}.",
                "info"
            )

        if missing_external_count > 0:
            flash(
                f"Atención: {missing_external_count} partido(s) eliminatorios "
                f"no se encontraron en football-data.",
                "warning"
            )

        if team_not_found_count > 0:
            flash(
                f"Atención: {team_not_found_count} partido(s) tienen equipos "
                f"cuyo código no existe en tu tabla teams. Revisá TEAM_CODE_ALIASES.",
                "warning"
            )

        if error_count > 0:
            flash(
                f"La sincronización tuvo {error_count} error(es). Revisá los logs.",
                "danger"
            )

    except Exception as e:
        print("ERROR SINCRONIZAR CRUCES:")
        print(type(e))
        print(repr(e))

        flash("No se pudieron sincronizar los cruces desde football-data.", "danger")

    return redirect(url_for("admin.resultados"))