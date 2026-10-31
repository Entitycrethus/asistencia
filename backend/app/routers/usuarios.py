from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.database import get_supabase, t
from app.schemas import (
    Usuario,
    UsuarioCreate,
    UsuarioUpdate,
    Rol,
    RolCreate,
    Cargo,
    CargoCreate,
    HorarioLaboral,
    HorarioLaboralCreate,
)
from app.security import hash_password

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios, Roles, Cargos y Horarios"])


@router.get("", response_model=List[Usuario])
def listar_usuarios():
    supabase = get_supabase()
    rows = supabase.table(t("Usuario")).select("*").order("id", desc=False).execute().data or []
    roles = {r["id"]: r["nombre"] for r in (supabase.table(t("Rol")).select("*").execute().data or [])}
    cargos = {c["id"]: c["nombre"] for c in (supabase.table(t("Cargo")).select("*").execute().data or [])}

    return [
        Usuario(
            id=r["id"],
            codigo=r.get("codigo", ""),
            codigo_qr=r.get("codigo_qr", ""),
            nombres=r.get("nombres", ""),
            apellidos=r.get("apellidos", ""),
            correo=r.get("correo", ""),
            activo=bool(r.get("activo", True)),
            rol_id=r["rol_id"],
            cargo_id=r["cargo_id"],
            rol_nombre=roles.get(r["rol_id"], "Sin Rol"),
            cargo_nombre=cargos.get(r["cargo_id"], "Sin Cargo"),
        )
        for r in rows
    ]


@router.post("", response_model=Usuario)
def crear_usuario(payload: UsuarioCreate):
    supabase = get_supabase()
    data = payload.model_dump()
    data["password"] = hash_password(data["password"])

    res = supabase.table(t("Usuario")).insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario.")

    created = res.data[0]
    return Usuario(**{k: v for k, v in created.items() if k != "password"})


@router.patch("/{usuario_id}", response_model=Usuario)
def actualizar_usuario(usuario_id: int, payload: UsuarioUpdate):
    supabase = get_supabase()
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "password" in update_data and update_data["password"]:
        update_data["password"] = hash_password(update_data["password"])
    else:
        update_data.pop("password", None)

    res = supabase.table(t("Usuario")).update(update_data).eq("id", usuario_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    updated = res.data[0]
    return Usuario(**{k: v for k, v in updated.items() if k != "password"})


# ==========================================
# ROLES Y CARGOS
# ==========================================
@router.get("/roles", response_model=List[Rol])
def listar_roles():
    supabase = get_supabase()
    rows = supabase.table(t("Rol")).select("*").execute().data or []
    return [Rol(**r) for r in rows]


@router.post("/roles", response_model=Rol)
def crear_rol(payload: RolCreate):
    supabase = get_supabase()
    res = supabase.table(t("Rol")).insert(payload.model_dump()).execute()
    return Rol(**res.data[0])


@router.get("/cargos", response_model=List[Cargo])
def listar_cargos():
    supabase = get_supabase()
    rows = supabase.table(t("Cargo")).select("*").execute().data or []
    return [Cargo(**r) for r in rows]


@router.post("/cargos", response_model=Cargo)
def crear_cargo(payload: CargoCreate):
    supabase = get_supabase()
    res = supabase.table(t("Cargo")).insert(payload.model_dump()).execute()
    return Cargo(**res.data[0])


# ==========================================
# HORARIOS LABORALES
# ==========================================
@router.get("/horarios", response_model=List[HorarioLaboral])
def listar_horarios(usuario_id: Optional[int] = None):
    supabase = get_supabase()
    query = supabase.table(t("HorarioLaboral")).select("*")
    if usuario_id:
        query = query.eq("usuario_id", usuario_id)

    rows = query.execute().data or []
    usuarios = {u["id"]: u for u in (supabase.table(t("Usuario")).select("*").execute().data or [])}

    return [
        HorarioLaboral(
            id=r["id"],
            usuario_id=r["usuario_id"],
            dia_semana=r.get("dia_semana", ""),
            hora_inicio=str(r.get("hora_inicio", "")),
            hora_fin=str(r.get("hora_fin", "")),
            usuario_nombre=(
                f"{usuarios.get(r['usuario_id'], {}).get('nombres', '')} "
                f"{usuarios.get(r['usuario_id'], {}).get('apellidos', '')}"
            ).strip()
            or "Usuario",
        )
        for r in rows
    ]


@router.post("/horarios", response_model=HorarioLaboral)
def crear_horario(payload: HorarioLaboralCreate):
    supabase = get_supabase()
    res = supabase.table(t("HorarioLaboral")).insert(payload.model_dump()).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo registrar el horario.")
    return HorarioLaboral(**res.data[0])


@router.delete("/horarios/{horario_id}")
def eliminar_horario(horario_id: int):
    supabase = get_supabase()
    supabase.table(t("HorarioLaboral")).delete().eq("id", horario_id).execute()
    return {"ok": True}

