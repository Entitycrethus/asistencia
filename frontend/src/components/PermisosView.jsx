import React, { useState, useEffect } from 'react'
import { Plus, Check, X, FileCheck } from 'lucide-react'
import { apiFetch } from '../lib/api'

export default function PermisosView({ usuarios, onChanged }) {
  const [permisos, setPermisos] = useState([])
  const [tiposPermiso, setTiposPermiso] = useState([])
  const [mostrarForm, setMostrarForm] = useState(false)
  const [form, setForm] = useState({
    usuario_id: '',
    tipo_permiso_id: '',
    fecha_inicio: new Date().toISOString().slice(0, 10),
    fecha_fin: new Date().toISOString().slice(0, 10),
    motivo: '',
    aprobado: false,
  })

  const cargarPermisos = async () => {
    try {
      const [pData, tData] = await Promise.all([
        apiFetch('/api/permisos'),
        apiFetch('/api/permisos/tipos'),
      ])
      setPermisos(pData)
      setTiposPermiso(tData)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    cargarPermisos()
  }, [])

  const handleCrearPermiso = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('/api/permisos', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          usuario_id: Number(form.usuario_id || usuarios[0]?.id),
          tipo_permiso_id: Number(form.tipo_permiso_id || tiposPermiso[0]?.id),
        }),
      })
      setMostrarForm(false)
      setForm({ ...form, motivo: '' })
      cargarPermisos()
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  const cambiarEstado = async (id, aprobado) => {
    try {
      await apiFetch(`/api/permisos/${id}/estado`, {
        method: 'PATCH',
        body: JSON.stringify({ aprobado }),
      })
      cargarPermisos()
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-5 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Gestión de Permisos y Licencias
          </h2>
          <p className="text-xs text-slate-500">
            Aprobación y registro de ausencias justificadas del personal
          </p>
        </div>
        <button
          onClick={() => setMostrarForm(!mostrarForm)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Registrar Permiso</span>
        </button>
      </div>

      {mostrarForm && (
        <form
          onSubmit={handleCrearPermiso}
          className="bg-white border border-slate-200 rounded-xl p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Colaborador
            </label>
            <select
              value={form.usuario_id || (usuarios[0]?.id ?? '')}
              onChange={(e) => setForm({ ...form, usuario_id: e.target.value })}
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
              Tipo de Permiso
            </label>
            <select
              value={form.tipo_permiso_id || (tiposPermiso[0]?.id ?? '')}
              onChange={(e) =>
                setForm({ ...form, tipo_permiso_id: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            >
              {tiposPermiso.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Fecha Inicio
            </label>
            <input
              type="date"
              required
              value={form.fecha_inicio}
              onChange={(e) =>
                setForm({ ...form, fecha_inicio: e.target.value })
              }
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Fecha Fin
            </label>
            <input
              type="date"
              required
              value={form.fecha_fin}
              onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Motivo o Sustento
            </label>
            <input
              type="text"
              required
              placeholder="Detalle el motivo de la solicitud..."
              value={form.motivo}
              onChange={(e) => setForm({ ...form, motivo: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="w-full py-2 px-4 bg-slate-900 text-white text-xs font-medium rounded-lg cursor-pointer"
            >
              Guardar Solicitud
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Personal</th>
                <th className="py-3 px-4">Tipo de Permiso</th>
                <th className="py-3 px-4">Vigencia</th>
                <th className="py-3 px-4">Motivo</th>
                <th className="py-3 px-4">Estado</th>
                <th className="py-3 px-4 text-right">Resolución</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {permisos.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No hay permisos registrados.
                  </td>
                </tr>
              ) : (
                permisos.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/70">
                    <td className="py-3.5 px-4 font-medium text-slate-900">
                      {p.usuario_nombre}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-medium">
                        <FileCheck className="w-3 h-3" />
                        {p.tipo_permiso_nombre}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {p.fecha_inicio} al {p.fecha_fin}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 max-w-xs">
                      {p.motivo}
                    </td>
                    <td className="py-3.5 px-4">
                      {p.aprobado ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Aprobado
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-600">
                          Pendiente
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {p.aprobado ? (
                        <button
                          onClick={() => cambiarEstado(p.id, false)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs cursor-pointer"
                        >
                          <X className="w-3 h-3" />
                          <span>Revocar</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => cambiarEstado(p.id, true)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium cursor-pointer"
                        >
                          <Check className="w-3 h-3" />
                          <span>Aprobar</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

