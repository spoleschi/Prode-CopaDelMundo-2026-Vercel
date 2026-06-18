from werkzeug.security import generate_password_hash, check_password_hash

from services.supabase_service import get_supabase_admin_client

def get_groups_by_user(user_id: str):
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("prode_group_members")
        .select("""
            id,
            group_id,
            joined_at,
            group:group_id(
                id,
                name,
                created_by,
                created_at
            )
        """)
        .eq("user_id", user_id)
        .order("joined_at")
        .execute()
    )

    return response.data or []


def get_group_by_id(group_id: int):
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("prode_groups")
        .select("id, name, created_by, created_at")
        .eq("id", group_id)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_group_by_name(name: str):
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("prode_groups")
        .select("*")
        .ilike("name", name.strip())
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def is_user_member_of_group(user_id: str, group_id: int) -> bool:
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("prode_group_members")
        .select("id")
        .eq("user_id", user_id)
        .eq("group_id", group_id)
        .execute()
    )

    return bool(response.data)


def add_user_to_group(user_id: str, group_id: int):
    supabase = get_supabase_admin_client()

    if is_user_member_of_group(user_id, group_id):
        return {
            "added": False,
            "reason": "already_member"
        }

    response = (
        supabase
        .table("prode_group_members")
        .insert({
            "group_id": group_id,
            "user_id": user_id
        })
        .execute()
    )

    return {
        "added": True,
        "data": response.data
    }


def create_group(name: str, password: str, created_by: str):
    if not name or not name.strip():
        raise ValueError("El nombre del grupo es obligatorio.")

    if not password or len(password.strip()) < 4:
        raise ValueError("La contraseña del grupo debe tener al menos 4 caracteres.")

    clean_name = name.strip()

    existing = get_group_by_name(clean_name)
    if existing:
        raise ValueError("Ya existe un grupo con ese nombre.")

    password_hash = generate_password_hash(password.strip())

    supabase = get_supabase_admin_client()

    created = (
        supabase
        .table("prode_groups")
        .insert({
            "name": clean_name,
            "password_hash": password_hash,
            "created_by": created_by
        })
        .execute()
    )

    if not created.data:
        raise ValueError("No se pudo crear el grupo.")

    group = created.data[0]

    add_user_to_group(
        user_id=created_by,
        group_id=group["id"]
    )

    return group


def join_group(name: str, password: str, user_id: str):
    if not name or not name.strip():
        raise ValueError("Ingresá el nombre del grupo.")

    if not password:
        raise ValueError("Ingresá la contraseña del grupo.")

    group = get_group_by_name(name.strip())

    if not group:
        raise ValueError("No existe un grupo con ese nombre.")

    if not check_password_hash(group["password_hash"], password):
        raise ValueError("La contraseña del grupo es incorrecta.")

    if is_user_member_of_group(user_id, group["id"]):
        raise ValueError("Ya pertenecés a ese grupo.")

    add_user_to_group(
        user_id=user_id,
        group_id=group["id"]
    )

    return group

def get_user_ids_by_group(group_id: int):
    supabase = get_supabase_admin_client()

    response = (
        supabase
        .table("prode_group_members")
        .select("user_id")
        .eq("group_id", group_id)
        .execute()
    )

    rows = response.data or []

    return [row["user_id"] for row in rows]