from config import Config
from services.supabase_service import get_supabase_admin_client, get_supabase_anon_client

def login_user(email: str, password: str):
    supabase = get_supabase_anon_client()
    return supabase.auth.sign_in_with_password({"email": email, "password": password})


def register_user(email: str, password: str, display_name: str = None):
    supabase = get_supabase_anon_client()
    return supabase.auth.sign_up(
        {
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name or email.split("@")[0]}},
        }
    )


def request_password_reset(email: str):
    supabase = get_supabase_anon_client()
    redirect_to = f"{Config.APP_BASE_URL.rstrip('/')}/reset-password/confirm"
    if hasattr(supabase.auth, "reset_password_for_email"):
        return supabase.auth.reset_password_for_email(email, {"redirect_to": redirect_to})
    return supabase.auth.reset_password_email(email, {"redirect_to": redirect_to})


def get_profile(user_id: str):
    supabase = get_supabase_admin_client()
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return response.data


def ensure_profile(user_id: str, email: str, display_name: str = None):
    supabase = get_supabase_admin_client()
    existing = supabase.table("profiles").select("*").eq("id", user_id).execute()

    if existing.data:
        return existing.data[0]

    profile = {
        "id": user_id,
        "email": email,
        "display_name": display_name or email.split("@")[0],
        "is_admin": False,
    }

    created = supabase.table("profiles").insert(profile).execute()
    return created.data[0] if created.data else None
