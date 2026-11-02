from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException
from app.config import settings
from app.websocket_manager import ws_manager


@contextmanager
def get_db_connection():
    """
    Abre una conexión directa al motor PostgreSQL de Supabase utilizando psycopg2.
    """
    if not settings.is_db_configured:
        raise HTTPException(
            status_code=500,
            detail=(
                "Falta colocar la contraseña real de tu base de datos en DATABASE_URL "
                "dentro de backend/.env (reemplaza [YOUR-PASSWORD])."
            ),
        )
    conn = None
    try:
        conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
        yield conn
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos PostgreSQL: {exc}")
    finally:
        if conn:
            conn.close()


def fetch_all(sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
    """Ejecuta una sentencia SELECT SQL y devuelve todas las filas como diccionarios."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def fetch_one(sql: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
    """Ejecuta una sentencia SELECT SQL y devuelve una sola fila o None."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None


def _detect_op_and_table(sql: str) -> Tuple[str, str]:
    clean = " ".join(sql.strip().split()).upper()
    op = clean.split(" ")[0] if clean else "CHANGE"
    for tbl in ("asistencia", "historial_acceso", "incidencia", "permiso", "usuario", "horario_laboral", "dispositivo"):
        if f"PUBLIC.{tbl.upper()}" in clean or f" {tbl.upper()} " in clean:
            return op, tbl
    return op, "asistencia"


def execute_returning(sql: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
    """
    Ejecuta un INSERT / UPDATE / DELETE con RETURNING, confirma la transacción (COMMIT)
    y emite la notificación en tiempo real por WebSocket a los clientes conectados.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone() if cur.description else None
            conn.commit()
            op, tbl = _detect_op_and_table(sql)
            ws_manager.notify_from_sync(event_type=op, table=tbl)
            return dict(row) if row else None


def execute_commit(sql: str, params: Optional[Tuple[Any, ...]] = None) -> int:
    """
    Ejecuta una sentencia DML (INSERT, UPDATE, DELETE), confirma la transacción (COMMIT)
    y emite la notificación en tiempo real por WebSocket.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            affected = cur.rowcount
            conn.commit()
            op, tbl = _detect_op_and_table(sql)
            ws_manager.notify_from_sync(event_type=op, table=tbl)
            return affected
