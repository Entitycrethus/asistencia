from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.database import get_supabase, t, reset_supabase_client
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
    supabase_url: str
    supabase_key: str


@router.get("/dispositivos", response_model=List[Dispositivo])
def listar_dispositivos():
    supabase = get_supabase()
    rows = supabase.table(t("Dispositivo")).select("*").order("id", desc=False).execute().data or []
    return [Dispositivo(**r) for r in rows]


@router.post("/dispositivos", response_model=Dispositivo)
def crear_dispositivo(payload: DispositivoCreate):
    supabase = get_supabase()
    res = supabase.table(t("Dispositivo")).insert(payload.model_dump()).execute()
    return Dispositivo(**res.data[0])


@router.patch("/dispositivos/{dispositivo_id}", response_model=Dispositivo)
def actualizar_dispositivo(dispositivo_id: int, payload: DispositivoUpdate):
    supabase = get_supabase()
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    res = supabase.table(t("Dispositivo")).update(update_data).eq("id", dispositivo_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado.")
    return Dispositivo(**res.data[0])


@router.get("/institucion", response_model=List[ConfiguracionInstitucion])
def obtener_configuracion_institucion():
    supabase = get_supabase()
    rows = supabase.table(t("ConfiguracionInstitucion")).select("*").execute().data or []
    return [
        ConfiguracionInstitucion(
            id=r["id"],
            nombre=r.get("nombre", ""),
            hora_entrada=str(r.get("hora_entrada", "08:00:00")),
            tolerancia_minutos=int(r.get("tolerancia_minutos", 10)),
            activa=bool(r.get("activa", True)),
        )
        for r in rows
    ]


@router.post("/institucion", response_model=ConfiguracionInstitucion)
def crear_configuracion_institucion(payload: ConfiguracionInstitucionCreate):
    supabase = get_supabase()
    res = supabase.table(t("ConfiguracionInstitucion")).insert(payload.model_dump()).execute()
    return ConfiguracionInstitucion(**res.data[0])


@router.patch("/institucion/{config_id}", response_model=ConfiguracionInstitucion)
def actualizar_configuracion_institucion(config_id: int, payload: ConfiguracionInstitucionUpdate):
    supabase = get_supabase()
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    res = (
        supabase.table(t("ConfiguracionInstitucion"))
        .update(update_data)
        .eq("id", config_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Configuración no encontrada.")
    return ConfiguracionInstitucion(**res.data[0])


@router.get("/conexion")
def estado_conexion_supabase():
    return {
        "conectado": settings.is_supabase_configured,
        "supabase_url": settings.SUPABASE_URL if settings.is_supabase_configured else "",
        "supabase_key": settings.SUPABASE_KEY if settings.is_supabase_configured else "",
    }


@router.post("/conexion")
def configurar_conexion_supabase(body: SupabaseCredsUpdate):
    reset_supabase_client(body.supabase_url, body.supabase_key)
    return {
        "conectado": settings.is_supabase_configured,
        "supabase_url": settings.SUPABASE_URL,
        "mensaje": "Conexión a Supabase actualizada correctamente.",
    }

