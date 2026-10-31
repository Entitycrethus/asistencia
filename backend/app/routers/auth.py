from fastapi import APIRouter, Depends, HTTPException, status
from app.database import fetch_one
from app.schemas import LoginRequest, TokenResponse, Usuario
from app.security import verify_password, create_access_token, get_current_user_payload

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    sql = """
        SELECT
            u.id,
            u.codigo,
            u.codigo_qr,
            u.nombres,
            u.apellidos,
            u.correo,
            u.password,
            u.activo,
            u.rol_id,
            u.cargo_id,
            r.nombre AS rol_nombre,
            c.nombre AS cargo_nombre
        FROM public.usuario u
        INNER JOIN public.rol r ON r.id = u.rol_id
        INNER JOIN public.cargo c ON c.id = u.cargo_id
        WHERE u.correo = %s
        LIMIT 1;
    """
    user_row = fetch_one(sql, (credentials.correo,))

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
        )

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
        rol_nombre=user_row.get("rol_nombre"),
        cargo_nombre=user_row.get("cargo_nombre"),
    )

    token = create_access_token(
        {
            "sub": str(usuario_obj.id),
            "correo": usuario_obj.correo,
            "rol_id": usuario_obj.rol_id,
            "rol_nombre": usuario_obj.rol_nombre,
        }
    )

    return TokenResponse(access_token=token, usuario=usuario_obj)


@router.get("/me", response_model=Usuario)
def get_me(payload: dict = Depends(get_current_user_payload)):
    user_id = int(payload["sub"])
    sql = """
        SELECT
            u.id,
            u.codigo,
            u.codigo_qr,
            u.nombres,
            u.apellidos,
            u.correo,
            u.activo,
            u.rol_id,
            u.cargo_id,
            r.nombre AS rol_nombre,
            c.nombre AS cargo_nombre
        FROM public.usuario u
        INNER JOIN public.rol r ON r.id = u.rol_id
        INNER JOIN public.cargo c ON c.id = u.cargo_id
        WHERE u.id = %s
        LIMIT 1;
    """
    u = fetch_one(sql, (user_id,))
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    return Usuario(**u)
