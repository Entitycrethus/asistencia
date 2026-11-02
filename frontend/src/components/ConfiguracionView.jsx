import React, { useState, useEffect } from 'react'
import { Database, Smartphone, Building2, Plus, CheckCircle2 } from 'lucide-react'
import { apiFetch } from '../lib/api'

export default function ConfiguracionView({ dispositivos, onChanged }) {
  const [institucion, setInstitucion] = useState(null)
  const [supabaseUrl, setSupabaseUrl] = useState(
    localStorage.getItem('agy_supabase_url') || ''
  )
  const [supabaseKey, setSupabaseKey] = useState(
    localStorage.getItem('agy_supabase_key') || ''
  )
  const [conectado, setConectado] = useState(false)
  const [nuevoDisp, setNuevoDisp] = useState({
    nombre: '',
    ubicacion: '',
    activo: true,
  })
  const [guardadoMsg, setGuardadoMsg] = useState('')

  const cargarConfig = async () => {
    try {
      const [instData, connData] = await Promise.all([
        apiFetch('/api/configuracion/institucion'),
        apiFetch('/api/configuracion/conexion'),
      ])
      if (instData && instData.length > 0) {
        setInstitucion(instData[0])
      }
      setConectado(connData.conectado)
      if (connData.supabase_url && !supabaseUrl) {
        setSupabaseUrl(connData.supabase_url)
      }
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    cargarConfig()
  }, [])

  const handleGuardarSupabase = async (e) => {
    e.preventDefault()
    try {
      localStorage.setItem('agy_supabase_url', supabaseUrl.trim())
      localStorage.setItem('agy_supabase_key', supabaseKey.trim())
      const res = await apiFetch('/api/configuracion/conexion', {
        method: 'POST',
        body: JSON.stringify({
          supabase_url: supabaseUrl,
          supabase_key: supabaseKey,
        }),
      })
      setConectado(res.conectado)
      setGuardadoMsg(res.mensaje)
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleGuardarInstitucion = async (e) => {
    e.preventDefault()
    if (!institucion) return
    try {
      await apiFetch(`/api/configuracion/institucion/${institucion.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          nombre: institucion.nombre,
          hora_entrada: institucion.hora_entrada,
          tolerancia_minutos: Number(institucion.tolerancia_minutos),
          activa: institucion.activa,
        }),
      })
      setGuardadoMsg('Parámetros de la institución actualizados.')
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleCrearDispositivo = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('/api/configuracion/dispositivos', {
        method: 'POST',
        body: JSON.stringify(nuevoDisp),
      })
      setNuevoDisp({ nombre: '', ubicacion: '', activo: true })
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  const toggleDispositivo = async (d) => {
    try {
      await apiFetch(`/api/configuracion/dispositivos/${d.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ activo: !d.activo }),
      })
      if (onChanged) onChanged()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="space-y-6">
      {guardadoMsg && (
        <div className="p-3.5 rounded-xl bg-slate-900 text-white text-xs flex items-center justify-between">
          <span className="inline-flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {guardadoMsg}
          </span>
          <button
            onClick={() => setGuardadoMsg('')}
            className="underline opacity-80 hover:opacity-100 cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Conexión a Supabase */}


        {/* Parámetros de ConfiguracionInstitucion */}
        <div className="w-full flex-1 bg-white border border-slate-200 rounded-xl p-6">
          <div className="flex items-center gap-2.5 mb-4">
            <Building2 className="w-4 h-4 text-slate-700" />
            <h3 className="text-sm font-semibold text-slate-900">
              Configuración de la Institución
            </h3>
          </div>

          {institucion ? (
            <form onSubmit={handleGuardarInstitucion} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Nombre de la Institución
                </label>
                <input
                  type="text"
                  value={institucion.nombre}
                  onChange={(e) =>
                    setInstitucion({ ...institucion, nombre: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Hora de Entrada Referencial
                  </label>
                  <input
                    type="time"
                    step="1"
                    value={institucion.hora_entrada || '07:45:00'}
                    onChange={(e) =>
                      setInstitucion({
                        ...institucion,
                        hora_entrada: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Tolerancia (minutos)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={60}
                    value={institucion.tolerancia_minutos}
                    onChange={(e) =>
                      setInstitucion({
                        ...institucion,
                        tolerancia_minutos: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg font-mono"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium rounded-lg cursor-pointer"
              >
                Guardar Parámetros
              </button>
            </form>
          ) : (
            <p className="text-xs text-slate-400">
              No hay registros en ConfiguracionInstitucion.
            </p>
          )}
        </div>
      </div>

      {/* Gestión de Dispositivos */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <Smartphone className="w-4 h-4 text-slate-700" />
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Puntos de Control y Dispositivos ({dispositivos.length})
              </h3>
              <p className="text-xs text-slate-500">
                Dispositivos móviles o terminales registrados en la tabla Dispositivo
              </p>
            </div>
          </div>

          <form
            onSubmit={handleCrearDispositivo}
            className="flex flex-wrap items-center gap-2"
          >
            <input
              type="text"
              required
              placeholder="Nombre del dispositivo"
              value={nuevoDisp.nombre}
              onChange={(e) =>
                setNuevoDisp({ ...nuevoDisp, nombre: e.target.value })
              }
              className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg"
            />
            <input
              type="text"
              required
              placeholder="Ubicación física"
              value={nuevoDisp.ubicacion}
              onChange={(e) =>
                setNuevoDisp({ ...nuevoDisp, ubicacion: e.target.value })
              }
              className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg"
            />
            <button
              type="submit"
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-medium cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Agregar</span>
            </button>
          </form>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">ID</th>
                <th className="py-3 px-4">Nombre del Dispositivo</th>
                <th className="py-3 px-4">Ubicación</th>
                <th className="py-3 px-4 text-right">Estado Operativo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {dispositivos.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/70">
                  <td className="py-3 px-4 font-mono text-slate-400">#{d.id}</td>
                  <td className="py-3 px-4 font-medium text-slate-900">
                    {d.nombre}
                  </td>
                  <td className="py-3 px-4 text-slate-600">{d.ubicacion}</td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => toggleDispositivo(d)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer ${d.activo
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-100 text-slate-500 border-slate-200'
                        }`}
                    >
                      {d.activo ? 'Activo' : 'Inactivo'}
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

