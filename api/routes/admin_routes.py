from flask import Blueprint, flash, redirect, render_template, request, url_for

from services.match_service import clear_match_result, get_matches, get_match, update_match_result
from services.policy_service import can_admin_update_result, validate_score
from services.scoring_service import recalculate_points_for_match, reset_points_for_match
from utils import admin_required, group_matches_by_day

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
