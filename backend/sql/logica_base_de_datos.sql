-- =============================================================================
-- SISTEMA DE GESTIÓN DE ASISTENCIA - LÓGICA AVANZADA DE BASE DE DATOS (PostgreSQL)
-- Curso: Base de Datos
-- Incluye:
--   1. Consultas con INNER JOIN, LEFT JOIN, GROUP BY y CASE WHEN (Vistas SQL)
--   2. Subconsultas correlacionadas (EXISTS / NOT EXISTS / IN)
--   3. Procedimientos Almacenados / Funciones Transaccionales en PL/pgSQL
--   4. Triggers (Disparadores automáticos para HistorialAcceso e Incidencias)
-- =============================================================================

-- Permisos sobre el esquema public para la API de Supabase
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;


-- =============================================================================
-- 1. FUNCIÓN EJECUTORA DE CONSULTAS SQL DINÁMICAS DESDE EL BACKEND (FastAPI)
-- Permite que FastAPI envíe sentencias SQL con JOINs y Subconsultas y reciba JSON.
-- =============================================================================
CREATE OR REPLACE FUNCTION public.fn_ejecutar_sql_consulta(p_sql TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_resultado JSONB;
BEGIN
    EXECUTE format('SELECT COALESCE(jsonb_agg(t), ''[]''::jsonb) FROM (%s) t', p_sql)
    INTO v_resultado;
    RETURN v_resultado;
END;
$$;


-- =============================================================================
-- 2. VISTAS CON INNER JOIN, LEFT JOIN Y SUBCONSULTAS
-- =============================================================================

-- 2.1 Vista detallada de Asistencias (INNER JOIN + LEFT JOIN + Subconsulta)
CREATE OR REPLACE VIEW public.vw_asistencia_detallada AS
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
    r.nombre AS rol_nombre,
    d.nombre AS dispositivo_nombre,
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
              AND LOWER(ti2.nombre) LIKE '%falta%'
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
INNER JOIN public.rol r ON r.id = u.rol_id
LEFT JOIN public.dispositivo d ON d.id = a.dispositivo_id;


-- 2.2 Vista detallada de Incidencias (Triple INNER JOIN)
CREATE OR REPLACE VIEW public.vw_incidencias_detalladas AS
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
INNER JOIN public.tipo_incidencia ti ON ti.id = i.tipo_incidencia_id;


-- 2.3 Vista consolidada de Faltas, Tardanzas y Asistencias por Usuario
-- Utiliza LEFT JOIN, GROUP BY, COUNT, SUM(CASE WHEN ...) y Subconsultas
CREATE OR REPLACE VIEW public.vw_resumen_faltas_por_usuario AS
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
ORDER BY total_faltas DESC, total_tardanzas DESC, total_asistencias DESC;


-- =============================================================================
-- 3. TRIGGER AUTOMÁTICO EN LA BASE DE DATOS (HISTORIAL E INCIDENCIAS)
-- Cuando se inserta o actualiza en `asistencia`, el motor PostgreSQL:
--   a) Registra automáticamente el evento en `historial_acceso` (ENTRADA / SALIDA)
--   b) Evalúa el `horario_laboral` y `configuracion_institucion` para generar
--      automáticamente la `incidencia` de Tardanza o Salida Anticipada.
-- =============================================================================
CREATE OR REPLACE FUNCTION public.fn_trigger_procesar_asistencia()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_dia_semana TEXT;
    v_hora_inicio TIME;
    v_hora_fin TIME;
    v_tolerancia INT := 10;
    v_hora_limite TIME;
    v_tipo_tardanza_id INT;
    v_tipo_falta_id INT;
    v_tipo_salida_id INT;
BEGIN
    -- Determinar el nombre del día de la semana según la fecha de asistencia
    v_dia_semana := CASE EXTRACT(ISODOW FROM NEW.fecha)
        WHEN 1 THEN 'lunes'
        WHEN 2 THEN 'martes'
        WHEN 3 THEN 'miercoles'
        WHEN 4 THEN 'jueves'
        WHEN 5 THEN 'viernes'
        WHEN 6 THEN 'sabado'
        WHEN 7 THEN 'domingo'
    END;

    -- Obtener horario laboral del usuario para ese día (Subconsulta)
    SELECT hl.hora_inicio, hl.hora_fin
    INTO v_hora_inicio, v_hora_fin
    FROM public.horario_laboral hl
    WHERE hl.usuario_id = NEW.usuario_id
      AND LOWER(TRANSLATE(hl.dia_semana, 'áéíóúÁÉÍÓÚ', 'aeiouAEIOU')) = v_dia_semana
    LIMIT 1;

    -- Obtener tolerancia e ingreso por defecto desde configuracion_institucion
    SELECT COALESCE(ci.tolerancia_minutos, 10), COALESCE(v_hora_inicio, ci.hora_entrada, '08:00:00'::TIME)
    INTO v_tolerancia, v_hora_inicio
    FROM public.configuracion_institucion ci
    WHERE ci.activa = TRUE
    LIMIT 1;

    v_hora_inicio := COALESCE(v_hora_inicio, '08:00:00'::TIME);
    v_hora_fin := COALESCE(v_hora_fin, '13:00:00'::TIME);
    v_hora_limite := v_hora_inicio + make_interval(mins => v_tolerancia);

    -- Resolver IDs de tipo_incidencia
    SELECT id INTO v_tipo_tardanza_id FROM public.tipo_incidencia WHERE LOWER(nombre) LIKE '%tardanza%' LIMIT 1;
    SELECT id INTO v_tipo_falta_id FROM public.tipo_incidencia WHERE LOWER(nombre) LIKE '%falta%' LIMIT 1;
    SELECT id INTO v_tipo_salida_id FROM public.tipo_incidencia WHERE LOWER(nombre) LIKE '%salida%' LIMIT 1;

    v_tipo_tardanza_id := COALESCE(v_tipo_tardanza_id, 1);
    v_tipo_falta_id := COALESCE(v_tipo_falta_id, 2);
    v_tipo_salida_id := COALESCE(v_tipo_salida_id, 3);

    -- CASO 1: Se inserta una FALTA (hora_entrada IS NULL)
    IF TG_OP = 'INSERT' AND NEW.hora_entrada IS NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.incidencia
            WHERE asistencia_id = NEW.id AND tipo_incidencia_id = v_tipo_falta_id
        ) THEN
            INSERT INTO public.incidencia (asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro)
            VALUES (
                NEW.id,
                v_tipo_falta_id,
                format('Falta automática: no registró asistencia hasta el cierre de su horario (%s).', v_hora_fin),
                NULL,
                NOW()
            );
        END IF;
        RETURN NEW;
    END IF;

    -- CASO 2: Se registra ENTRADA (INSERT con hora_entrada o UPDATE pasando de NULL a hora_entrada)
    IF (TG_OP = 'INSERT' AND NEW.hora_entrada IS NOT NULL)
       OR (TG_OP = 'UPDATE' AND OLD.hora_entrada IS NULL AND NEW.hora_entrada IS NOT NULL) THEN

        INSERT INTO public.historial_acceso (usuario_id, dispositivo_id, fecha_hora, accion)
        VALUES (NEW.usuario_id, COALESCE(NEW.dispositivo_id, 1), NOW(), 'ENTRADA');

        -- Evaluar Tardanza
        IF NEW.hora_entrada > v_hora_limite THEN
            IF NOT EXISTS (
                SELECT 1 FROM public.incidencia
                WHERE asistencia_id = NEW.id AND tipo_incidencia_id = v_tipo_tardanza_id
            ) THEN
                INSERT INTO public.incidencia (asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro)
                VALUES (
                    NEW.id,
                    v_tipo_tardanza_id,
                    format('Ingreso fuera de tolerancia (%s, límite %s).', NEW.hora_entrada, v_hora_limite),
                    NULL,
                    NOW()
                );
            END IF;
        END IF;
    END IF;

    -- CASO 3: Se registra SALIDA (UPDATE pasando de hora_salida NULL a NOT NULL)
    IF TG_OP = 'UPDATE' AND OLD.hora_salida IS NULL AND NEW.hora_salida IS NOT NULL THEN
        INSERT INTO public.historial_acceso (usuario_id, dispositivo_id, fecha_hora, accion)
        VALUES (NEW.usuario_id, COALESCE(NEW.dispositivo_id, 1), NOW(), 'SALIDA');

        -- Evaluar Salida Anticipada
        IF NEW.hora_salida < v_hora_fin THEN
            IF NOT EXISTS (
                SELECT 1 FROM public.incidencia
                WHERE asistencia_id = NEW.id AND tipo_incidencia_id = v_tipo_salida_id
            ) THEN
                INSERT INTO public.incidencia (asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro)
                VALUES (
                    NEW.id,
                    v_tipo_salida_id,
                    format('Salida anticipada registrada a las %s (horario fin %s).', NEW.hora_salida, v_hora_fin),
                    NULL,
                    NOW()
                );
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_procesar_asistencia ON public.asistencia;
CREATE TRIGGER trg_procesar_asistencia
AFTER INSERT OR UPDATE ON public.asistencia
FOR EACH ROW
EXECUTE FUNCTION public.fn_trigger_procesar_asistencia();


-- =============================================================================
-- 4. PROCEDIMIENTO ALMACENADO (FUNCIÓN PL/pgSQL) PARA MARCAR FALTAS AUTOMÁTICAS
-- Utiliza SUBCONSULTAS (NOT EXISTS) sobre `asistencia` y `permiso`
-- =============================================================================
CREATE OR REPLACE FUNCTION public.fn_evaluar_faltas_automaticas(
    p_fecha DATE DEFAULT CURRENT_DATE,
    p_forzar_cierre BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    usuario_id INT,
    usuario_nombre TEXT,
    hora_limite TIME,
    asistencia_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_dia_semana TEXT;
    v_disp_default INT;
    v_tipo_falta_id INT;
    rec RECORD;
    v_new_asist_id BIGINT;
BEGIN
    v_dia_semana := CASE EXTRACT(ISODOW FROM p_fecha)
        WHEN 1 THEN 'lunes'
        WHEN 2 THEN 'martes'
        WHEN 3 THEN 'miercoles'
        WHEN 4 THEN 'jueves'
        WHEN 5 THEN 'viernes'
        WHEN 6 THEN 'sabado'
        WHEN 7 THEN 'domingo'
    END;

    SELECT id INTO v_disp_default FROM public.dispositivo ORDER BY id ASC LIMIT 1;
    v_disp_default := COALESCE(v_disp_default, 1);

    SELECT id INTO v_tipo_falta_id FROM public.tipo_incidencia WHERE LOWER(nombre) LIKE '%falta%' LIMIT 1;
    v_tipo_falta_id := COALESCE(v_tipo_falta_id, 2);

    FOR rec IN
        SELECT
            u.id AS uid,
            (u.nombres || ' ' || u.apellidos) AS nombre_completo,
            hl.hora_fin AS h_fin
        FROM public.usuario u
        INNER JOIN public.horario_laboral hl ON hl.usuario_id = u.id
        WHERE u.activo = TRUE
          AND LOWER(TRANSLATE(hl.dia_semana, 'áéíóúÁÉÍÓÚ', 'aeiouAEIOU')) = v_dia_semana
          -- Condición de hora límite superada (hora_fin del horario laboral)
          AND (
              p_forzar_cierre = TRUE
              OR p_fecha < CURRENT_DATE
              OR (p_fecha = CURRENT_DATE AND CURRENT_TIME >= hl.hora_fin)
          )
          -- SUBCONSULTA 1: No existe asistencia registrada en esa fecha
          AND NOT EXISTS (
              SELECT 1
              FROM public.asistencia a
              WHERE a.usuario_id = u.id
                AND a.fecha = p_fecha
          )
          -- SUBCONSULTA 2: No existe permiso aprobado vigente para esa fecha
          AND NOT EXISTS (
              SELECT 1
              FROM public.permiso p
              WHERE p.usuario_id = u.id
                AND p.aprobado = TRUE
                AND p_fecha BETWEEN LEAST(p.fecha_inicio, p.fecha_fin)
                                AND GREATEST(p.fecha_inicio, p.fecha_fin)
          )
    LOOP
        INSERT INTO public.asistencia (usuario_id, dispositivo_id, fecha, hora_entrada, hora_salida)
        VALUES (rec.uid, v_disp_default, p_fecha, NULL, NULL)
        RETURNING id INTO v_new_asist_id;

        -- Asegurar creación de la incidencia de Falta si el trigger aún no estaba activo
        IF NOT EXISTS (
            SELECT 1 FROM public.incidencia i
            WHERE i.asistencia_id = v_new_asist_id
        ) THEN
            INSERT INTO public.incidencia (asistencia_id, tipo_incidencia_id, descripcion, justificacion, fecha_registro)
            VALUES (
                v_new_asist_id,
                v_tipo_falta_id,
                format('Falta automática: no registró asistencia hasta el cierre de su horario (%s).', rec.h_fin),
                NULL,
                NOW()
            );
        END IF;

        usuario_id := rec.uid;
        usuario_nombre := rec.nombre_completo;
        hora_limite := rec.h_fin;
        asistencia_id := v_new_asist_id;
        RETURN NEXT;
    END LOOP;
END;
$$;

GRANT EXECUTE ON FUNCTION public.fn_ejecutar_sql_consulta(TEXT) TO postgres, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.fn_evaluar_faltas_automaticas(DATE, BOOLEAN) TO postgres, anon, authenticated, service_role;

