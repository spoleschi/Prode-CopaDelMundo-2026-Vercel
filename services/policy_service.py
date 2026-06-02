from datetime import datetime, timezone

from config import Config
from utils import parse_supabase_datetime


def validate_score(value, field_name: str = "goles") -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"El valor de {field_name} no es valido.")

    if score < 0:
        raise ValueError("Los goles no pueden ser negativos.")

    return score


def can_predict(match: dict, now: datetime | None = None) -> tuple[bool, str | None]:
    if not match:
        return False, "El partido no existe."

    if match.get("is_finished"):
        return False, "El partido ya esta finalizado."

    match_dt = parse_supabase_datetime(match.get("match_date"))
    if not match_dt:
        return False, "El partido no tiene fecha configurada."

    now_utc = now or datetime.now(timezone.utc)
    if now_utc >= match_dt.astimezone(timezone.utc):
        return False, "El partido ya comenzo. No se puede modificar el pronostico."

    return True, None


def can_publish_predictions(match: dict, now: datetime | None = None) -> bool:
    match_dt = parse_supabase_datetime(match.get("match_date"))
    if not match_dt:
        return False

    now_utc = now or datetime.now(timezone.utc)
    return bool(match.get("is_finished")) or now_utc >= match_dt.astimezone(timezone.utc)


def can_admin_update_result(
    match: dict,
    now: datetime | None = None,
    allow_early: bool | None = None,
) -> tuple[bool, str | None]:
    if not match:
        return False, "El partido no existe."

    match_dt = parse_supabase_datetime(match.get("match_date"))
    if not match_dt:
        return False, "El partido no tiene fecha configurada."

    allow_early_result = Config.ALLOW_EARLY_RESULT_ADMIN if allow_early is None else allow_early
    now_utc = now or datetime.now(timezone.utc)

    if not allow_early_result and now_utc < match_dt.astimezone(timezone.utc):
        return False, "No se puede cargar resultado antes del inicio del partido."

    return True, None


def can_access_group(group: dict | None, is_member: bool) -> tuple[bool, str | None]:
    if not group:
        return False, "El grupo seleccionado no existe."

    if not is_member:
        return False, "No perteneces al grupo seleccionado."

    return True, None
