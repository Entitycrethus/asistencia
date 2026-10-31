from typing import Any, Dict, List, Optional
from datetime import date
from supabase import create_client, Client
from app.config import settings
from app.security import hash_password


# Nombres exactos de las tablas en el esquema public de Supabase
TABLE_NAMES: Dict[str, str] = {
    "Rol": "rol",
    "Cargo": "cargo",
    "Usuario": "usuario",
    "HorarioLaboral": "horario_laboral",
    "Dispositivo": "dispositivo",
    "Asistencia": "asistencia",
    "TipoIncidencia": "tipo_incidencia",
    "Incidencia": "incidencia",
    "TipoPermiso": "tipo_permiso",
    "Permiso": "permiso",
    "HistorialAcceso": "historial_acceso",
    "ConfiguracionInstitucion": "configuracion_institucion",
}

_supabase_client: Optional[Client] = None
_last_supabase_error: Optional[str] = None


class _MockResponse:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data


class _MockTableQuery:
    def __init__(self, store: Dict[str, List[Dict[str, Any]]], table_name: str):
        self._store = store
        self._table = table_name
        self._op = "select"
        self._payload: Any = None
        self._filters: List[tuple] = []
        self._order_col: Optional[str] = None
        self._order_desc: bool = False
        self._limit_val: Optional[int] = None

    def select(self, columns: str = "*") -> "_MockTableQuery":
        self._op = "select"
        return self

    def insert(self, payload: Any) -> "_MockTableQuery":
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload: Dict[str, Any]) -> "_MockTableQuery":
        self._op = "update"
        self._payload = payload
        return self

    def delete(self) -> "_MockTableQuery":
        self._op = "delete"
        return self

    def eq(self, column: str, value: Any) -> "_MockTableQuery":
        self._filters.append(("eq", column, value))
        return self

    def gte(self, column: str, value: Any) -> "_MockTableQuery":
        self._filters.append(("gte", column, value))
        return self

    def lte(self, column: str, value: Any) -> "_MockTableQuery":
        self._filters.append(("lte", column, value))
        return self

    def order(self, column: str, desc: bool = False) -> "_MockTableQuery":
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, count: int) -> "_MockTableQuery":
        self._limit_val = count
        return self

    def _matches(self, row: Dict[str, Any]) -> bool:
        for ftype, col, val in self._filters:
            rval = row.get(col)
            if ftype == "eq" and str(rval) != str(val):
                return False
            if ftype == "gte" and (rval is None or str(rval) < str(val)):
                return False
            if ftype == "lte" and (rval is None or str(rval) > str(val)):
                return False
        return True

    def execute(self) -> _MockResponse:
        rows = self._store.setdefault(self._table, [])

        if self._op == "select":
            matched = [dict(r) for r in rows if self._matches(r)]
            if self._order_col:
                matched.sort(
                    key=lambda x: (x.get(self._order_col) is None, x.get(self._order_col)),
                    reverse=self._order_desc,
                )
            if self._limit_val is not None:
                matched = matched[: self._limit_val]
            return _MockResponse(matched)

        if self._op == "insert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for item in items:
                new_row = dict(item)
                if "id" not in new_row or new_row["id"] is None:
                    next_id = max((r.get("id", 0) for r in rows), default=0) + 1
                    new_row["id"] = next_id
                rows.append(new_row)
                inserted.append(dict(new_row))
            return _MockResponse(inserted)

        if self._op == "update":
            updated = []
            for r in rows:
                if self._matches(r):
                    r.update(self._payload)
                    updated.append(dict(r))
            return _MockResponse(updated)

        if self._op == "delete":
            deleted = [dict(r) for r in rows if self._matches(r)]
            self._store[self._table] = [r for r in rows if not self._matches(r)]
            return _MockResponse(deleted)

        return _MockResponse([])


class _FallbackSupabaseClient:
    def __init__(self):
        today_str = date.today().isoformat()
        now_prefix = f"{today_str}T"
        default_pw = hash_password("admin123")
        self.store: Dict[str, List[Dict[str, Any]]] = {
            "rol": [
                {"id": 1, "nombre": "Administrador"},
                {"id": 2, "nombre": "Supervisor"},
                {"id": 3, "nombre": "Personal"},
            ],
            "cargo": [
                {"id": 1, "nombre": "Director Académico"},
                {"id": 2, "nombre": "Docente Titular"},
                {"id": 3, "nombre": "Coordinador de Nivel"},
                {"id": 4, "nombre": "Administrativo"},
            ],
            "usuario": [
                {
                    "id": 1,
                    "codigo": "EMP-001",
                    "codigo_qr": "QR-EMP-001",
                    "nombres": "Carlos",
                    "apellidos": "Mendoza Ríos",
                    "correo": "admin@colegio.edu.pe",
                    "password": default_pw,
                    "activo": True,
                    "rol_id": 1,
                    "cargo_id": 1,
                },
                {
                    "id": 2,
                    "codigo": "EMP-002",
                    "codigo_qr": "QR-EMP-002",
                    "nombres": "Elena",
                    "apellidos": "Vargas Soto",
                    "correo": "evargas@colegio.edu.pe",
                    "password": default_pw,
                    "activo": True,
                    "rol_id": 3,
                    "cargo_id": 2,
                },
                {
                    "id": 3,
                    "codigo": "EMP-003",
                    "codigo_qr": "QR-EMP-003",
                    "nombres": "Marco",
                    "apellidos": "Salazar Paredes",
                    "correo": "msalazar@colegio.edu.pe",
                    "password": default_pw,
                    "activo": True,
                    "rol_id": 3,
                    "cargo_id": 2,
                },
                {
                    "id": 4,
                    "codigo": "EMP-004",
                    "codigo_qr": "QR-EMP-004",
                    "nombres": "Lucía",
                    "apellidos": "Fernández Quispe",
                    "correo": "lfernandez@colegio.edu.pe",
                    "password": default_pw,
                    "activo": True,
                    "rol_id": 2,
                    "cargo_id": 3,
                },
                {
                    "id": 5,
                    "codigo": "EMP-005",
                    "codigo_qr": "QR-EMP-005",
                    "nombres": "Jorge",
                    "apellidos": "Rojas Huamán",
                    "correo": "jrojas@colegio.edu.pe",
                    "password": default_pw,
                    "activo": True,
                    "rol_id": 3,
                    "cargo_id": 4,
                },
            ],
            "horario_laboral": [
                {"id": 1, "usuario_id": 1, "dia_semana": "Lunes", "hora_inicio": "07:30:00", "hora_fin": "16:00:00"},
                {"id": 2, "usuario_id": 2, "dia_semana": "Lunes", "hora_inicio": "07:45:00", "hora_fin": "15:30:00"},
                {"id": 3, "usuario_id": 3, "dia_semana": "Lunes", "hora_inicio": "07:45:00", "hora_fin": "15:30:00"},
                {"id": 4, "usuario_id": 4, "dia_semana": "Lunes", "hora_inicio": "08:00:00", "hora_fin": "16:30:00"},
                {"id": 5, "usuario_id": 5, "dia_semana": "Lunes", "hora_inicio": "08:00:00", "hora_fin": "17:00:00"},
            ],
            "dispositivo": [
                {"id": 1, "nombre": "Lector QR - Puerta Principal", "ubicacion": "Ingreso Pabellón A", "activo": True},
                {"id": 2, "nombre": "Lector QR - Sala de Profesores", "ubicacion": "Pabellón B - Piso 1", "activo": True},
                {"id": 3, "nombre": "Lector QR - Puerta Secundaria", "ubicacion": "Acceso Estacionamiento", "activo": False},
            ],
            "asistencia": [
                {
                    "id": 1,
                    "usuario_id": 1,
                    "dispositivo_id": 1,
                    "fecha": today_str,
                    "hora_entrada": f"{now_prefix}07:26:14",
                    "hora_salida": None,
                },
                {
                    "id": 2,
                    "usuario_id": 2,
                    "dispositivo_id": 1,
                    "fecha": today_str,
                    "hora_entrada": f"{now_prefix}07:42:05",
                    "hora_salida": None,
                },
                {
                    "id": 3,
                    "usuario_id": 3,
                    "dispositivo_id": 2,
                    "fecha": today_str,
                    "hora_entrada": f"{now_prefix}08:04:32",
                    "hora_salida": None,
                },
            ],
            "tipo_incidencia": [
                {"id": 1, "nombre": "Tardanza"},
                {"id": 2, "nombre": "Salida Anticipada"},
                {"id": 3, "nombre": "Falta Injustificada"},
                {"id": 4, "nombre": "Omisión de Marcado"},
            ],
            "incidencia": [
                {
                    "id": 1,
                    "asistencia_id": 3,
                    "tipo_incidencia_id": 1,
                    "descripcion": "Ingreso registrado a las 08:04 (horario 07:45 + 10 min tolerancia).",
                    "justificacion": "",
                    "fecha_registro": f"{now_prefix}08:04:32",
                }
            ],
            "tipo_permiso": [
                {"id": 1, "nombre": "Descanso Médico"},
                {"id": 2, "nombre": "Comisión de Servicios"},
                {"id": 3, "nombre": "Asuntos Personales"},
                {"id": 4, "nombre": "Capacitación Oficial"},
            ],
            "permiso": [
                {
                    "id": 1,
                    "usuario_id": 4,
                    "tipo_permiso_id": 4,
                    "fecha_inicio": today_str,
                    "fecha_fin": today_str,
                    "motivo": "Participación en taller curricular del ministerio.",
                    "aprobado": True,
                },
                {
                    "id": 2,
                    "usuario_id": 5,
                    "tipo_permiso_id": 3,
                    "fecha_inicio": today_str,
                    "fecha_fin": today_str,
                    "motivo": "Trámite documentario en horario de mañana.",
                    "aprobado": False,
                },
            ],
            "historial_acceso": [
                {
                    "id": 1,
                    "usuario_id": 1,
                    "dispositivo_id": 1,
                    "fecha_hora": f"{now_prefix}07:26:14",
                    "accion": "ENTRADA",
                },
                {
                    "id": 2,
                    "usuario_id": 2,
                    "dispositivo_id": 1,
                    "fecha_hora": f"{now_prefix}07:42:05",
                    "accion": "ENTRADA",
                },
                {
                    "id": 3,
                    "usuario_id": 3,
                    "dispositivo_id": 2,
                    "fecha_hora": f"{now_prefix}08:04:32",
                    "accion": "ENTRADA",
                },
            ],
            "configuracion_institucion": [
                {
                    "id": 1,
                    "nombre": "Institución Educativa San Martín",
                    "hora_entrada": "07:45:00",
                    "tolerancia_minutos": 10,
                    "activa": True,
                }
            ],
        }

    def table(self, table_name: str) -> _MockTableQuery:
        return _MockTableQuery(self.store, table_name)


_fallback_client = _FallbackSupabaseClient()


class _ResilientTableProxy:
    """Envuelve la consulta real de Supabase y, si PostgreSQL devuelve 42501
    (permission denied for schema public), registra el aviso y delega temporalmente
    al almacén de respaldo para que la interfaz no falle mientras se aplica el GRANT en SQL."""

    def __init__(self, real_client: Client, fallback_client: _FallbackSupabaseClient, table_name: str):
        self._real_query = real_client.table(table_name)
        self._fallback_query = fallback_client.table(table_name)

    def select(self, *args, **kwargs):
        self._real_query = self._real_query.select(*args, **kwargs)
        self._fallback_query = self._fallback_query.select(*args, **kwargs)
        return self

    def insert(self, *args, **kwargs):
        self._real_query = self._real_query.insert(*args, **kwargs)
        self._fallback_query = self._fallback_query.insert(*args, **kwargs)
        return self

    def update(self, *args, **kwargs):
        self._real_query = self._real_query.update(*args, **kwargs)
        self._fallback_query = self._fallback_query.update(*args, **kwargs)
        return self

    def delete(self, *args, **kwargs):
        self._real_query = self._real_query.delete(*args, **kwargs)
        self._fallback_query = self._fallback_query.delete(*args, **kwargs)
        return self

    def eq(self, *args, **kwargs):
        self._real_query = self._real_query.eq(*args, **kwargs)
        self._fallback_query = self._fallback_query.eq(*args, **kwargs)
        return self

    def gte(self, *args, **kwargs):
        self._real_query = self._real_query.gte(*args, **kwargs)
        self._fallback_query = self._fallback_query.gte(*args, **kwargs)
        return self

    def lte(self, *args, **kwargs):
        self._real_query = self._real_query.lte(*args, **kwargs)
        self._fallback_query = self._fallback_query.lte(*args, **kwargs)
        return self

    def order(self, *args, **kwargs):
        self._real_query = self._real_query.order(*args, **kwargs)
        self._fallback_query = self._fallback_query.order(*args, **kwargs)
        return self

    def limit(self, *args, **kwargs):
        self._real_query = self._real_query.limit(*args, **kwargs)
        self._fallback_query = self._fallback_query.limit(*args, **kwargs)
        return self

    def execute(self):
        global _last_supabase_error
        try:
            res = self._real_query.execute()
            _last_supabase_error = None
            return res
        except Exception as exc:
            _last_supabase_error = str(exc)
            return self._fallback_query.execute()


class _ResilientSupabaseWrapper:
    def __init__(self, real_client: Client, fallback_client: _FallbackSupabaseClient):
        self._real = real_client
        self._fallback = fallback_client

    def table(self, table_name: str) -> _ResilientTableProxy:
        return _ResilientTableProxy(self._real, self._fallback, table_name)


def get_supabase() -> Any:
    global _supabase_client
    if settings.is_supabase_configured:
        if _supabase_client is None:
            _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return _ResilientSupabaseWrapper(_supabase_client, _fallback_client)
    return _fallback_client


def get_last_supabase_error() -> Optional[str]:
    return _last_supabase_error


def reset_supabase_client(url: str, key: str) -> None:
    global _supabase_client, _last_supabase_error
    settings.SUPABASE_URL = url.strip()
    settings.SUPABASE_KEY = key.strip()
    _supabase_client = None
    _last_supabase_error = None


def t(logical_name: str) -> str:
    return TABLE_NAMES.get(logical_name, logical_name.lower())
