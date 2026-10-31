from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from app.database import fetch_all, fetch_one, execute_returning
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


def procesar_faltas_automaticas(
    target_date: str,
    forzar_cierre: bool = False,
) -> List[Dict[str, Any]]:
    """
    Ejecuta una consulta SQL con INNER JOIN y dos SUBCONSULTAS (NOT EXISTS)
    para detectar a los usuarios activos cuyo horario laboral del día ya superó
    su `hora_fin` sin haber registrado asistencia ni contar con permiso aprobado.
    """
    try:
        fecha_dt = date.fromisoformat(target_date)
    except ValueError:
        return []

    today_dt = date.today()
    if fecha_dt > today_dt and not forzar_cierre:
        return []

    dia_nombre = WEEKDAY_NAMES_ES.get(fecha_dt.weekday(), "")
    hora_actual_str = datetime.now().strftime("%H:%M:%S")
    aplicar_cierre = forzar_cierre or (fecha_dt < today_dt)

    sql_pendientes_falta = """
        SELECT
            u.id AS usuario_id,
            u.codigo,
            (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
            hl.hora_fin::TEXT AS hora_fin
        FROM public.usuario u
        INNER JOIN public.horario_laboral hl ON hl.usuario_id = u.id
        WHERE u.activo = TRUE
          AND LOWER(TRANSLATE(hl.dia_semana, 'áéíóúÁÉÍÓÚ', 'aeiouAEIOU')) = %s
          AND (%s = TRUE OR %s::TIME >= hl.hora_fin)
          AND NOT EXISTS (
              SELECT 1
              FROM public.asistencia a
              WHERE a.usuario_id = u.id
                AND a.fecha = %s::DATE
          )
          AND NOT EXISTS (
              SELECT 1
              FROM public.permiso p
              WHERE p.usuario_id = u.id
                AND p.aprobado = TRUE
                AND %s::DATE BETWEEN LEAST(p.fecha_inicio, p.fecha_fin)
                                 AND GREATEST(p.fecha_inicio, p.fecha_fin)
          );
    """
    pendientes = fetch_all(
        sql_pendientes_falta,
        (dia_nombre, aplicar_cierre, hora_actual_str, target_date, target_date),
    )
    if not pendientes:
        return []

    disp_row = fetch_one("SELECT id FROM public.dispositivo ORDER BY id ASC LIMIT 1;")
    default_disp_id = disp_row["id"] if disp_row else 1

    tipo_falta_row = fetch_one(
        "SELECT id FROM public.tipo_incidencia WHERE LOWER(nombre) LIKE '%%falta%%' LIMIT 1;"
    )
    tipo_falta_id = tipo_falta_row["id"] if tipo_falta_row else 2

    faltas_generadas = []
    for row in pendientes:
        uid = row["usuario_id"]
        hora_fin = str(row.get("hora_fin") or "13:00:00")[:8]

        nueva_asist = execute_returning(
            """
            INSERT INTO public.asistencia (usuario_id, dispositivo_id, fecha, hora_entrada, hora_salida)
            VALUES (%s, %s, %s::DATE, NULL, NULL)
            RETURNING id, usuario_id, dispositivo_id, fecha::TEXT AS fecha, hora_entrada, hora_salida;
            """,
            (uid, default_disp_id, target_date),
        )
        if not nueva_asist:
            continue

        nueva_inc = execute_returning(
            """
            INSERT INTO public.incidencia (
                asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro
            )
            VALUES (%s, %s, %s, NULL, NOW())
            RETURNING id, asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro::TEXT AS fecha_registro;
            """,
            (
                nueva_asist["id"],
                tipo_falta_id,
                f"Falta automática: no registró asistencia hasta el cierre de su horario ({hora_fin}).",
            ),
        )

        faltas_generadas.append(
            {
                "usuario_id": uid,
                "usuario_nombre": row["usuario_nombre"],
                "hora_limite": hora_fin,
                "asistencia": nueva_asist,
                "incidencia": nueva_inc,
            }
        )

    return faltas_generadas


def registrar_marcaje_sql(
    usuario_id: Optional[int] = None,
    codigo_qr: Optional[str] = None,
    dispositivo_id: int = 1,
    forzar_tardanza: bool = False,
    aplicar_antirrebote: bool = False,
    bloquear_si_jornada_completa: bool = False,
) -> Dict[str, Any]:
    """
    Lógica central en SQL puro para registrar asistencia (desde la App Móvil vía Ngrok
    o desde el Simulador del Dashboard):
      1. Identifica al colaborador por `codigo_qr`, `codigo` o `usuario_id` (con INNER JOIN a cargo y rol).
      2. Verifica que el usuario esté activo.
      3. Verifica mediante subconsulta SQL si tiene un Permiso aprobado vigente hoy.
      4. Aplica bloqueo anti-rebote (60 segundos) sobre `historial_acceso` para evitar doble lectura de cámara.
      5. Registra ENTRADA o SALIDA en `asistencia`, evalúa `horario_laboral` + `configuracion_institucion`
         para generar automáticamente `incidencia` (Tardanza o Salida anticipada) e inserta en `historial_acceso`.
    """
    if usuario_id is not None:
        usuario = fetch_one(
            """
            SELECT u.*, c.nombre AS cargo_nombre, r.nombre AS rol_nombre
            FROM public.usuario u
            INNER JOIN public.cargo c ON c.id = u.cargo_id
            INNER JOIN public.rol r ON r.id = u.rol_id
            WHERE u.id = %s
            LIMIT 1;
            """,
            (usuario_id,),
        )
    elif codigo_qr:
        qr_clean = codigo_qr.strip()
        usuario = fetch_one(
            """
            SELECT u.*, c.nombre AS cargo_nombre, r.nombre AS rol_nombre
            FROM public.usuario u
            INNER JOIN public.cargo c ON c.id = u.cargo_id
            INNER JOIN public.rol r ON r.id = u.rol_id
            WHERE u.codigo_qr = %s OR u.codigo = %s
            LIMIT 1;
            """,
            (qr_clean, qr_clean),
        )
    else:
        raise HTTPException(status_code=400, detail="Debe proporcionar codigo_qr o usuario_id.")

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ningún colaborador con el código QR '{codigo_qr or usuario_id}'.",
        )

    if not usuario.get("activo", True):
        raise HTTPException(
            status_code=403,
            detail=f"El colaborador {usuario['nombres']} {usuario['apellidos']} se encuentra inactivo.",
        )

    today_dt = date.today()
    today_str = today_dt.isoformat()
    now_dt = datetime.now()
    if forzar_tardanza:
        hora_str = f"08:28:{now_dt.strftime('%S')}"
        now_iso = f"{today_str}T{hora_str}"
    else:
        hora_str = now_dt.strftime("%H:%M:%S")
        now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S")

    # 1. Validar si el usuario tiene un Permiso aprobado vigente hoy (INNER JOIN con tipo_permiso)
    permiso_hoy = fetch_one(
        """
        SELECT p.id, p.motivo, tp.nombre AS tipo_permiso_nombre
        FROM public.permiso p
        INNER JOIN public.tipo_permiso tp ON tp.id = p.tipo_permiso_id
        WHERE p.usuario_id = %s
          AND p.aprobado = TRUE
          AND %s::DATE BETWEEN LEAST(p.fecha_inicio, p.fecha_fin)
                           AND GREATEST(p.fecha_inicio, p.fecha_fin)
        LIMIT 1;
        """,
        (usuario["id"], today_str),
    )
    if permiso_hoy:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede marcar asistencia: {usuario['nombres']} {usuario['apellidos']} "
                f"cuenta con un permiso aprobado hoy ({permiso_hoy['tipo_permiso_nombre']}: {permiso_hoy['motivo']})."
            ),
        )

    # 2. Protección anti-rebote (doble escaneo accidental de cámara en menos de 60 segundos)
    if aplicar_antirrebote:
        ultimo_acceso = fetch_one(
            """
            SELECT id, accion, fecha_hora::TEXT AS fecha_hora,
                   EXTRACT(EPOCH FROM (%s::TIMESTAMP - fecha_hora))::INT AS segundos_transcurridos
            FROM public.historial_acceso
            WHERE usuario_id = %s
            ORDER BY id DESC
            LIMIT 1;
            """,
            (now_iso, usuario["id"]),
        )
        if (
            ultimo_acceso
            and ultimo_acceso.get("segundos_transcurridos") is not None
            and 0 <= ultimo_acceso["segundos_transcurridos"] < 60
        ):
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Lectura duplicada detectada: {usuario['nombres']} {usuario['apellidos']} "
                    f"ya registró {ultimo_acceso['accion']} hace {ultimo_acceso['segundos_transcurridos']} segundos."
                ),
            )

    # 3. Consultar horario laboral del día y configuración de tolerancia
    dia_nombre = WEEKDAY_NAMES_ES.get(today_dt.weekday(), "")
    horario_hoy = fetch_one(
        """
        SELECT hora_inicio::TEXT AS hora_inicio, hora_fin::TEXT AS hora_fin
        FROM public.horario_laboral
        WHERE usuario_id = %s
          AND LOWER(TRANSLATE(dia_semana, 'áéíóúÁÉÍÓÚ', 'aeiouAEIOU')) = %s
        LIMIT 1;
        """,
        (usuario["id"], dia_nombre),
    )
    config_inst = fetch_one(
        """
        SELECT COALESCE(hora_entrada::TEXT, '08:00:00') AS hora_entrada,
               COALESCE(tolerancia_minutos, 10) AS tolerancia_minutos
        FROM public.configuracion_institucion
        WHERE activa = TRUE
        LIMIT 1;
        """
    ) or {"hora_entrada": "08:00:00", "tolerancia_minutos": 10}

    tolerancia_min = int(config_inst["tolerancia_minutos"])
    hora_base_str = (
        str(horario_hoy["hora_inicio"])[:8]
        if horario_hoy
        else str(config_inst["hora_entrada"])[:8]
    )
    hora_fin_str = str(horario_hoy["hora_fin"])[:8] if horario_hoy else "13:00:00"

    try:
        h_parts = [int(x) for x in hora_base_str.split(":")]
        limite_dt = datetime(2000, 1, 1, h_parts[0], h_parts[1], h_parts[2] if len(h_parts) > 2 else 0) + timedelta(
            minutes=tolerancia_min
        )
        hora_limite_tolerancia = limite_dt.strftime("%H:%M:%S")
    except Exception:
        hora_limite_tolerancia = "08:10:00"

    # 4. Verificar estado de asistencia de hoy para el usuario
    asistencia_abierta = fetch_one(
        """
        SELECT id, usuario_id, dispositivo_id, fecha::TEXT AS fecha,
               hora_entrada::TEXT AS hora_entrada, hora_salida::TEXT AS hora_salida
        FROM public.asistencia
        WHERE usuario_id = %s AND fecha = %s::DATE
          AND hora_entrada IS NOT NULL AND hora_salida IS NULL
        ORDER BY id DESC LIMIT 1;
        """,
        (usuario["id"], today_str),
    )

    if bloquear_si_jornada_completa and not asistencia_abierta:
        asistencia_completada = fetch_one(
            """
            SELECT id, hora_entrada::TEXT AS hora_entrada, hora_salida::TEXT AS hora_salida
            FROM public.asistencia
            WHERE usuario_id = %s AND fecha = %s::DATE
              AND hora_entrada IS NOT NULL AND hora_salida IS NOT NULL
            ORDER BY id DESC LIMIT 1;
            """,
            (usuario["id"], today_str),
        )
        if asistencia_completada:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{usuario['nombres']} {usuario['apellidos']} ya completó su jornada de hoy "
                    f"(Entrada: {asistencia_completada['hora_entrada']}, Salida: {asistencia_completada['hora_salida']})."
                ),
            )

    asistencia_en_falta = fetch_one(
        """
        SELECT id FROM public.asistencia
        WHERE usuario_id = %s AND fecha = %s::DATE AND hora_entrada IS NULL
        ORDER BY id DESC LIMIT 1;
        """,
        (usuario["id"], today_str),
    )

    incidencia_generada = None
    estado_puntualidad = "PUNTUAL"

    if asistencia_abierta:
        asistencia_actual = execute_returning(
            """
            UPDATE public.asistencia
            SET hora_salida = %s::TIME, dispositivo_id = %s
            WHERE id = %s
            RETURNING id, usuario_id, dispositivo_id, fecha::TEXT AS fecha,
                      hora_entrada::TEXT AS hora_entrada, hora_salida::TEXT AS hora_salida;
            """,
            (hora_str, dispositivo_id, asistencia_abierta["id"]),
        )
        accion = "SALIDA"
        estado_puntualidad = "JORNADA COMPLETA"

        if hora_str < hora_fin_str:
            estado_puntualidad = "SALIDA ANTICIPADA"
            tipo_salida = fetch_one(
                "SELECT id FROM public.tipo_incidencia WHERE LOWER(nombre) LIKE '%%salida%%' LIMIT 1;"
            )
            tipo_salida_id = tipo_salida["id"] if tipo_salida else 3
            incidencia_generada = execute_returning(
                """
                INSERT INTO public.incidencia (
                    asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro
                )
                VALUES (%s, %s, %s, NULL, %s::TIMESTAMP)
                RETURNING id, asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro::TEXT AS fecha_registro;
                """,
                (
                    asistencia_actual["id"],
                    tipo_salida_id,
                    f"Salida anticipada registrada a las {hora_str} (horario fin {hora_fin_str}).",
                    now_iso,
                ),
            )
    else:
        if asistencia_en_falta:
            asistencia_actual = execute_returning(
                """
                UPDATE public.asistencia
                SET hora_entrada = %s::TIME, dispositivo_id = %s
                WHERE id = %s
                RETURNING id, usuario_id, dispositivo_id, fecha::TEXT AS fecha,
                          hora_entrada::TEXT AS hora_entrada, hora_salida::TEXT AS hora_salida;
                """,
                (hora_str, dispositivo_id, asistencia_en_falta["id"]),
            )
        else:
            asistencia_actual = execute_returning(
                """
                INSERT INTO public.asistencia (
                    usuario_id, dispositivo_id, fecha, hora_entrada, hora_salida
                )
                VALUES (%s, %s, %s::DATE, %s::TIME, NULL)
                RETURNING id, usuario_id, dispositivo_id, fecha::TEXT AS fecha,
                          hora_entrada::TEXT AS hora_entrada, hora_salida::TEXT AS hora_salida;
                """,
                (usuario["id"], dispositivo_id, today_str, hora_str),
            )
        accion = "ENTRADA"

        if forzar_tardanza or hora_str > hora_limite_tolerancia:
            estado_puntualidad = "TARDANZA"
            tipo_tard = fetch_one(
                "SELECT id FROM public.tipo_incidencia WHERE LOWER(nombre) LIKE '%%tardanza%%' LIMIT 1;"
            )
            tipo_tardanza_id = tipo_tard["id"] if tipo_tard else 1
            incidencia_generada = execute_returning(
                """
                INSERT INTO public.incidencia (
                    asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro
                )
                VALUES (%s, %s, %s, NULL, %s::TIMESTAMP)
                RETURNING id, asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro::TEXT AS fecha_registro;
                """,
                (
                    asistencia_actual["id"],
                    tipo_tardanza_id,
                    f"Ingreso fuera de tolerancia ({hora_str}, límite {hora_limite_tolerancia}).",
                    now_iso,
                ),
            )

    historial_row = execute_returning(
        """
        INSERT INTO public.historial_acceso (usuario_id, dispositivo_id, fecha_hora, accion)
        VALUES (%s, %s, %s::TIMESTAMP, %s)
        RETURNING id, usuario_id, dispositivo_id, fecha_hora::TEXT AS fecha_hora, accion;
        """,
        (usuario["id"], dispositivo_id, now_iso, accion),
    )

    return {
        "ok": True,
        "mensaje": (
            f"Marcaje de {accion} ({hora_str} - {estado_puntualidad}) registrado "
            f"para {usuario['nombres']} {usuario['apellidos']}"
        ),
        "accion": accion,
        "estado_puntualidad": estado_puntualidad,
        "usuario": {
            "id": usuario["id"],
            "codigo": usuario.get("codigo", ""),
            "codigo_qr": usuario.get("codigo_qr", ""),
            "nombre_completo": f"{usuario['nombres']} {usuario['apellidos']}",
            "cargo": usuario.get("cargo_nombre", ""),
        },
        "asistencia": asistencia_actual,
        "historial": historial_row,
        "incidencia": incidencia_generada,
    }


@router.post("/evaluar-faltas")
def evaluar_faltas_endpoint(req: EvaluarFaltasRequest):
    target_date = req.fecha or date.today().isoformat()
    generadas = procesar_faltas_automaticas(
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
    target_date = fecha or date.today().isoformat()

    procesar_faltas_automaticas(target_date=target_date, forzar_cierre=False)

    sql_asistencias_hoy = """
        SELECT
            a.id,
            a.usuario_id,
            a.dispositivo_id,
            a.fecha::TEXT AS fecha,
            a.hora_entrada::TEXT AS hora_entrada,
            a.hora_salida::TEXT AS hora_salida,
            (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
            u.codigo AS usuario_codigo,
            c.nombre AS cargo_nombre,
            COALESCE(d.nombre, 'Dispositivo') AS dispositivo_nombre,
            EXISTS (
                SELECT 1 FROM public.incidencia i WHERE i.asistencia_id = a.id
            ) AS tiene_incidencia,
            (
                a.hora_entrada IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM public.incidencia i2
                    INNER JOIN public.tipo_incidencia ti2 ON ti2.id = i2.tipo_incidencia_id
                    WHERE i2.asistencia_id = a.id
                      AND LOWER(ti2.nombre) LIKE '%%falta%%'
                )
            ) AS es_falta,
            (
                SELECT ti3.nombre
                FROM public.incidencia i3
                INNER JOIN public.tipo_incidencia ti3 ON ti3.id = i3.tipo_incidencia_id
                WHERE i3.asistencia_id = a.id
                ORDER BY i3.id DESC
                LIMIT 1
            ) AS tipo_incidencia_nombre
        FROM public.asistencia a
        INNER JOIN public.usuario u ON u.id = a.usuario_id
        INNER JOIN public.cargo c ON c.id = u.cargo_id
        LEFT JOIN public.dispositivo d ON d.id = a.dispositivo_id
        WHERE a.fecha = %s::DATE
        ORDER BY a.id DESC;
    """
    asistencias_enriquecidas = fetch_all(sql_asistencias_hoy, (target_date,))

    sql_historial = """
        SELECT
            ha.id,
            ha.usuario_id,
            ha.dispositivo_id,
            ha.fecha_hora::TEXT AS fecha_hora,
            ha.accion,
            (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
            u.codigo AS usuario_codigo,
            COALESCE(d.nombre, 'Dispositivo') AS dispositivo_nombre
        FROM public.historial_acceso ha
        INNER JOIN public.usuario u ON u.id = ha.usuario_id
        LEFT JOIN public.dispositivo d ON d.id = ha.dispositivo_id
        ORDER BY ha.id DESC
        LIMIT 25;
    """
    historial_enriquecido = fetch_all(sql_historial)

    sql_incidencias_hoy = """
        SELECT
            i.id,
            i.asistencia_id,
            i.tipo_incidencia_id,
            i.descripcion,
            COALESCE(i.justificacion, '') AS justificacion,
            i.fecha_registro::TEXT AS fecha_registro,
            a.usuario_id,
            u.codigo AS usuario_codigo,
            (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
            ti.nombre AS tipo_incidencia_nombre,
            a.fecha::TEXT AS fecha_asistencia
        FROM public.incidencia i
        INNER JOIN public.asistencia a ON a.id = i.asistencia_id
        INNER JOIN public.usuario u ON u.id = a.usuario_id
        INNER JOIN public.tipo_incidencia ti ON ti.id = i.tipo_incidencia_id
        WHERE a.fecha = %s::DATE
        ORDER BY i.id DESC;
    """
    incidencias_enriquecidas = fetch_all(sql_incidencias_hoy, (target_date,))

    sql_metricas = """
        SELECT
            (SELECT COUNT(*)::INT FROM public.usuario WHERE activo = TRUE) AS total_personal,
            (SELECT COUNT(*)::INT FROM public.dispositivo WHERE activo = TRUE) AS dispositivos_activos,
            (SELECT COUNT(*)::INT FROM public.dispositivo) AS total_dispositivos,
            (
                SELECT COUNT(*)::INT
                FROM public.permiso p
                WHERE p.aprobado = TRUE
                  AND %s::DATE BETWEEN LEAST(p.fecha_inicio, p.fecha_fin)
                                   AND GREATEST(p.fecha_inicio, p.fecha_fin)
            ) AS permisos_hoy;
    """
    m_row = fetch_one(sql_metricas, (target_date,)) or {}

    total_activos = m_row.get("total_personal", 0)
    permisos_hoy = m_row.get("permisos_hoy", 0)
    presentes_hoy = len({a.get("usuario_id") for a in asistencias_enriquecidas if a.get("hora_entrada")})
    faltas_hoy = sum(1 for a in asistencias_enriquecidas if a.get("es_falta"))
    salidas_registradas = sum(1 for a in asistencias_enriquecidas if a.get("hora_salida"))

    franjas = {"07:00": 0, "07:30": 0, "08:00": 0, "08:30": 0, "09:00+": 0}
    for a in asistencias_enriquecidas:
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
        "supabase_conectado": settings.is_db_configured,
        "metricas": {
            "total_personal": total_activos,
            "presentes_hoy": presentes_hoy,
            "faltas_hoy": faltas_hoy,
            "pendientes_ingreso": max(total_activos - presentes_hoy - faltas_hoy - permisos_hoy, 0),
            "salidas_registradas": salidas_registradas,
            "incidencias_hoy": len(incidencias_enriquecidas),
            "permisos_hoy": permisos_hoy,
            "dispositivos_activos": m_row.get("dispositivos_activos", 0),
            "total_dispositivos": m_row.get("total_dispositivos", 0),
        },
        "asistencias_hoy": asistencias_enriquecidas,
        "historial_reciente": historial_enriquecido,
        "incidencias_hoy": incidencias_enriquecidas,
        "flujo_horario": flujo_horario,
    }


@router.post("/simular-asistencia")
def simular_marcaje_asistencia(req: SimularAsistenciaRequest):
    return registrar_marcaje_sql(
        usuario_id=req.usuario_id,
        codigo_qr=req.codigo_qr,
        dispositivo_id=req.dispositivo_id,
        forzar_tardanza=req.forzar_tardanza,
        aplicar_antirrebote=False,
        bloquear_si_jornada_completa=False,
    )
