from typing import List
from fastapi import APIRouter, HTTPException
from app.database import fetch_all, execute_returning
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
    sql = """
        SELECT
            p.id,
            p.usuario_id,
            p.tipo_permiso_id,
            p.fecha_inicio::TEXT AS fecha_inicio,
            p.fecha_fin::TEXT AS fecha_fin,
            p.motivo,
            p.aprobado,
            (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
            tp.nombre AS tipo_permiso_nombre
        FROM public.permiso p
        INNER JOIN public.usuario u ON u.id = p.usuario_id
        INNER JOIN public.tipo_permiso tp ON tp.id = p.tipo_permiso_id
        ORDER BY p.id DESC;
    """
    rows = fetch_all(sql)
    return [Permiso(**r) for r in rows]


@router.post("", response_model=Permiso)
def crear_permiso(payload: PermisoCreate):
    sql = """
        INSERT INTO public.permiso (
            usuario_id, tipo_permiso_id, fecha_inicio, fecha_fin, motivo, aprobado
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING
            id,
            usuario_id,
            tipo_permiso_id,
            fecha_inicio::TEXT AS fecha_inicio,
            fecha_fin::TEXT AS fecha_fin,
            motivo,
            aprobado;
    """
    row = execute_returning(
        sql,
        (
            payload.usuario_id,
            payload.tipo_permiso_id,
            payload.fecha_inicio,
            payload.fecha_fin,
            payload.motivo,
            payload.aprobado,
        ),
    )
    if not row:
        raise HTTPException(status_code=400, detail="No se pudo registrar el permiso.")
    return Permiso(**row)


@router.patch("/{permiso_id}/estado", response_model=Permiso)
def actualizar_estado_permiso(permiso_id: int, body: PermisoEstadoUpdate):
    sql = """
        UPDATE public.permiso
        SET aprobado = %s
        WHERE id = %s
        RETURNING
            id,
            usuario_id,
            tipo_permiso_id,
            fecha_inicio::TEXT AS fecha_inicio,
            fecha_fin::TEXT AS fecha_fin,
            motivo,
            aprobado;
    """
    row = execute_returning(sql, (body.aprobado, permiso_id))
    if not row:
        raise HTTPException(status_code=404, detail="Permiso no encontrado.")
    return Permiso(**row)


@router.get("/tipos", response_model=List[TipoPermiso])
def listar_tipos_permiso():
    rows = fetch_all("SELECT id, nombre FROM public.tipo_permiso ORDER BY id ASC;")
    return [TipoPermiso(**r) for r in rows]


@router.post("/tipos", response_model=TipoPermiso)
def crear_tipo_permiso(payload: TipoPermisoCreate):
    row = execute_returning(
        "INSERT INTO public.tipo_permiso (nombre) VALUES (%s) RETURNING id, nombre;",
        (payload.nombre,),
    )
    return TipoPermiso(**row)
