from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from functools import wraps
import re
from zoneinfo import ZoneInfo

from flask import flash, redirect, session, url_for


try:
    ARG_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:
    ARG_TZ = timezone(timedelta(hours=-3))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Tenes que iniciar sesion.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Tenes que iniciar sesion.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("is_admin") is not True:
            flash("No tenes permisos de administrador.", "danger")
            return redirect(url_for("main.fixture"))
        return view(*args, **kwargs)

    return wrapped


def parse_supabase_datetime(value: str) -> datetime | None:
    if not value:
        return None

    value = value.replace("Z", "+00:00")
    microseconds_match = re.search(r"\.(\d+)([+-]\d{2}:\d{2})$", value)
    if microseconds_match:
        microseconds = microseconds_match.group(1).ljust(6, "0")[:6]
        value = (
            value[: microseconds_match.start()]
            + "."
            + microseconds
            + microseconds_match.group(2)
        )

    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def get_day_label(dt_arg: datetime) -> str:
    days = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sabado",
        6: "Domingo",
    }

    return f"{days[dt_arg.weekday()]} {dt_arg.strftime('%d/%m/%Y')}"


def format_supabase_date(value: str) -> str | None:
    dt = parse_supabase_datetime(value)
    if not dt:
        return None
    return dt.astimezone(ARG_TZ).strftime("%d-%m-%Y")


def annotate_match_datetime(match: dict) -> str:
    match_dt = parse_supabase_datetime(match.get("match_date"))

    if not match_dt:
        match["match_date_arg"] = None
        match["match_time_arg"] = "-"
        match["match_day_label"] = "Sin fecha"
        return "Sin fecha"

    match_dt_arg = match_dt.astimezone(ARG_TZ)
    day_label = get_day_label(match_dt_arg)

    match["match_date_arg"] = match_dt_arg
    match["match_time_arg"] = match_dt_arg.strftime("%H:%M")
    match["match_day_label"] = day_label

    return day_label


def group_matches_by_day(matches: list[dict]) -> OrderedDict:
    grouped_matches = OrderedDict()

    for match in matches:
        day_label = annotate_match_datetime(match)
        grouped_matches.setdefault(day_label, []).append(match)

    return grouped_matches
