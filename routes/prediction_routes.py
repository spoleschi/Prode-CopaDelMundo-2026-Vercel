from flask import Blueprint, flash, redirect, request, session, url_for

from services.policy_service import validate_score
from services.prediction_service import save_prediction, save_predictions_batch
from utils import login_required


prediction_bp = Blueprint("prediction", __name__, url_prefix="/pronosticos")


@prediction_bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    try:
        match_id = int(request.form.get("match_id"))
        home_score = validate_score(request.form.get("home_score"), "goles local")
        away_score = validate_score(request.form.get("away_score"), "goles visitante")

        save_prediction(
            user_id=session["user_id"],
            match_id=match_id,
            home_score=home_score,
            away_score=away_score,
        )

        flash("Pronostico guardado correctamente.", "success")

    except ValueError as e:
        flash(str(e), "warning")

    except Exception:
        flash("No se pudo guardar el pronostico.", "danger")

    return redirect(url_for("main.fixture"))


@prediction_bp.route("/guardar-dia", methods=["POST"])
@login_required
def guardar_dia():
    state = request.form.get("state")

    def redirect_to_fixture():
        return redirect(url_for("main.fixture", state=state)) if state else redirect(url_for("main.fixture"))

    try:
        match_ids_raw = request.form.get("match_ids", "")

        if not match_ids_raw:
            flash("No se recibieron partidos para guardar.", "warning")
            return redirect_to_fixture()

        match_ids = [int(x) for x in match_ids_raw.split(",") if x.strip()]

        predictions_to_save = []
        incomplete_matches = []

        for match_id in match_ids:
            home_raw = request.form.get(f"home_score_{match_id}", "").strip()
            away_raw = request.form.get(f"away_score_{match_id}", "").strip()

            if home_raw == "" and away_raw == "":
                continue

            if home_raw == "" or away_raw == "":
                incomplete_matches.append(match_id)
                continue

            predictions_to_save.append(
                {
                    "match_id": match_id,
                    "home_score": validate_score(home_raw, "goles local"),
                    "away_score": validate_score(away_raw, "goles visitante"),
                }
            )

        if incomplete_matches:
            flash(
                f"Hay pronósticos incompletos en {len(incomplete_matches)} partido(s). Carga ambos goles o deja ambos campos vacios.",
                "warning",
            )
            return redirect_to_fixture()

        if not predictions_to_save:
            flash("No habia pronósticos nuevos para guardar en este dia.", "info")
            return redirect_to_fixture()

        result = save_predictions_batch(
            user_id=session["user_id"],
            predictions=predictions_to_save,
        )

        saved_count = result["saved_count"]
        errors = result["errors"]

        if saved_count > 0 and not errors:
            flash(f"Se guardaron {saved_count} pronóstico(s) correctamente.", "success")
        elif saved_count > 0 and errors:
            flash(
                f"Se guardaron {saved_count} pronóstico(s), pero {len(errors)} no pudieron guardarse porque el partido ya cerro o tuvo un error.",
                "warning",
            )
        else:
            flash("No se pudo guardar ningun pronóstico.", "danger")

    except ValueError as e:
        flash(str(e), "danger")

    except Exception:
        flash("No se pudieron guardar los pronósticos del dia.", "danger")

    return redirect_to_fixture()
