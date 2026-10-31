import React, { useState, useEffect } from 'react'
import { UserPlus, QrCode, Clock, Plus, Trash2 } from 'lucide-react'
import { apiFetch } from '../lib/api'

export default function PersonalHorariosView({ usuarios, onChanged }) {
  const [roles, setRoles] = useState([])
  const [cargos, setCargos] = useState([])
  const [horarios, setHorarios] = useState([])
  const [mostrarFormUsuario, setMostrarFormUsuario] = useState(false)
  const [mostrarFormHorario, setMostrarFormHorario] = useState(false)

  const [nuevoUsuario, setNuevoUsuario] = useState({
    codigo: '',
    codigo_qr: '',
    nombres: '',
    apellidos: '',
    correo: '',
    password: '',
    rol_id: 3,
    cargo_id: 2,
    activo: true,
  })

  const [nuevoHorario, setNuevoHorario] = useState({
    usuario_id: '',
    dia_semana: 'Lunes',
    hora_inicio: '07:45:00',
    hora_fin: '15:30:00',
  })

  const cargarAuxiliares = async () => {
    try {
      const [rData, cData, hData] = await Promise.all([
        apiFetch('/api/usuarios/roles'),
        apiFetch('/api/usuarios/cargos'),
        apiFetch('/api/usuarios/horarios'),
      ])
      setRoles(rData)
      setCargos(cData)
      setHorarios(hData)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    cargarAuxiliares()
  }, [])

  const handleCrearUsuario = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('/api/usuarios', {
        method: 'POST',
        body: JSON.stringify({
          ...nuevoUsuario,
          rol_id: Number(nuevoUsuario.rol_id),
          cargo_id: Number(nuevoUsuario.cargo_id),
        }),
      })
      setMostrarFormUsuario(false)
      setNuevoUsuario({
        codigo: '',
        codigo_qr: '',
        nombres: '',
        apellidos: '',
        correo: '',
        password: '',
        rol_id: 3,
        cargo_id: 2,
        activo: true,
      })
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  const toggleActivo = async (u) => {
    try {
      await apiFetch(`/api/usuarios/${u.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ activo: !u.activo }),
      })
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleCrearHorario = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('/api/usuarios/horarios', {
        method: 'POST',
        body: JSON.stringify({
          ...nuevoHorario,
          usuario_id: Number(nuevoHorario.usuario_id || usuarios[0]?.id),
        }),
      })
      setMostrarFormHorario(false)
      cargarAuxiliares()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleEliminarHorario = async (id) => {
    try {
      await apiFetch(`/api/usuarios/horarios/${id}`, { method: 'DELETE' })
      cargarAuxiliares()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Cabecera Personal */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Directorio de Personal y Horarios Laborales
          </h2>
          <p className="text-xs text-slate-500">
            Gestión de usuarios (contraseñas encriptadas con Bcrypt), códigos QR y jornadas
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setMostrarFormHorario(!mostrarFormHorario)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium cursor-pointer"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Asignar Horario</span>
          </button>

          <button
            onClick={() => setMostrarFormUsuario(!mostrarFormUsuario)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium cursor-pointer"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Nuevo Usuario</span>
          </button>
        </div>
      </div>

      {/* Formulario Nuevo Usuario */}
      {mostrarFormUsuario && (
        <form
          onSubmit={handleCrearUsuario}
          className="bg-white border border-slate-200 rounded-xl p-5 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4"
        >
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Código Interno
            </label>
            <input
              type="text"
              required
              placeholder="EMP-006"
              value={nuevoUsuario.codigo}
              onChange={(e) =>
                setNuevoUsuario({
                  ...nuevoUsuario,
                  codigo: e.target.value,
                  codigo_qr: nuevoUsuario.codigo_qr || `QR-${e.target.value}`,
                })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Código QR
            </label>
            <input
              type="text"
              required
              placeholder="QR-EMP-006"
              value={nuevoUsuario.codigo_qr}
              onChange={(e) =>
                setNuevoUsuario({ ...nuevoUsuario, codigo_qr: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Nombres
            </label>
            <input
              type="text"
              required
              value={nuevoUsuario.nombres}
              onChange={(e) =>
                setNuevoUsuario({ ...nuevoUsuario, nombres: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Apellidos
            </label>
            <input
              type="text"
              required
              value={nuevoUsuario.apellidos}
              onChange={(e) =>
                setNuevoUsuario({ ...nuevoUsuario, apellidos: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Correo Electrónico
            </label>
            <input
              type="email"
              required
              value={nuevoUsuario.correo}
              onChange={(e) =>
                setNuevoUsuario({ ...nuevoUsuario, correo: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Contraseña (se encriptará con Bcrypt)
            </label>
            <input
              type="password"
              required
              minLength={4}
              value={nuevoUsuario.password}
              onChange={(e) =>
                setNuevoUsuario({ ...nuevoUsuario, password: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Rol
            </label>
            <select
              value={nuevoUsuario.rol_id}
              onChange={(e) =>
                setNuevoUsuario({ ...nuevoUsuario, rol_id: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            >
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.nombre}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Cargo
            </label>
            <select
              value={nuevoUsuario.cargo_id}
              onChange={(e) =>
                setNuevoUsuario({ ...nuevoUsuario, cargo_id: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            >
              {cargos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-3 lg:col-span-4 flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setMostrarFormUsuario(false)}
              className="px-3.5 py-2 text-xs text-slate-600 hover:text-slate-900 cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-slate-900 text-white text-xs font-medium rounded-lg cursor-pointer"
            >
              Guardar Usuario
            </button>
          </div>
        </form>
      )}

      {/* Formulario Nuevo Horario */}
      {mostrarFormHorario && (
        <form
          onSubmit={handleCrearHorario}
          className="bg-white border border-slate-200 rounded-xl p-5 grid grid-cols-1 md:grid-cols-5 gap-4"
        >
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Colaborador
            </label>
            <select
              value={nuevoHorario.usuario_id || (usuarios[0]?.id ?? '')}
              onChange={(e) =>
                setNuevoHorario({ ...nuevoHorario, usuario_id: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            >
              {usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nombres} {u.apellidos}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Día de Semana
            </label>
            <select
              value={nuevoHorario.dia_semana}
              onChange={(e) =>
                setNuevoHorario({ ...nuevoHorario, dia_semana: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            >
              {['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'].map(
                (d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                )
              )}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Hora Inicio / Fin
            </label>
            <div className="flex items-center gap-1.5">
              <input
                type="time"
                step="1"
                value={nuevoHorario.hora_inicio}
                onChange={(e) =>
                  setNuevoHorario({
                    ...nuevoHorario,
                    hora_inicio: e.target.value,
                  })
                }
                className="w-full px-2 py-2 text-xs border border-slate-200 rounded-lg"
              />
              <input
                type="time"
                step="1"
                value={nuevoHorario.hora_fin}
                onChange={(e) =>
                  setNuevoHorario({ ...nuevoHorario, hora_fin: e.target.value })
                }
                className="w-full px-2 py-2 text-xs border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              className="w-full py-2 px-4 bg-slate-900 text-white text-xs font-medium rounded-lg inline-flex items-center justify-center gap-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Agregar Turno</span>
            </button>
          </div>
        </form>
      )}

      {/* Tabla de Usuarios */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">
            Personal Registrado ({usuarios.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Código</th>
                <th className="py-3 px-4">Nombres y Apellidos</th>
                <th className="py-3 px-4">Correo</th>
                <th className="py-3 px-4">Cargo / Rol</th>
                <th className="py-3 px-4">Identificador QR</th>
                <th className="py-3 px-4 text-right">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {usuarios.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/70">
                  <td className="py-3 px-4 font-mono text-slate-600">
                    {u.codigo}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-900">
                    {u.nombres} {u.apellidos}
                  </td>
                  <td className="py-3 px-4 text-slate-600">{u.correo}</td>
                  <td className="py-3 px-4 text-slate-600">
                    <div>{u.cargo_nombre}</div>
                    <div className="text-[11px] text-slate-400">
                      {u.rol_nombre}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[11px]">
                      <QrCode className="w-3 h-3 text-slate-500" />
                      {u.codigo_qr}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => toggleActivo(u)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer ${
                        u.activo
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-100 text-slate-500 border-slate-200'
                      }`}
                    >
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tabla de Horarios Laborales */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">
            Horarios Laborales Configurados ({horarios.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Colaborador</th>
                <th className="py-3 px-4">Día de Semana</th>
                <th className="py-3 px-4">Hora de Ingreso</th>
                <th className="py-3 px-4">Hora de Salida</th>
                <th className="py-3 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {horarios.map((h) => (
                <tr key={h.id} className="hover:bg-slate-50/70">
                  <td className="py-3 px-4 font-medium text-slate-900">
                    {h.usuario_nombre}
                  </td>
                  <td className="py-3 px-4 text-slate-600">{h.dia_semana}</td>
                  <td className="py-3 px-4 font-mono text-slate-800">
                    {h.hora_inicio}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-800">
                    {h.hora_fin}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => handleEliminarHorario(h.id)}
                      className="p-1.5 text-slate-400 hover:text-red-600 transition-colors cursor-pointer"
                      title="Eliminar horario"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

