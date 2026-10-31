import unicodedata
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from app.database import get_supabase, t
from app.schemas import SimularAsistenciaRequest, EvaluarFaltasRequest
from app.config import settings

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard y Monitoreo"])

WEEKDAY_NAMES_ES = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo",
}


def _norm(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip().lower()


def _build_lookup(rows: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    return {r["id"]: r for r in rows if "id" in r}


def _resolve_tipo_incidencia_id(tipos: List[Dict[str, Any]], keyword: str, default_id: int) -> int:
    kw = _norm(keyword)
    for ti in tipos:
        if kw in _norm(ti.get("nombre", "")):
            return ti["id"]
    return default_id


def _tiene_permiso_aprobado(permisos: List[Dict[str, Any]], usuario_id: int, fecha_str: str) -> bool:
    for p in permisos:
        if not p.get("aprobado") or p.get("usuario_id") != usuario_id:
            continue
        fi = str(p.get("fecha_inicio") or "")
        ff = str(p.get("fecha_fin") or "")
        inicio = min(fi, ff) if (fi and ff) else fi
        fin = max(fi, ff) if (fi and ff) else ff
        if inicio <= fecha_str <= fin:
            return True
    return False


def procesar_faltas_automaticas(
    supabase: Any,
    target_date: str,
    forzar_cierre: bool = False,
) -> List[Dict[str, Any]]:
    """
    Revisa los usuarios activos con horario laboral en `target_date`.
    Si la hora actual ya superó la `hora_fin` de su horario (o si la fecha es pasada / `forzar_cierre=True`)
    y el usuario no registró asistencia ni cuenta con permiso aprobado,
    crea automáticamente el registro de Asistencia (con hora_entrada=None)
    y su respectiva Incidencia de tipo 'Falta'.
    """
    try:
        fecha_dt = date.fromisoformat(target_date)
    except ValueError:
        return []

    today_dt = date.today()
    if fecha_dt > today_dt and not forzar_cierre:
        return []

    dia_nombre = WEEKDAY_NAMES_ES.get(fecha_dt.weekday(), "")
    now_dt = datetime.now()
    hora_actual_str = now_dt.strftime("%H:%M:%S")
    now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S")

    usuarios = supabase.table(t("Usuario")).select("*").execute().data or []
    horarios = supabase.table(t("HorarioLaboral")).select("*").execute().data or []
    asistencias_fecha = (
        supabase.table(t("Asistencia")).select("*").eq("fecha", target_date).execute().data or []
    )
    permisos = supabase.table(t("Permiso")).select("*").execute().data or []
    dispositivos = supabase.table(t("Dispositivo")).select("*").execute().data or []
    tipos_inc = supabase.table(t("TipoIncidencia")).select("*").execute().data or []

    default_disp_id = dispositivos[0]["id"] if dispositivos else 1
    tipo_falta_id = _resolve_tipo_incidencia_id(tipos_inc, "falta", 2)

    usuarios_con_asistencia = {a.get("usuario_id") for a in asistencias_fecha}

    # Agrupar horarios del día correspondiente por usuario_id
    horarios_dia_por_usuario: Dict[int, Dict[str, Any]] = {}
    for h in horarios:
        if _norm(h.get("dia_semana", "")) == dia_nombre:
            uid = h.get("usuario_id")
            if uid is not None:
                horarios_dia_por_usuario[uid] = h

    faltas_generadas = []
    for u in usuarios:
        if not u.get("activo", True):
            continue
        uid = u["id"]
        if uid in usuarios_con_asistencia:
            continue

        horario = horarios_dia_por_usuario.get(uid)
        if not horario:
            continue

        hora_fin = str(horario.get("hora_fin") or "13:00:00")[:8]
        ya_paso_hora_limite = (
            forzar_cierre
            or (fecha_dt < today_dt)
            or (fecha_dt == today_dt and hora_actual_str >= hora_fin)
        )

        if not ya_paso_hora_limite:
            continue

        if _tiene_permiso_aprobado(permisos, uid, target_date):
            continue

        # 1. Crear registro en Asistencia con hora_entrada=None y hora_salida=None
        nueva_asist_res = (
            supabase.table(t("Asistencia"))
            .insert(
                {
                    "usuario_id": uid,
                    "dispositivo_id": default_disp_id,
                    "fecha": target_date,
                    "hora_entrada": None,
                    "hora_salida": None,
                }
            )
            .execute()
        )
        if not nueva_asist_res.data:
            continue

        nueva_asist = nueva_asist_res.data[0]
        usuarios_con_asistencia.add(uid)

        # 2. Crear registro en Incidencia con tipo_incidencia = Falta (id=2)
        inc_res = (
            supabase.table(t("Incidencia"))
            .insert(
                {
                    "asistencia_id": nueva_asist["id"],
                    "tipo_incidencia_id": tipo_falta_id,
                    "descripcion": (
                        f"Falta automática: no registró asistencia hasta el cierre de su horario ({hora_fin})."
                    ),
                    "justificacion": None,
                    "fecha_registro": now_iso,
                }
            )
            .execute()
        )
        faltas_generadas.append(
            {
                "usuario_id": uid,
                "usuario_nombre": f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip(),
                "hora_limite": hora_fin,
                "asistencia": nueva_asist,
                "incidencia": inc_res.data[0] if inc_res.data else None,
            }
        )

    return faltas_generadas


@router.post("/evaluar-faltas")
def evaluar_faltas_endpoint(req: EvaluarFaltasRequest):
    supabase = get_supabase()
    target_date = req.fecha or date.today().isoformat()
    generadas = procesar_faltas_automaticas(
        supabase,
        target_date=target_date,
        forzar_cierre=req.forzar_cierre,
    )
    return {
        "fecha": target_date,
        "faltas_nuevas": len(generadas),
        "detalle": generadas,
        "mensaje": (
            f"Se generaron {len(generadas)} falta(s) automática(s) para {target_date}."
            if generadas
            else f"Todo al día: no hay nuevas faltas pendientes de generar para {target_date}."
        ),
    }


@router.get("/resumen")
def obtener_resumen_dashboard(fecha: str = None):
    supabase = get_supabase()
    target_date = fecha or date.today().isoformat()

    # Evaluar automáticamente si ya venció la hora_fin de algún horario hoy
    procesar_faltas_automaticas(supabase, target_date=target_date, forzar_cierre=False)

    usuarios = supabase.table(t("Usuario")).select("*").execute().data or []
    cargos = supabase.table(t("Cargo")).select("*").execute().data or []
    dispositivos = supabase.table(t("Dispositivo")).select("*").execute().data or []
    asistencias = supabase.table(t("Asistencia")).select("*").eq("fecha", target_date).execute().data or []
    incidencias = supabase.table(t("Incidencia")).select("*").execute().data or []
    tipos_incidencia = supabase.table(t("TipoIncidencia")).select("*").execute().data or []
    permisos = supabase.table(t("Permiso")).select("*").execute().data or []
    historial = (
        supabase.table(t("HistorialAcceso"))
        .select("*")
        .order("id", desc=True)
        .limit(25)
        .execute()
        .data
        or []
    )

    user_map = _build_lookup(usuarios)
    cargo_map = _build_lookup(cargos)
    disp_map = _build_lookup(dispositivos)
    tipo_inc_map = _build_lookup(tipos_incidencia)
    tipo_falta_id = _resolve_tipo_incidencia_id(tipos_incidencia, "falta", 2)

    asistencia_ids_hoy = {a["id"] for a in asistencias}
    incidencias_hoy = [i for i in incidencias if i.get("asistencia_id") in asistencia_ids_hoy]

    inc_por_asistencia: Dict[int, Dict[str, Any]] = {}
    for i in incidencias_hoy:
        aid = i.get("asistencia_id")
        if aid is not None:
            inc_por_asistencia[aid] = i

    permisos_activos_hoy = [
        p
        for p in permisos
        if _tiene_permiso_aprobado([p], p.get("usuario_id", 0), target_date)
    ]

    total_activos = sum(1 for u in usuarios if u.get("activo", True))
    presentes_hoy = len({a.get("usuario_id") for a in asistencias if a.get("hora_entrada")})
    faltas_hoy = sum(
        1
        for a in asistencias
        if not a.get("hora_entrada")
        or (inc_por_asistencia.get(a["id"], {}).get("tipo_incidencia_id") == tipo_falta_id)
    )
    salidas_registradas = sum(1 for a in asistencias if a.get("hora_salida"))
    dispositivos_activos = sum(1 for d in dispositivos if d.get("activo", True))

    asistencias_enriquecidas = []
    for a in sorted(asistencias, key=lambda x: x.get("id", 0), reverse=True):
        u = user_map.get(a.get("usuario_id"), {})
        c = cargo_map.get(u.get("cargo_id"), {})
        d = disp_map.get(a.get("dispositivo_id"), {})
        inc_asoc = inc_por_asistencia.get(a.get("id"))
        t_inc = tipo_inc_map.get(inc_asoc.get("tipo_incidencia_id"), {}) if inc_asoc else {}
        es_falta = (not a.get("hora_entrada")) or (
            inc_asoc is not None and inc_asoc.get("tipo_incidencia_id") == tipo_falta_id
        )

        asistencias_enriquecidas.append(
            {
                **a,
                "usuario_nombre": f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip() or "Usuario",
                "usuario_codigo": u.get("codigo", ""),
                "cargo_nombre": c.get("nombre", "General"),
                "dispositivo_nombre": d.get("nombre", "Dispositivo"),
                "tiene_incidencia": inc_asoc is not None,
                "es_falta": es_falta,
                "tipo_incidencia_nombre": t_inc.get("nombre") if inc_asoc else ("Falta" if es_falta else None),
            }
        )

    historial_enriquecido = []
    for h in historial:
        u = user_map.get(h.get("usuario_id"), {})
        d = disp_map.get(h.get("dispositivo_id"), {})
        historial_enriquecido.append(
            {
                **h,
                "usuario_nombre": f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip() or "Usuario",
                "usuario_codigo": u.get("codigo", ""),
                "dispositivo_nombre": d.get("nombre", "Dispositivo"),
            }
        )

    incidencias_enriquecidas = []
    asistencia_map = _build_lookup(asistencias)
    for inc in incidencias_hoy:
        asist = asistencia_map.get(inc.get("asistencia_id"), {})
        u = user_map.get(asist.get("usuario_id"), {})
        t_inc = tipo_inc_map.get(inc.get("tipo_incidencia_id"), {})
        incidencias_enriquecidas.append(
            {
                **inc,
                "usuario_id": asist.get("usuario_id"),
                "usuario_codigo": u.get("codigo", ""),
                "usuario_nombre": f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip() or "Usuario",
                "tipo_incidencia_nombre": t_inc.get("nombre", "Incidencia"),
                "fecha_asistencia": asist.get("fecha", target_date),
            }
        )

    franjas = {"07:00": 0, "07:30": 0, "08:00": 0, "08:30": 0, "09:00+": 0}
    for a in asistencias:
        he = str(a.get("hora_entrada") or "")
        if not he:
            continue
        hora_parte = he.split("T")[-1][:5] if "T" in he else he[:5]
        if hora_parte < "07:30":
            franjas["07:00"] += 1
        elif hora_parte < "08:00":
            franjas["07:30"] += 1
        elif hora_parte < "08:30":
            franjas["08:00"] += 1
        elif hora_parte < "09:00":
            franjas["08:30"] += 1
        else:
            franjas["09:00+"] += 1

    flujo_horario = [{"hora": k, "marcajes": v} for k, v in franjas.items()]

    return {
        "fecha": target_date,
        "supabase_conectado": settings.is_supabase_configured,
        "metricas": {
            "total_personal": total_activos,
            "presentes_hoy": presentes_hoy,
            "faltas_hoy": faltas_hoy,
            "pendientes_ingreso": max(
                total_activos - presentes_hoy - faltas_hoy - len(permisos_activos_hoy), 0
            ),
            "salidas_registradas": salidas_registradas,
            "incidencias_hoy": len(incidencias_hoy),
            "permisos_hoy": len(permisos_activos_hoy),
            "dispositivos_activos": dispositivos_activos,
            "total_dispositivos": len(dispositivos),
        },
        "asistencias_hoy": asistencias_enriquecidas,
        "historial_reciente": historial_enriquecido,
        "incidencias_hoy": incidencias_enriquecidas,
        "flujo_horario": flujo_horario,
    }


@router.post("/simular-asistencia")
def simular_marcaje_asistencia(req: SimularAsistenciaRequest):
    """
    Endpoint provisional para simular el marcaje de un código QR desde el Dashboard
    y comprobar el flujo de Asistencia, HistorialAcceso e Incidencia en tiempo real.
    """
    supabase = get_supabase()

    if req.usuario_id:
        user_res = supabase.table(t("Usuario")).select("*").eq("id", req.usuario_id).execute()
    elif req.codigo_qr:
        user_res = supabase.table(t("Usuario")).select("*").eq("codigo_qr", req.codigo_qr).execute()
    else:
        raise HTTPException(status_code=400, detail="Debe indicar un usuario_id o codigo_qr.")

    if not user_res.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado para el marcaje.")

    usuario = user_res.data[0]
    if not usuario.get("activo", True):
        raise HTTPException(status_code=400, detail="El usuario se encuentra inactivo.")

    today_dt = date.today()
    today_str = today_dt.isoformat()
    now_dt = datetime.now()
    if req.forzar_tardanza:
        hora_str = f"08:28:{now_dt.strftime('%S')}"
        now_iso = f"{today_str}T{hora_str}"
    else:
        hora_str = now_dt.strftime("%H:%M:%S")
        now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S")

    tipos_inc = supabase.table(t("TipoIncidencia")).select("*").execute().data or []
    tipo_tardanza_id = _resolve_tipo_incidencia_id(tipos_inc, "tardanza", 1)
    tipo_salida_ant_id = _resolve_tipo_incidencia_id(tipos_inc, "salida", 3)

    # Buscar horario del usuario para hoy
    dia_nombre = WEEKDAY_NAMES_ES.get(today_dt.weekday(), "")
    horarios_user = (
        supabase.table(t("HorarioLaboral"))
        .select("*")
        .eq("usuario_id", usuario["id"])
        .execute()
        .data
        or []
    )
    horario_hoy = next(
        (h for h in horarios_user if _norm(h.get("dia_semana", "")) == dia_nombre),
        None,
    )

    # Configuración de tolerancia institucional
    configs = supabase.table(t("ConfiguracionInstitucion")).select("*").execute().data or []
    tolerancia_min = int(configs[0].get("tolerancia_minutos", 10)) if configs else 10
    hora_base_str = (
        str(horario_hoy.get("hora_inicio", "08:00:00"))[:8]
        if horario_hoy
        else (str(configs[0].get("hora_entrada", "08:00:00"))[:8] if configs else "08:00:00")
    )
    hora_fin_str = str(horario_hoy.get("hora_fin", "13:00:00"))[:8] if horario_hoy else "13:00:00"

    # Calcular hora límite con tolerancia
    try:
        h_parts = [int(x) for x in hora_base_str.split(":")]
        limite_dt = datetime(2000, 1, 1, h_parts[0], h_parts[1], h_parts[2] if len(h_parts) > 2 else 0) + timedelta(
            minutes=tolerancia_min
        )
        hora_limite_tolerancia = limite_dt.strftime("%H:%M:%S")
    except Exception:
        hora_limite_tolerancia = "08:10:00"

    # Verificar si ya tiene asistencia hoy
    asist_res = (
        supabase.table(t("Asistencia"))
        .select("*")
        .eq("usuario_id", usuario["id"])
        .eq("fecha", today_str)
        .execute()
    )
    asistencias_hoy = asist_res.data or []
    asistencia_abierta = next(
        (a for a in asistencias_hoy if a.get("hora_entrada") and not a.get("hora_salida")),
        None,
    )
    asistencia_en_falta = next(
        (a for a in asistencias_hoy if not a.get("hora_entrada")),
        None,
    )

    incidencia_generada = None

    if asistencia_abierta:
        # Registrar SALIDA
        updated = (
            supabase.table(t("Asistencia"))
            .update({"hora_salida": hora_str, "dispositivo_id": req.dispositivo_id})
            .eq("id", asistencia_abierta["id"])
            .execute()
        )
        accion = "SALIDA"
        asistencia_actual = updated.data[0] if updated.data else asistencia_abierta

        # Evaluar Salida Anticipada (tipo_incidencia_id = 3)
        if hora_str < hora_fin_str:
            inc_res = (
                supabase.table(t("Incidencia"))
                .insert(
                    {
                        "asistencia_id": asistencia_actual["id"],
                        "tipo_incidencia_id": tipo_salida_ant_id,
                        "descripcion": f"Salida anticipada registrada a las {hora_str} (horario fin {hora_fin_str}).",
                        "justificacion": None,
                        "fecha_registro": now_iso,
                    }
                )
                .execute()
            )
            incidencia_generada = inc_res.data[0] if inc_res.data else None
    else:
        # Si tenía un registro vacío de falta hoy, lo actualizamos con la entrada; si no, insertamos
        if asistencia_en_falta:
            nueva_asist = (
                supabase.table(t("Asistencia"))
                .update({"hora_entrada": hora_str, "dispositivo_id": req.dispositivo_id})
                .eq("id", asistencia_en_falta["id"])
                .execute()
            )
        else:
            nueva_asist = (
                supabase.table(t("Asistencia"))
                .insert(
                    {
                        "usuario_id": usuario["id"],
                        "dispositivo_id": req.dispositivo_id,
                        "fecha": today_str,
                        "hora_entrada": hora_str,
                        "hora_salida": None,
                    }
                )
                .execute()
            )
        accion = "ENTRADA"
        asistencia_actual = nueva_asist.data[0] if nueva_asist.data else {}

        # Evaluar si corresponde registrar Incidencia de Tardanza (tipo_incidencia_id = 1)
        if req.forzar_tardanza or hora_str > hora_limite_tolerancia:
            inc_res = (
                supabase.table(t("Incidencia"))
                .insert(
                    {
                        "asistencia_id": asistencia_actual.get("id", 1),
                        "tipo_incidencia_id": tipo_tardanza_id,
                        "descripcion": f"Ingreso fuera de tolerancia ({hora_str}, límite {hora_limite_tolerancia}).",
                        "justificacion": None,
                        "fecha_registro": now_iso,
                    }
                )
                .execute()
            )
            incidencia_generada = inc_res.data[0] if inc_res.data else None

    # Registrar en HistorialAcceso
    hist_res = (
        supabase.table(t("HistorialAcceso"))
        .insert(
            {
                "usuario_id": usuario["id"],
                "dispositivo_id": req.dispositivo_id,
                "fecha_hora": now_iso,
                "accion": accion,
            }
        )
        .execute()
    )

    return {
        "mensaje": f"Marcaje de {accion} ({hora_str}) registrado para {usuario['nombres']} {usuario['apellidos']}",
        "accion": accion,
        "asistencia": asistencia_actual,
        "historial": hist_res.data[0] if hist_res.data else None,
        "incidencia": incidencia_generada,
    }
