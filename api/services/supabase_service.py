from config import Config

def _create_client(url: str, key: str):
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("Falta instalar la dependencia supabase.") from exc

    return create_client(url, key)


def get_supabase_anon_client():
    """
    Cliente usado para operaciones de Auth.
    Usa la anon key.
    """
    if not Config.SUPABASE_URL or not Config.SUPABASE_ANON_KEY:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_ANON_KEY en .env")

    return _create_client(
        Config.SUPABASE_URL,
        Config.SUPABASE_ANON_KEY
    )


def get_supabase_admin_client():
    """
    Cliente usado por Flask para acceder a tablas.
    Usa service_role y bypassea RLS.
    No debe usarse jamás desde frontend.
    """
    if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")

    return _create_client(
        Config.SUPABASE_URL,
        Config.SUPABASE_SERVICE_ROLE_KEY
    )
