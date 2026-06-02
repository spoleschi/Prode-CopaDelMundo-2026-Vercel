from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from config import Config
from services.auth_service import (
    ensure_profile,
    login_user,
    register_user,
    request_password_reset,
)


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.args.get("confirmed") == "1":
        flash("Usuario confirmado correctamente. Ya podes iniciar sesion.", "success")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            response = login_user(email, password)
            user = response.user

            if not user:
                flash("No se pudo iniciar sesion.", "danger")
                return redirect(url_for("auth.login"))

            profile = ensure_profile(user_id=user.id, email=user.email)

            session["user_id"] = user.id
            session["email"] = user.email
            session["display_name"] = profile.get("display_name") if profile else user.email
            session["is_admin"] = profile.get("is_admin", False) if profile else False

            flash("Sesion iniciada correctamente.", "success")
            return redirect(url_for("main.fixture"))

        except Exception:
            flash("Email o contrasena incorrectos.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        display_name = request.form.get("display_name", "").strip()

        try:
            response = register_user(email, password, display_name)
            user = response.user

            if user:
                ensure_profile(user_id=user.id, email=user.email, display_name=display_name)

            flash("Usuario registrado correctamente. Ya podes iniciar sesion.", "success")
            return redirect(url_for("auth.login"))

        except Exception:
            flash("No se pudo registrar el usuario.", "danger")

    return render_template("register.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password_request():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Ingresa tu email.", "warning")
            return redirect(url_for("auth.reset_password_request"))

        try:
            request_password_reset(email)
            flash("Si el email existe, recibiras un enlace para recuperar tu contrasena.", "success")
            return redirect(url_for("auth.login"))

        except Exception:
            flash("No se pudo solicitar la recuperacion de contrasena.", "danger")

    return render_template("reset_password.html")


@auth_bp.route("/reset-password/confirm")
def reset_password_confirm():
    return render_template(
        "reset_password_confirm.html",
        supabase_url=Config.SUPABASE_URL or "",
        supabase_anon_key=Config.SUPABASE_ANON_KEY or "",
    )


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada.", "info")
    return redirect(url_for("auth.login"))
