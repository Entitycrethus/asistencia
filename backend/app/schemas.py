from typing import Optional
from pydantic import BaseModel, Field


# ==========================================
# 1. ROL & CARGO
# ==========================================
class RolBase(BaseModel):
    nombre: str


class RolCreate(RolBase):
    pass


class Rol(RolBase):
    id: int


class CargoBase(BaseModel):
    nombre: str


class CargoCreate(CargoBase):
    pass


class Cargo(CargoBase):
    id: int


# ==========================================
# 2. USUARIO
# ==========================================
class UsuarioBase(BaseModel):
    codigo: str
    codigo_qr: str
    nombres: str
    apellidos: str
    correo: str
    activo: bool = True
    rol_id: int
    cargo_id: int


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=4)


class UsuarioUpdate(BaseModel):
    codigo: Optional[str] = None
    codigo_qr: Optional[str] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    correo: Optional[str] = None
    password: Optional[str] = None
    activo: Optional[bool] = None
    rol_id: Optional[int] = None
    cargo_id: Optional[int] = None


class Usuario(UsuarioBase):
    id: int
    rol_nombre: Optional[str] = None
    cargo_nombre: Optional[str] = None


# ==========================================
# 3. HORARIO LABORAL
# ==========================================
class HorarioLaboralBase(BaseModel):
    usuario_id: int
    dia_semana: str
    hora_inicio: str
    hora_fin: str


class HorarioLaboralCreate(HorarioLaboralBase):
    pass


class HorarioLaboral(HorarioLaboralBase):
    id: int
    usuario_nombre: Optional[str] = None


# ==========================================
# 4. DISPOSITIVO
# ==========================================
class DispositivoBase(BaseModel):
    nombre: str
    ubicacion: str
    activo: bool = True


class DispositivoCreate(DispositivoBase):
    pass


class DispositivoUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    activo: Optional[bool] = None


class Dispositivo(DispositivoBase):
    id: int


# ==========================================
# 5. ASISTENCIA
# ==========================================
class AsistenciaBase(BaseModel):
    usuario_id: int
    dispositivo_id: int
    fecha: str
    hora_entrada: Optional[str] = None
    hora_salida: Optional[str] = None


class AsistenciaCreate(AsistenciaBase):
    pass


class Asistencia(AsistenciaBase):
    id: int
    usuario_nombre: Optional[str] = None
    usuario_codigo: Optional[str] = None
    cargo_nombre: Optional[str] = None
    dispositivo_nombre: Optional[str] = None
    tiene_incidencia: bool = False
    es_falta: bool = False
    tipo_incidencia_nombre: Optional[str] = None


# ==========================================
# 6. TIPO INCIDENCIA & INCIDENCIA
# ==========================================
class TipoIncidenciaBase(BaseModel):
    nombre: str


class TipoIncidenciaCreate(TipoIncidenciaBase):
    pass


class TipoIncidencia(TipoIncidenciaBase):
    id: int


class IncidenciaBase(BaseModel):
    asistencia_id: int
    tipo_incidencia_id: int
    descripcion: str
    justificacion: Optional[str] = ""
    fecha_registro: Optional[str] = None


class IncidenciaCreate(IncidenciaBase):
    pass


class IncidenciaJustificar(BaseModel):
    justificacion: str


class Incidencia(IncidenciaBase):
    id: int
    usuario_id: Optional[int] = None
    usuario_codigo: Optional[str] = None
    tipo_incidencia_nombre: Optional[str] = None
    usuario_nombre: Optional[str] = None
    fecha_asistencia: Optional[str] = None


# ==========================================
# 7. TIPO PERMISO & PERMISO
# ==========================================
class TipoPermisoBase(BaseModel):
    nombre: str


class TipoPermisoCreate(TipoPermisoBase):
    pass


class TipoPermiso(TipoPermisoBase):
    id: int


class PermisoBase(BaseModel):
    usuario_id: int
    tipo_permiso_id: int
    fecha_inicio: str
    fecha_fin: str
    motivo: str
    aprobado: bool = False


class PermisoCreate(PermisoBase):
    pass


class PermisoEstadoUpdate(BaseModel):
    aprobado: bool


class Permiso(PermisoBase):
    id: int
    usuario_nombre: Optional[str] = None
    tipo_permiso_nombre: Optional[str] = None


# ==========================================
# 8. HISTORIAL ACCESO
# ==========================================
class HistorialAccesoBase(BaseModel):
    usuario_id: int
    dispositivo_id: int
    fecha_hora: str
    accion: str


class HistorialAccesoCreate(HistorialAccesoBase):
    pass


class HistorialAcceso(HistorialAccesoBase):
    id: int
    usuario_nombre: Optional[str] = None
    usuario_codigo: Optional[str] = None
    dispositivo_nombre: Optional[str] = None


# ==========================================
# 9. CONFIGURACION INSTITUCION
# ==========================================
class ConfiguracionInstitucionBase(BaseModel):
    nombre: str
    hora_entrada: Optional[str] = "08:00:00"
    tolerancia_minutos: int = 10
    activa: bool = True


class ConfiguracionInstitucionCreate(ConfiguracionInstitucionBase):
    pass


class ConfiguracionInstitucionUpdate(BaseModel):
    nombre: Optional[str] = None
    hora_entrada: Optional[str] = None
    tolerancia_minutos: Optional[int] = None
    activa: Optional[bool] = None


class ConfiguracionInstitucion(ConfiguracionInstitucionBase):
    id: int


# ==========================================
# 10. AUTH, SIMULADOR Y EVALUACIÓN DE FALTAS
# ==========================================
class LoginRequest(BaseModel):
    correo: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: Usuario


class SimularAsistenciaRequest(BaseModel):
    usuario_id: Optional[int] = None
    codigo_qr: Optional[str] = None
    dispositivo_id: int = 1
    forzar_tardanza: bool = False


class EvaluarFaltasRequest(BaseModel):
    fecha: Optional[str] = None
    forzar_cierre: bool = False


class ResumenFaltasUsuario(BaseModel):
    usuario_id: int
    codigo: str
    usuario_nombre: str
    cargo_nombre: str
    total_asistencias: int
    total_faltas: int
    faltas_justificadas: int
    faltas_injustificadas: int
    total_tardanzas: int
    total_salidas_anticipadas: int
