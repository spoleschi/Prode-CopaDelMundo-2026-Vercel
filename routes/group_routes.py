from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from services.group_service import create_group, get_groups_by_user, join_group
from utils import format_supabase_date, login_required


group_bp = Blueprint("group", __name__, url_prefix="/grupos")


@group_bp.route("/", methods=["GET"])
@login_required
def index():
    groups = get_groups_by_user(session["user_id"])

    for group in groups:
        if group.get("joined_at"):
            group["joined_at"] = format_supabase_date(group["joined_at"])

    return render_template("grupos.html", groups=groups)


@group_bp.route("/crear", methods=["POST"])
@login_required
def crear():
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")

    try:
        create_group(name=name, password=password, created_by=session["user_id"])
        flash("Grupo creado correctamente.", "success")

    except ValueError as e:
        flash(str(e), "warning")

    except Exception:
        flash("No se pudo crear el grupo.", "danger")

    return redirect(url_for("group.index"))


@group_bp.route("/unirse", methods=["POST"])
@login_required
def unirse():
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")

    try:
        join_group(name=name, password=password, user_id=session["user_id"])
        flash("Te sumaste al grupo correctamente.", "success")

    except ValueError as e:
        flash(str(e), "warning")

    except Exception:
        flash("No se pudo unir al grupo.", "danger")

    return redirect(url_for("group.index"))
