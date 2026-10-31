from datetime import date
from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException
from app.database import fetch_all, execute_returning
from app.routers.dashboard import procesar_faltas_automaticas, registrar_marcaje_sql
from app.schemas import (
    Asistencia,
    Incidencia,
    IncidenciaCreate,
    IncidenciaJustificar,
    HistorialAcceso,
    TipoIncidencia,
    ResumenFaltasUsuario,
    MarcarQRRequest,
    MarcarQRResponse,
)

router = APIRouter(prefix="/api/asistencias", tags=["Asistencias e Incidencias"])


@router.post("/marcar-qr", response_model=MarcarQRResponse)
def marcar_asistencia_desde_qr_movil(req: MarcarQRRequest):
  
  
    resultado = registrar_marcaje_sql(
        codigo_qr=req.codigo_qr,
        dispositivo_id=req.dispositivo_id,
        forzar_tardanza=False,
        aplicar_antirrebote=True,
        bloquear_si_jornada_completa=True,
    )
    return MarcarQRResponse(**resultado)


@router.get("", response_model=List[Asistencia])
def listar_asistencias(
    fecha: Optional[str] = None,
    usuario_id: Optional[int] = None,
    solo_faltas: Optional[bool] = None,
):
    procesar_faltas_automaticas(target_date=fecha or date.today().isoformat(), forzar_cierre=False)

    condiciones = []
    params: List[Any] = []

    if fecha:
        condiciones.append("a.fecha = %s::DATE")
        params.append(fecha)
    if usuario_id is not None:
        condiciones.append("a.usuario_id = %s")
        params.append(usuario_id)
    if solo_faltas is True:
        condiciones.append(
            """(
                a.hora_entrada IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM public.incidencia i2
                    INNER JOIN public.tipo_incidencia ti2 ON ti2.id = i2.tipo_incidencia_id
                    WHERE i2.asistencia_id = a.id
                      AND LOWER(ti2.nombre) LIKE '%%falta%%'
                )
            )"""
        )

    where_sql = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    sql = f"""
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
                SELECT 1
                FROM public.incidencia i
                WHERE i.asistencia_id = a.id
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
        {where_sql}
        ORDER BY a.id DESC;
    """
    rows = fetch_all(sql, tuple(params))
    return [Asistencia(**r) for r in rows]


@router.get("/resumen-usuarios", response_model=List[ResumenFaltasUsuario])
def obtener_resumen_faltas_por_usuario():
    procesar_faltas_automaticas(target_date=date.today().isoformat(), forzar_cierre=False)

    sql = """
        SELECT
            u.id AS usuario_id,
            u.codigo,
            (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
            c.nombre AS cargo_nombre,
            COUNT(DISTINCT CASE WHEN a.hora_entrada IS NOT NULL THEN a.id END)::INT AS total_asistencias,
            COUNT(DISTINCT CASE
                WHEN a.id IS NOT NULL AND (a.hora_entrada IS NULL OR LOWER(ti.nombre) LIKE '%%falta%%')
                THEN a.id
            END)::INT AS total_faltas,
            COUNT(DISTINCT CASE
                WHEN LOWER(ti.nombre) LIKE '%%falta%%' AND COALESCE(TRIM(i.justificacion), '') <> ''
                THEN i.id
            END)::INT AS faltas_justificadas,
            (
                COUNT(DISTINCT CASE
                    WHEN a.id IS NOT NULL AND (a.hora_entrada IS NULL OR LOWER(ti.nombre) LIKE '%%falta%%')
                    THEN a.id
                END)
                -
                COUNT(DISTINCT CASE
                    WHEN LOWER(ti.nombre) LIKE '%%falta%%' AND COALESCE(TRIM(i.justificacion), '') <> ''
                    THEN i.id
                END)
            )::INT AS faltas_injustificadas,
            COUNT(DISTINCT CASE WHEN LOWER(ti.nombre) LIKE '%%tardanza%%' THEN i.id END)::INT AS total_tardanzas,
            COUNT(DISTINCT CASE WHEN LOWER(ti.nombre) LIKE '%%salida%%' THEN i.id END)::INT AS total_salidas_anticipadas
        FROM public.usuario u
        INNER JOIN public.cargo c ON c.id = u.cargo_id
        LEFT JOIN public.asistencia a ON a.usuario_id = u.id
        LEFT JOIN public.incidencia i ON i.asistencia_id = a.id
        LEFT JOIN public.tipo_incidencia ti ON ti.id = i.tipo_incidencia_id
        GROUP BY u.id, u.codigo, u.nombres, u.apellidos, c.nombre
        ORDER BY total_faltas DESC, total_tardanzas DESC, total_asistencias DESC;
    """
    rows = fetch_all(sql)
    return [ResumenFaltasUsuario(**r) for r in rows]


@router.get("/historial", response_model=List[HistorialAcceso])
def listar_historial_acceso(limit: int = 50):
    sql = """
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
        LIMIT %s;
    """
    rows = fetch_all(sql, (limit,))
    return [HistorialAcceso(**r) for r in rows]


@router.get("/incidencias", response_model=List[Incidencia])
def listar_incidencias(
    usuario_id: Optional[int] = None,
    tipo_incidencia_id: Optional[int] = None,
):
    condiciones = []
    params: List[Any] = []
    if usuario_id is not None:
        condiciones.append("a.usuario_id = %s")
        params.append(usuario_id)
    if tipo_incidencia_id is not None:
        condiciones.append("i.tipo_incidencia_id = %s")
        params.append(tipo_incidencia_id)

    where_sql = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    sql = f"""
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
        {where_sql}
        ORDER BY i.id DESC;
    """
    rows = fetch_all(sql, tuple(params))
    return [Incidencia(**r) for r in rows]


@router.post("/incidencias", response_model=Incidencia)
def crear_incidencia(payload: IncidenciaCreate):
    sql = """
        INSERT INTO public.incidencia (
            asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro
        )
        VALUES (%s, %s, %s, %s, COALESCE(%s::TIMESTAMP, NOW()))
        RETURNING
            id,
            asistencia_id,
            tipo_incidencia_id,
            descripcion,
            COALESCE(justificacion, '') AS justificacion,
            fecha_registro::TEXT AS fecha_registro;
    """
    row = execute_returning(
        sql,
        (
            payload.asistencia_id,
            payload.tipo_incidencia_id,
            payload.descripcion,
            payload.justificacion,
            payload.fecha_registro,
        ),
    )
    if not row:
        raise HTTPException(status_code=400, detail="No se pudo registrar la incidencia.")
    return Incidencia(**row)


@router.patch("/incidencias/{incidencia_id}/justificar", response_model=Incidencia)
def justificar_incidencia(incidencia_id: int, body: IncidenciaJustificar):
    sql = """
        UPDATE public.incidencia
        SET justificacion = %s
        WHERE id = %s
        RETURNING
            id,
            asistencia_id,
            tipo_incidencia_id,
            descripcion,
            COALESCE(justificacion, '') AS justificacion,
            fecha_registro::TEXT AS fecha_registro;
    """
    row = execute_returning(sql, (body.justificacion, incidencia_id))
    if not row:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada.")
    return Incidencia(**row)


@router.get("/tipos-incidencia", response_model=List[TipoIncidencia])
def listar_tipos_incidencia():
    rows = fetch_all("SELECT id, nombre FROM public.tipo_incidencia ORDER BY id ASC;")
    return [TipoIncidencia(**r) for r in rows]
