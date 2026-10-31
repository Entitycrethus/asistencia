from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.database import fetch_all, fetch_one, execute_returning, execute_commit
from app.schemas import (
    Usuario,
    UsuarioCreate,
    UsuarioUpdate,
    Rol,
    RolCreate,
    Cargo,
    CargoCreate,
    HorarioLaboral,
    HorarioLaboralCreate,
)
from app.security import hash_password

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios, Roles, Cargos y Horarios"])


@router.get("", response_model=List[Usuario])
def listar_usuarios():
    sql = """
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
        ORDER BY u.id ASC;
    """
    rows = fetch_all(sql)
    return [Usuario(**r) for r in rows]


@router.post("", response_model=Usuario)
def crear_usuario(payload: UsuarioCreate):
    hashed_pw = hash_password(payload.password)
    sql = """
        INSERT INTO public.usuario (
            codigo, codigo_qr, nombres, apellidos, correo, password, activo, rol_id, cargo_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, codigo, codigo_qr, nombres, apellidos, correo, activo, rol_id, cargo_id;
    """
    created = execute_returning(
        sql,
        (
            payload.codigo,
            payload.codigo_qr,
            payload.nombres,
            payload.apellidos,
            payload.correo,
            hashed_pw,
            payload.activo,
            payload.rol_id,
            payload.cargo_id,
        ),
    )
    if not created:
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario.")
    return Usuario(**created)


@router.patch("/{usuario_id}", response_model=Usuario)
def actualizar_usuario(usuario_id: int, payload: UsuarioUpdate):
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "password" in update_data and update_data["password"]:
        update_data["password"] = hash_password(update_data["password"])
    else:
        update_data.pop("password", None)

    if not update_data:
        existing = fetch_one(
            "SELECT id, codigo, codigo_qr, nombres, apellidos, correo, activo, rol_id, cargo_id FROM public.usuario WHERE id = %s;",
            (usuario_id,),
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        return Usuario(**existing)

    set_clauses = [f"{col} = %s" for col in update_data.keys()]
    values = list(update_data.values()) + [usuario_id]

    sql = f"""
        UPDATE public.usuario
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING id, codigo, codigo_qr, nombres, apellidos, correo, activo, rol_id, cargo_id;
    """
    updated = execute_returning(sql, tuple(values))
    if not updated:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return Usuario(**updated)


# ==========================================
# ROLES Y CARGOS (SQL PURO)
# ==========================================
@router.get("/roles", response_model=List[Rol])
def listar_roles():
    rows = fetch_all("SELECT id, nombre FROM public.rol ORDER BY id ASC;")
    return [Rol(**r) for r in rows]


@router.post("/roles", response_model=Rol)
def crear_rol(payload: RolCreate):
    row = execute_returning(
        "INSERT INTO public.rol (nombre) VALUES (%s) RETURNING id, nombre;",
        (payload.nombre,),
    )
    return Rol(**row)


@router.get("/cargos", response_model=List[Cargo])
def listar_cargos():
    rows = fetch_all("SELECT id, nombre FROM public.cargo ORDER BY id ASC;")
    return [Cargo(**r) for r in rows]


@router.post("/cargos", response_model=Cargo)
def crear_cargo(payload: CargoCreate):
    row = execute_returning(
        "INSERT INTO public.cargo (nombre) VALUES (%s) RETURNING id, nombre;",
        (payload.nombre,),
    )
    return Cargo(**row)


# ==========================================
# HORARIOS LABORALES (INNER JOIN CON USUARIO)
# ==========================================
@router.get("/horarios", response_model=List[HorarioLaboral])
def listar_horarios(usuario_id: Optional[int] = None):
    if usuario_id is not None:
        sql = """
            SELECT
                hl.id,
                hl.usuario_id,
                hl.dia_semana,
                hl.hora_inicio::TEXT AS hora_inicio,
                hl.hora_fin::TEXT AS hora_fin,
                (u.nombres || ' ' || u.apellidos) AS usuario_nombre
            FROM public.horario_laboral hl
            INNER JOIN public.usuario u ON u.id = hl.usuario_id
            WHERE hl.usuario_id = %s
            ORDER BY hl.id ASC;
        """
        rows = fetch_all(sql, (usuario_id,))
    else:
        sql = """
            SELECT
                hl.id,
                hl.usuario_id,
                hl.dia_semana,
                hl.hora_inicio::TEXT AS hora_inicio,
                hl.hora_fin::TEXT AS hora_fin,
                (u.nombres || ' ' || u.apellidos) AS usuario_nombre
            FROM public.horario_laboral hl
            INNER JOIN public.usuario u ON u.id = hl.usuario_id
            ORDER BY hl.usuario_id ASC, hl.id ASC;
        """
        rows = fetch_all(sql)

    return [HorarioLaboral(**r) for r in rows]


@router.post("/horarios", response_model=HorarioLaboral)
def crear_horario(payload: HorarioLaboralCreate):
    sql = """
        INSERT INTO public.horario_laboral (usuario_id, dia_semana, hora_inicio, hora_fin)
        VALUES (%s, %s, %s, %s)
        RETURNING id, usuario_id, dia_semana, hora_inicio::TEXT AS hora_inicio, hora_fin::TEXT AS hora_fin;
    """
    row = execute_returning(
        sql,
        (payload.usuario_id, payload.dia_semana, payload.hora_inicio, payload.hora_fin),
    )
    if not row:
        raise HTTPException(status_code=400, detail="No se pudo registrar el horario.")
    return HorarioLaboral(**row)


@router.delete("/horarios/{horario_id}")
def eliminar_horario(horario_id: int):
    execute_commit("DELETE FROM public.horario_laboral WHERE id = %s;", (horario_id,))
    return {"ok": True}
