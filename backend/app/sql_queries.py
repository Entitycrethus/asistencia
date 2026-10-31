"""
Módulo central de consultas SQL relacionales (INNER JOIN, LEFT JOIN, GROUP BY,
CASE WHEN, Subconsultas correlacionadas EXISTS/NOT EXISTS y llamadas a
Procedimientos Almacenados / Funciones en PL/pgSQL).
"""

# =============================================================================
# 1. AUTENTICACIÓN Y USUARIOS (INNER JOIN con rol y cargo)
# =============================================================================
SQL_OBTENER_USUARIO_LOGIN = """
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
WHERE u.correo = '{correo}'
LIMIT 1
"""

SQL_LISTAR_USUARIOS_CON_ROL_Y_CARGO = """
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
ORDER BY u.id ASC
"""

SQL_LISTAR_HORARIOS_CON_USUARIO = """
SELECT
    hl.id,
    hl.usuario_id,
    hl.dia_semana,
    hl.hora_inicio::TEXT AS hora_inicio,
    hl.hora_fin::TEXT AS hora_fin,
    (u.nombres || ' ' || u.apellidos) AS usuario_nombre
FROM public.horario_laboral hl
INNER JOIN public.usuario u ON u.id = hl.usuario_id
{filtro_usuario}
ORDER BY hl.usuario_id ASC, hl.id ASC
"""


# =============================================================================
# 2. ASISTENCIAS DETALLADAS (INNER JOIN, LEFT JOIN y SUBCONSULTAS EXISTS)
# =============================================================================
SQL_LISTAR_ASISTENCIAS_DETALLADAS = """
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
    -- Subconsulta EXISTS para determinar si la asistencia registra alguna incidencia
    EXISTS (
        SELECT 1
        FROM public.incidencia i
        WHERE i.asistencia_id = a.id
    ) AS tiene_incidencia,
    -- Subconsulta EXISTS para determinar si corresponde a una Falta
    (
        a.hora_entrada IS NULL
        OR EXISTS (
            SELECT 1
            FROM public.incidencia i2
            INNER JOIN public.tipo_incidencia ti2 ON ti2.id = i2.tipo_incidencia_id
            WHERE i2.asistencia_id = a.id
              AND LOWER(ti2.nombre) LIKE '%falta%'
        )
    ) AS es_falta,
    -- Subconsulta escalar para obtener el nombre del tipo de incidencia
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
{where_clause}
ORDER BY a.id DESC
"""


# =============================================================================
# 3. CONSOLIDADO DE FALTAS E INCIDENCIAS POR USUARIO
#    (LEFT JOIN + GROUP BY + COUNT DISTINCT + CASE WHEN)
# =============================================================================
SQL_RESUMEN_FALTAS_POR_USUARIO = """
SELECT
    u.id AS usuario_id,
    u.codigo,
    (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
    c.nombre AS cargo_nombre,
    COUNT(DISTINCT CASE WHEN a.hora_entrada IS NOT NULL THEN a.id END)::INT AS total_asistencias,
    COUNT(DISTINCT CASE
        WHEN a.id IS NOT NULL AND (a.hora_entrada IS NULL OR LOWER(ti.nombre) LIKE '%falta%')
        THEN a.id
    END)::INT AS total_faltas,
    COUNT(DISTINCT CASE
        WHEN LOWER(ti.nombre) LIKE '%falta%' AND COALESCE(TRIM(i.justificacion), '') <> ''
        THEN i.id
    END)::INT AS faltas_justificadas,
    (
        COUNT(DISTINCT CASE
            WHEN a.id IS NOT NULL AND (a.hora_entrada IS NULL OR LOWER(ti.nombre) LIKE '%falta%')
            THEN a.id
        END)
        -
        COUNT(DISTINCT CASE
            WHEN LOWER(ti.nombre) LIKE '%falta%' AND COALESCE(TRIM(i.justificacion), '') <> ''
            THEN i.id
        END)
    )::INT AS faltas_injustificadas,
    COUNT(DISTINCT CASE WHEN LOWER(ti.nombre) LIKE '%tardanza%' THEN i.id END)::INT AS total_tardanzas,
    COUNT(DISTINCT CASE WHEN LOWER(ti.nombre) LIKE '%salida%' THEN i.id END)::INT AS total_salidas_anticipadas
FROM public.usuario u
INNER JOIN public.cargo c ON c.id = u.cargo_id
LEFT JOIN public.asistencia a ON a.usuario_id = u.id
LEFT JOIN public.incidencia i ON i.asistencia_id = a.id
LEFT JOIN public.tipo_incidencia ti ON ti.id = i.tipo_incidencia_id
GROUP BY u.id, u.codigo, u.nombres, u.apellidos, c.nombre
ORDER BY total_faltas DESC, total_tardanzas DESC, total_asistencias DESC
"""


# =============================================================================
# 4. INCIDENCIAS CON TRIPLE INNER JOIN (incidencia + asistencia + usuario + tipo_incidencia)
# =============================================================================
SQL_LISTAR_INCIDENCIAS_DETALLADAS = """
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
{where_clause}
ORDER BY i.id DESC
"""


# =============================================================================
# 5. HISTORIAL DE ACCESO Y PERMISOS CON INNER JOIN
# =============================================================================
SQL_LISTAR_HISTORIAL_ACCESO = """
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
LIMIT {limit}
"""

SQL_LISTAR_PERMISOS_DETALLADOS = """
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
ORDER BY p.id DESC
"""


# =============================================================================
# 6. SUBCONSULTA CON NOT EXISTS PARA DETECCIÓN DE FALTAS POR HORARIO VENCIDO
# =============================================================================
SQL_SUBCONSULTA_USUARIOS_SIN_MARCAJE_HORA_VENCIDA = """
SELECT
    u.id AS usuario_id,
    u.codigo,
    (u.nombres || ' ' || u.apellidos) AS usuario_nombre,
    hl.dia_semana,
    hl.hora_inicio::TEXT AS hora_inicio,
    hl.hora_fin::TEXT AS hora_fin
FROM public.usuario u
INNER JOIN public.horario_laboral hl ON hl.usuario_id = u.id
WHERE u.activo = TRUE
  AND LOWER(TRANSLATE(hl.dia_semana, 'áéíóúÁÉÍÓÚ', 'aeiouAEIOU')) = '{dia_semana}'
  AND ({forzar_cierre} = TRUE OR CURRENT_TIME >= hl.hora_fin)
  AND NOT EXISTS (
      SELECT 1
      FROM public.asistencia a
      WHERE a.usuario_id = u.id
        AND a.fecha = '{fecha}'
  )
  AND NOT EXISTS (
      SELECT 1
      FROM public.permiso p
      WHERE p.usuario_id = u.id
        AND p.aprobado = TRUE
        AND '{fecha}'::DATE BETWEEN LEAST(p.fecha_inicio, p.fecha_fin)
                                AND GREATEST(p.fecha_inicio, p.fecha_fin)
  )
"""

