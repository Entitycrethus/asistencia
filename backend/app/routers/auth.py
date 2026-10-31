from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_supabase, t
from app.schemas import LoginRequest, TokenResponse, Usuario
from app.security import verify_password, create_access_token, get_current_user_payload

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    supabase = get_supabase()
    res = supabase.table(t("Usuario")).select("*").eq("correo", credentials.correo).execute()

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
        )

    user_row = res.data[0]
    if not user_row.get("activo", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta del usuario se encuentra inactiva.",
        )

    if not verify_password(credentials.password, user_row.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
        )

    roles_res = supabase.table(t("Rol")).select("*").eq("id", user_row["rol_id"]).execute()
    cargos_res = supabase.table(t("Cargo")).select("*").eq("id", user_row["cargo_id"]).execute()

    rol_nombre = roles_res.data[0]["nombre"] if roles_res.data else "Sin Rol"
    cargo_nombre = cargos_res.data[0]["nombre"] if cargos_res.data else "Sin Cargo"

    usuario_obj = Usuario(
        id=user_row["id"],
        codigo=user_row.get("codigo", ""),
        codigo_qr=user_row.get("codigo_qr", ""),
        nombres=user_row.get("nombres", ""),
        apellidos=user_row.get("apellidos", ""),
        correo=user_row.get("correo", ""),
        activo=user_row.get("activo", True),
        rol_id=user_row["rol_id"],
        cargo_id=user_row["cargo_id"],
        rol_nombre=rol_nombre,
        cargo_nombre=cargo_nombre,
    )

    token = create_access_token(
        {
            "sub": str(usuario_obj.id),
            "correo": usuario_obj.correo,
            "rol_id": usuario_obj.rol_id,
            "rol_nombre": rol_nombre,
        }
    )

    return TokenResponse(access_token=token, usuario=usuario_obj)


@router.get("/me", response_model=Usuario)
def get_me(payload: dict = Depends(get_current_user_payload)):
    supabase = get_supabase()
    user_id = int(payload["sub"])
    res = supabase.table(t("Usuario")).select("*").eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    u = res.data[0]
    roles_res = supabase.table(t("Rol")).select("*").eq("id", u["rol_id"]).execute()
    cargos_res = supabase.table(t("Cargo")).select("*").eq("id", u["cargo_id"]).execute()

    return Usuario(
        id=u["id"],
        codigo=u.get("codigo", ""),
        codigo_qr=u.get("codigo_qr", ""),
        nombres=u.get("nombres", ""),
        apellidos=u.get("apellidos", ""),
        correo=u.get("correo", ""),
        activo=u.get("activo", True),
        rol_id=u["rol_id"],
        cargo_id=u["cargo_id"],
        rol_nombre=roles_res.data[0]["nombre"] if roles_res.data else None,
        cargo_nombre=cargos_res.data[0]["nombre"] if cargos_res.data else None,
    )

