from typing import List
from fastapi import APIRouter, HTTPException
from app.database import get_supabase, t
from app.schemas import (
    Permiso,
    PermisoCreate,
    PermisoEstadoUpdate,
    TipoPermiso,
    TipoPermisoCreate,
)

router = APIRouter(prefix="/api/permisos", tags=["Permisos"])


@router.get("", response_model=List[Permiso])
def listar_permisos():
    supabase = get_supabase()
    rows = supabase.table(t("Permiso")).select("*").order("id", desc=True).execute().data or []
    usuarios = {u["id"]: u for u in (supabase.table(t("Usuario")).select("*").execute().data or [])}
    tipos = {tp["id"]: tp for tp in (supabase.table(t("TipoPermiso")).select("*").execute().data or [])}

    return [
        Permiso(
            id=r["id"],
            usuario_id=r["usuario_id"],
            tipo_permiso_id=r["tipo_permiso_id"],
            fecha_inicio=str(r.get("fecha_inicio", "")),
            fecha_fin=str(r.get("fecha_fin", "")),
            motivo=r.get("motivo", ""),
            aprobado=bool(r.get("aprobado", False)),
            usuario_nombre=(
                f"{usuarios.get(r['usuario_id'], {}).get('nombres', '')} "
                f"{usuarios.get(r['usuario_id'], {}).get('apellidos', '')}"
            ).strip()
            or "Usuario",
            tipo_permiso_nombre=tipos.get(r["tipo_permiso_id"], {}).get("nombre", "Permiso"),
        )
        for r in rows
    ]


@router.post("", response_model=Permiso)
def crear_permiso(payload: PermisoCreate):
    supabase = get_supabase()
    res = supabase.table(t("Permiso")).insert(payload.model_dump()).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo registrar el permiso.")
    return Permiso(**res.data[0])


@router.patch("/{permiso_id}/estado", response_model=Permiso)
def actualizar_estado_permiso(permiso_id: int, body: PermisoEstadoUpdate):
    supabase = get_supabase()
    res = (
        supabase.table(t("Permiso"))
        .update({"aprobado": body.aprobado})
        .eq("id", permiso_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Permiso no encontrado.")
    return Permiso(**res.data[0])


@router.get("/tipos", response_model=List[TipoPermiso])
def listar_tipos_permiso():
    supabase = get_supabase()
    rows = supabase.table(t("TipoPermiso")).select("*").execute().data or []
    return [TipoPermiso(**r) for r in rows]


@router.post("/tipos", response_model=TipoPermiso)
def crear_tipo_permiso(payload: TipoPermisoCreate):
    supabase = get_supabase()
    res = supabase.table(t("TipoPermiso")).insert(payload.model_dump()).execute()
    return TipoPermiso(**res.data[0])

