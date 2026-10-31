from datetime import date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from app.database import get_supabase, t
from app.routers.dashboard import procesar_faltas_automaticas, _resolve_tipo_incidencia_id
from app.schemas import (
    Asistencia,
    Incidencia,
    IncidenciaCreate,
    IncidenciaJustificar,
    HistorialAcceso,
    TipoIncidencia,
    ResumenFaltasUsuario,
)



router = APIRouter(prefix="/api/asistencias", tags=["Asistencias e Incidencias"])


@router.get("", response_model=List[Asistencia])
def listar_asistencias(
    fecha: Optional[str] = None,
    usuario_id: Optional[int] = None,
    solo_faltas: Optional[bool] = None,
):
    supabase = get_supabase()
    procesar_faltas_automaticas(supabase, target_date=fecha or date.today().isoformat(), forzar_cierre=False)

    query = supabase.table(t("Asistencia")).select("*")
    if fecha:
        query = query.eq("fecha", fecha)
    if usuario_id:
        query = query.eq("usuario_id", usuario_id)

    asistencias = query.order("id", desc=True).execute().data or []
    usuarios = {u["id"]: u for u in (supabase.table(t("Usuario")).select("*").execute().data or [])}
    cargos = {c["id"]: c for c in (supabase.table(t("Cargo")).select("*").execute().data or [])}
    dispositivos = {d["id"]: d for d in (supabase.table(t("Dispositivo")).select("*").execute().data or [])}
    incidencias = supabase.table(t("Incidencia")).select("*").execute().data or []
    tipos = supabase.table(t("TipoIncidencia")).select("*").execute().data or []
    tipo_map = {ti["id"]: ti for ti in tipos}
    tipo_falta_id = _resolve_tipo_incidencia_id(tipos, "falta", 2)

    inc_por_asist: Dict[int, Dict[str, Any]] = {}
    for inc in incidencias:
        aid = inc.get("asistencia_id")
        if aid is not None:
            inc_por_asist[aid] = inc

    resultado = []
    for a in asistencias:
        u = usuarios.get(a.get("usuario_id"), {})
        c = cargos.get(u.get("cargo_id"), {})
        d = dispositivos.get(a.get("dispositivo_id"), {})
        inc_asoc = inc_por_asist.get(a["id"])
        ti = tipo_map.get(inc_asoc.get("tipo_incidencia_id"), {}) if inc_asoc else {}
        es_falta = (not a.get("hora_entrada")) or (
            inc_asoc is not None and inc_asoc.get("tipo_incidencia_id") == tipo_falta_id
        )

        if solo_faltas is True and not es_falta:
            continue
        if solo_faltas is False and es_falta:
            continue

        resultado.append(
            Asistencia(
                id=a["id"],
                usuario_id=a["usuario_id"],
                dispositivo_id=a["dispositivo_id"],
                fecha=str(a.get("fecha", "")),
                hora_entrada=str(a["hora_entrada"]) if a.get("hora_entrada") else None,
                hora_salida=str(a["hora_salida"]) if a.get("hora_salida") else None,
                usuario_nombre=f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip() or "Usuario",
                usuario_codigo=u.get("codigo", ""),
                cargo_nombre=c.get("nombre", ""),
                dispositivo_nombre=d.get("nombre", ""),
                tiene_incidencia=inc_asoc is not None,
                es_falta=es_falta,
                tipo_incidencia_nombre=ti.get("nombre") if inc_asoc else ("Falta" if es_falta else None),
            )
        )
    return resultado


@router.get("/resumen-usuarios", response_model=List[ResumenFaltasUsuario])
def obtener_resumen_faltas_por_usuario(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
):
    supabase = get_supabase()
    procesar_faltas_automaticas(supabase, target_date=date.today().isoformat(), forzar_cierre=False)

    usuarios = supabase.table(t("Usuario")).select("*").order("id", desc=False).execute().data or []
    cargos = {c["id"]: c for c in (supabase.table(t("Cargo")).select("*").execute().data or [])}
    asistencias = supabase.table(t("Asistencia")).select("*").execute().data or []
    incidencias = supabase.table(t("Incidencia")).select("*").execute().data or []
    tipos = supabase.table(t("TipoIncidencia")).select("*").execute().data or []

    tipo_tardanza_id = _resolve_tipo_incidencia_id(tipos, "tardanza", 1)
    tipo_falta_id = _resolve_tipo_incidencia_id(tipos, "falta", 2)
    tipo_salida_id = _resolve_tipo_incidencia_id(tipos, "salida", 3)

    # Filtrar asistencias por rango de fechas si aplica
    asistencias_filtradas = []
    for a in asistencias:
        f_str = str(a.get("fecha", ""))
        if fecha_inicio and f_str < fecha_inicio:
            continue
        if fecha_fin and f_str > fecha_fin:
            continue
        asistencias_filtradas.append(a)

    asist_map = {a["id"]: a for a in asistencias_filtradas}

    stats: Dict[int, Dict[str, int]] = {
        u["id"]: {
            "total_asistencias": 0,
            "total_faltas": 0,
            "faltas_justificadas": 0,
            "faltas_injustificadas": 0,
            "total_tardanzas": 0,
            "total_salidas_anticipadas": 0,
        }
        for u in usuarios
    }

    asistencias_contadas_como_falta = set()

    for inc in incidencias:
        aid = inc.get("asistencia_id")
        asist = asist_map.get(aid)
        if not asist:
            continue
        uid = asist.get("usuario_id")
        if uid not in stats:
            continue

        tid = inc.get("tipo_incidencia_id")
        tiene_justif = bool((inc.get("justificacion") or "").strip())

        if tid == tipo_falta_id:
            stats[uid]["total_faltas"] += 1
            asistencias_contadas_como_falta.add(aid)
            if tiene_justif:
                stats[uid]["faltas_justificadas"] += 1
            else:
                stats[uid]["faltas_injustificadas"] += 1
        elif tid == tipo_tardanza_id:
            stats[uid]["total_tardanzas"] += 1
        elif tid == tipo_salida_id:
            stats[uid]["total_salidas_anticipadas"] += 1

    for a in asistencias_filtradas:
        uid = a.get("usuario_id")
        if uid not in stats:
            continue
        if a.get("hora_entrada"):
            stats[uid]["total_asistencias"] += 1
        elif a["id"] not in asistencias_contadas_como_falta:
            stats[uid]["total_faltas"] += 1
            stats[uid]["faltas_injustificadas"] += 1

    resumen = []
    for u in usuarios:
        uid = u["id"]
        st = stats[uid]
        c = cargos.get(u.get("cargo_id"), {})
        resumen.append(
            ResumenFaltasUsuario(
                usuario_id=uid,
                codigo=u.get("codigo", ""),
                usuario_nombre=f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip() or "Usuario",
                cargo_nombre=c.get("nombre", ""),
                **st,
            )
        )

    # Ordenar primero los que tienen más faltas o incidencias
    resumen.sort(
        key=lambda x: (x.total_faltas, x.total_tardanzas, x.total_asistencias),
        reverse=True,
    )
    return resumen


@router.get("/historial", response_model=List[HistorialAcceso])
def listar_historial_acceso(limit: int = 50):
    supabase = get_supabase()
    rows = (
        supabase.table(t("HistorialAcceso"))
        .select("*")
        .order("id", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    usuarios = {u["id"]: u for u in (supabase.table(t("Usuario")).select("*").execute().data or [])}
    dispositivos = {d["id"]: d for d in (supabase.table(t("Dispositivo")).select("*").execute().data or [])}

    return [
        HistorialAcceso(
            id=r["id"],
            usuario_id=r["usuario_id"],
            dispositivo_id=r["dispositivo_id"],
            fecha_hora=str(r.get("fecha_hora", "")),
            accion=r.get("accion", ""),
            usuario_nombre=(
                f"{usuarios.get(r['usuario_id'], {}).get('nombres', '')} "
                f"{usuarios.get(r['usuario_id'], {}).get('apellidos', '')}"
            ).strip()
            or "Usuario",
            usuario_codigo=usuarios.get(r["usuario_id"], {}).get("codigo", ""),
            dispositivo_nombre=dispositivos.get(r["dispositivo_id"], {}).get("nombre", ""),
        )
        for r in rows
    ]


@router.get("/incidencias", response_model=List[Incidencia])
def listar_incidencias(
    usuario_id: Optional[int] = None,
    tipo_incidencia_id: Optional[int] = None,
):
    supabase = get_supabase()
    rows = supabase.table(t("Incidencia")).select("*").order("id", desc=True).execute().data or []
    asistencias = {a["id"]: a for a in (supabase.table(t("Asistencia")).select("*").execute().data or [])}
    usuarios = {u["id"]: u for u in (supabase.table(t("Usuario")).select("*").execute().data or [])}
    tipos = {ti["id"]: ti for ti in (supabase.table(t("TipoIncidencia")).select("*").execute().data or [])}

    resultado = []
    for r in rows:
        asist = asistencias.get(r.get("asistencia_id"), {})
        uid = asist.get("usuario_id")
        if usuario_id is not None and uid != usuario_id:
            continue
        if tipo_incidencia_id is not None and r.get("tipo_incidencia_id") != tipo_incidencia_id:
            continue

        u = usuarios.get(uid, {})
        ti = tipos.get(r.get("tipo_incidencia_id"), {})
        resultado.append(
            Incidencia(
                id=r["id"],
                asistencia_id=r["asistencia_id"],
                tipo_incidencia_id=r["tipo_incidencia_id"],
                descripcion=r.get("descripcion", ""),
                justificacion=r.get("justificacion") or "",
                fecha_registro=str(r.get("fecha_registro", "")),
                usuario_id=uid,
                usuario_codigo=u.get("codigo", ""),
                tipo_incidencia_nombre=ti.get("nombre", "Incidencia"),
                usuario_nombre=f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip() or "Usuario",
                fecha_asistencia=str(asist.get("fecha", "")),
            )
        )
    return resultado


@router.post("/incidencias", response_model=Incidencia)
def crear_incidencia(payload: IncidenciaCreate):
    supabase = get_supabase()
    res = supabase.table(t("Incidencia")).insert(payload.model_dump()).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo registrar la incidencia.")
    return Incidencia(**res.data[0])


@router.patch("/incidencias/{incidencia_id}/justificar", response_model=Incidencia)
def justificar_incidencia(incidencia_id: int, body: IncidenciaJustificar):
    supabase = get_supabase()
    res = (
        supabase.table(t("Incidencia"))
        .update({"justificacion": body.justificacion})
        .eq("id", incidencia_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada.")
    return Incidencia(**res.data[0])


@router.get("/tipos-incidencia", response_model=List[TipoIncidencia])
def listar_tipos_incidencia():
    supabase = get_supabase()
    rows = supabase.table(t("TipoIncidencia")).select("*").execute().data or []
    return [TipoIncidencia(**r) for r in rows]
