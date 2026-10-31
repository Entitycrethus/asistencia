from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.database import fetch_all, fetch_one, execute_returning
from app.config import settings
from app.schemas import (
    Dispositivo,
    DispositivoCreate,
    DispositivoUpdate,
    ConfiguracionInstitucion,
    ConfiguracionInstitucionCreate,
    ConfiguracionInstitucionUpdate,
)

router = APIRouter(prefix="/api/configuracion", tags=["Configuración y Dispositivos"])


class SupabaseCredsUpdate(BaseModel):
    database_url: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None


@router.get("/dispositivos", response_model=List[Dispositivo])
def listar_dispositivos():
    rows = fetch_all("SELECT id, nombre, ubicacion, activo FROM public.dispositivo ORDER BY id ASC;")
    return [Dispositivo(**r) for r in rows]


@router.post("/dispositivos", response_model=Dispositivo)
def crear_dispositivo(payload: DispositivoCreate):
    sql = """
        INSERT INTO public.dispositivo (nombre, ubicacion, activo)
        VALUES (%s, %s, %s)
        RETURNING id, nombre, ubicacion, activo;
    """
    row = execute_returning(sql, (payload.nombre, payload.ubicacion, payload.activo))
    return Dispositivo(**row)


@router.patch("/dispositivos/{dispositivo_id}", response_model=Dispositivo)
def actualizar_dispositivo(dispositivo_id: int, payload: DispositivoUpdate):
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        existing = fetch_one(
            "SELECT id, nombre, ubicacion, activo FROM public.dispositivo WHERE id = %s;",
            (dispositivo_id,),
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado.")
        return Dispositivo(**existing)

    set_clauses = [f"{col} = %s" for col in update_data.keys()]
    values = list(update_data.values()) + [dispositivo_id]
    sql = f"""
        UPDATE public.dispositivo
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING id, nombre, ubicacion, activo;
    """
    row = execute_returning(sql, tuple(values))
    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado.")
    return Dispositivo(**row)


@router.get("/institucion", response_model=List[ConfiguracionInstitucion])
def obtener_configuracion_institucion():
    sql = """
        SELECT
            id,
            nombre,
            COALESCE(hora_entrada::TEXT, '08:00:00') AS hora_entrada,
            COALESCE(tolerancia_minutos, 10) AS tolerancia_minutos,
            COALESCE(activa, TRUE) AS activa
        FROM public.configuracion_institucion
        ORDER BY id ASC;
    """
    rows = fetch_all(sql)
    return [ConfiguracionInstitucion(**r) for r in rows]


@router.post("/institucion", response_model=ConfiguracionInstitucion)
def crear_configuracion_institucion(payload: ConfiguracionInstitucionCreate):
    sql = """
        INSERT INTO public.configuracion_institucion (
            nombre, hora_entrada, tolerancia_minutos, activa
        )
        VALUES (%s, %s, %s, %s)
        RETURNING
            id,
            nombre,
            hora_entrada::TEXT AS hora_entrada,
            tolerancia_minutos,
            activa;
    """
    row = execute_returning(
        sql,
        (payload.nombre, payload.hora_entrada, payload.tolerancia_minutos, payload.activa),
    )
    return ConfiguracionInstitucion(**row)


@router.patch("/institucion/{config_id}", response_model=ConfiguracionInstitucion)
def actualizar_configuracion_institucion(config_id: int, payload: ConfiguracionInstitucionUpdate):
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        existing = fetch_one(
            """
            SELECT id, nombre, hora_entrada::TEXT AS hora_entrada, tolerancia_minutos, activa
            FROM public.configuracion_institucion WHERE id = %s;
            """,
            (config_id,),
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Configuración no encontrada.")
        return ConfiguracionInstitucion(**existing)

    set_clauses = [f"{col} = %s" for col in update_data.keys()]
    values = list(update_data.values()) + [config_id]
    sql = f"""
        UPDATE public.configuracion_institucion
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING
            id,
            nombre,
            hora_entrada::TEXT AS hora_entrada,
            tolerancia_minutos,
            activa;
    """
    row = execute_returning(sql, tuple(values))
    if not row:
        raise HTTPException(status_code=404, detail="Configuración no encontrada.")
    return ConfiguracionInstitucion(**row)


@router.get("/conexion")
def estado_conexion_supabase():
    return {
        "conectado": settings.is_db_configured,
        "supabase_url": settings.SUPABASE_URL,
        "supabase_key": settings.SUPABASE_KEY,
    }


@router.post("/conexion")
def configurar_conexion_supabase(body: SupabaseCredsUpdate):
    if body.database_url:
        settings.DATABASE_URL = body.database_url.strip()
    if body.supabase_url:
        settings.SUPABASE_URL = body.supabase_url.strip()
    if body.supabase_key:
        settings.SUPABASE_KEY = body.supabase_key.strip()
    return {
        "conectado": settings.is_db_configured,
        "supabase_url": settings.SUPABASE_URL,
        "mensaje": "Parámetros de conexión actualizados.",
    }
