import React, { useState, useEffect, useCallback } from 'react'
import {
  Calendar,
  FileText,
  CheckCircle2,
  AlertCircle,
  UserX,
  Clock,
  UserCheck,
  Filter,
  QrCode,
  RefreshCw,
} from 'lucide-react'
import { apiFetch } from '../lib/api'

function formatTime(val) {
  if (!val) return '—'
  const str = String(val)
  return str.includes('T') ? str.split('T')[1].slice(0, 8) : str.slice(0, 8)
}

export default function PortalTrabajadorView({ user, lastRealtimeEvent }) {
  const [asistencias, setAsistencias] = useState([])
  const [incidencias, setIncidencias] = useState([])
  const [tiposIncidencia, setTiposIncidencia] = useState([])
  const [horarios, setHorarios] = useState([])
  const [resumenPersonal, setResumenPersonal] = useState(null)

  const [filtroFecha, setFiltroFecha] = useState('')
  const [filtroTipoIncidencia, setFiltroTipoIncidencia] = useState('')
  const [soloFaltas, setSoloFaltas] = useState(false)

  const [editIncId, setEditIncId] = useState(null)
  const [justificacionTexto, setJustificacionTexto] = useState('')
  const [loading, setLoading] = useState(false)

  const cargarMisDatos = useCallback(async () => {
    if (!user?.id) return
    setLoading(true)
    try {
      const paramsAsist = new URLSearchParams()
      paramsAsist.append('usuario_id', String(user.id))
      if (filtroFecha) paramsAsist.append('fecha', filtroFecha)
      if (soloFaltas) paramsAsist.append('solo_faltas', 'true')

      const paramsInc = new URLSearchParams()
      paramsInc.append('usuario_id', String(user.id))
      if (filtroTipoIncidencia) {
        paramsInc.append('tipo_incidencia_id', filtroTipoIncidencia)
      }

      const [asistData, incData, tiposData, resumenData, horariosData] =
        await Promise.all([
          apiFetch(`/api/asistencias?${paramsAsist.toString()}`),
          apiFetch(`/api/asistencias/incidencias?${paramsInc.toString()}`),
          apiFetch('/api/asistencias/tipos-incidencia'),
          apiFetch('/api/asistencias/resumen-usuarios'),
          apiFetch(`/api/usuarios/horarios?usuario_id=${user.id}`),
        ])

      setAsistencias(asistData)
      setIncidencias(incData)
      setTiposIncidencia(tiposData)
      setHorarios(horariosData)

      const miFila = resumenData.find(
        (r) => Number(r.usuario_id) === Number(user.id)
      )
      setResumenPersonal(
        miFila || {
          total_asistencias: 0,
          total_faltas: 0,
          faltas_justificadas: 0,
          faltas_injustificadas: 0,
          total_tardanzas: 0,
          total_salidas_anticipadas: 0,
        }
      )
    } catch (err) {
      console.error('Error al cargar portal del trabajador:', err)
    } finally {
      setLoading(false)
    }
  }, [user?.id, filtroFecha, filtroTipoIncidencia, soloFaltas])

  useEffect(() => {
    cargarMisDatos()
  }, [cargarMisDatos, lastRealtimeEvent])

  const guardarJustificacion = async (incId) => {
    try {
      await apiFetch(`/api/asistencias/incidencias/${incId}/justificar`, {
        method: 'PATCH',
        body: JSON.stringify({ justificacion: justificacionTexto }),
      })
      setEditIncId(null)
      setJustificacionTexto('')
      cargarMisDatos()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Cabecera personal del colaborador */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700">
              {user.cargo_nombre || 'Colaborador'}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono bg-slate-50 text-slate-600 border border-slate-200">
              <QrCode className="w-3 h-3 text-slate-500" />
              {user.codigo_qr}
            </span>
          </div>
          <h2 className="text-base font-semibold text-slate-900">
            Mi Historial de Asistencia, Faltas e Incidencias
          </h2>
          <p className="text-xs text-slate-500">
            Bienvenido, {user.nombres} {user.apellidos} ({user.codigo}). Aquí puede consultar sus asistencias, faltas y registrar justificaciones.
          </p>
        </div>

        {/* Filtros personales */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filtroTipoIncidencia}
              onChange={(e) => setFiltroTipoIncidencia(e.target.value)}
              className="text-xs bg-transparent text-slate-800 focus:outline-none"
            >
              <option value="">Todas mis incidencias</option>
              {tiposIncidencia.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="date"
              value={filtroFecha}
              onChange={(e) => setFiltroFecha(e.target.value)}
              className="text-xs bg-transparent text-slate-800 focus:outline-none"
            />
          </div>

          {(filtroFecha || filtroTipoIncidencia || soloFaltas) && (
            <button
              onClick={() => {
                setFiltroFecha('')
                setFiltroTipoIncidencia('')
                setSoloFaltas(false)
              }}
              className="text-xs text-slate-600 hover:text-slate-900 underline cursor-pointer px-1"
            >
              Limpiar
            </button>
          )}

          <button
            onClick={cargarMisDatos}
            title="Actualizar mis registros"
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 4 Tarjetas de indicadores personales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Mis Faltas</span>
            <UserX className="w-4 h-4 text-red-600" />
          </div>
          <div className="text-2xl font-semibold text-slate-900">
            {resumenPersonal?.total_faltas ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            {resumenPersonal?.faltas_injustificadas ?? 0} sin justificar ·{' '}
            {resumenPersonal?.faltas_justificadas ?? 0} justificadas
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Mis Tardanzas</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-semibold text-slate-900">
            {resumenPersonal?.total_tardanzas ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Ingresos fuera de tolerancia
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Salidas Anticipadas</span>
            <AlertCircle className="w-4 h-4 text-slate-700" />
          </div>
          <div className="text-2xl font-semibold text-slate-900">
            {resumenPersonal?.total_salidas_anticipadas ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Antes del cierre de turno
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Mis Asistencias</span>
            <UserCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-semibold text-slate-900">
            {resumenPersonal?.total_asistencias ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Días asistidos registrados
          </p>
        </div>
      </div>

      {/* Mis Incidencias (Faltas, Tardanzas, Salidas anticipadas) */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Mis Incidencias Registradas ({incidencias.length})
            </h3>
            <p className="text-xs text-slate-500">
              Detalle de sus tardanzas, faltas y salidas anticipadas
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Fecha</th>
                <th className="py-3 px-4">Tipo de Incidencia</th>
                <th className="py-3 px-4">Descripción</th>
                <th className="py-3 px-4">Sustento / Justificación</th>
                <th className="py-3 px-4 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {incidencias.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400">
                    No registra incidencias con los filtros actuales.
                  </td>
                </tr>
              ) : (
                incidencias.map((inc) => {
                  const esFalta = String(inc.tipo_incidencia_nombre)
                    .toLowerCase()
                    .includes('falta')
                  return (
                    <tr key={inc.id} className="hover:bg-slate-50/70">
                      <td className="py-3 px-4 font-mono text-slate-700">
                        {inc.fecha_asistencia}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                            esFalta
                              ? 'bg-red-50 text-red-700 border-red-200'
                              : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}
                        >
                          <AlertCircle className="w-3 h-3" />
                          {inc.tipo_incidencia_nombre}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-600 max-w-md">
                        {inc.descripcion}
                      </td>
                      <td className="py-3 px-4 text-slate-700">
                        {editIncId === inc.id ? (
                          <input
                            type="text"
                            value={justificacionTexto}
                            onChange={(e) =>
                              setJustificacionTexto(e.target.value)
                            }
                            placeholder="Ingrese su justificación o descargo..."
                            className="w-full px-2.5 py-1 text-xs border border-slate-300 rounded-md focus:outline-none focus:border-slate-900"
                          />
                        ) : inc.justificacion ? (
                          <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            {inc.justificacion}
                          </span>
                        ) : (
                          <span className="text-slate-400">Sin justificar</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {editIncId === inc.id ? (
                          <div className="inline-flex items-center gap-2">
                            <button
                              onClick={() => guardarJustificacion(inc.id)}
                              className="px-2.5 py-1 rounded bg-slate-900 text-white text-xs font-medium cursor-pointer"
                            >
                              Guardar
                            </button>
                            <button
                              onClick={() => setEditIncId(null)}
                              className="px-2 py-1 text-slate-500 hover:text-slate-800 text-xs cursor-pointer"
                            >
                              Cancelar
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setEditIncId(inc.id)
                              setJustificacionTexto(inc.justificacion || '')
                            }}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-medium cursor-pointer"
                          >
                            <FileText className="w-3 h-3" />
                            <span>Justificar</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mi Lista de Asistencias y Faltas + Mi Horario Laboral */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Mis Registros de Asistencia y Faltas ({asistencias.length})
              </h3>
              <p className="text-xs text-slate-500">
                Historial cronológico de marcajes de entrada, salida e inasistencias
              </p>
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={soloFaltas}
                  onChange={(e) => setSoloFaltas(e.target.checked)}
                  className="rounded border-slate-300 text-slate-900 focus:ring-0"
                />
                <span>Solo faltas</span>
              </label>
              {loading && (
                <span className="text-xs text-slate-400">Cargando...</span>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Fecha</th>
                  <th className="py-3 px-4">Hora Entrada</th>
                  <th className="py-3 px-4">Hora Salida</th>
                  <th className="py-3 px-4">Estado</th>
                  <th className="py-3 px-4">Dispositivo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {asistencias.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      No tiene registros de asistencia para mostrar.
                    </td>
                  </tr>
                ) : (
                  asistencias.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/70">
                      <td className="py-3 px-4 font-mono text-slate-700">
                        {a.fecha}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-800">
                        {formatTime(a.hora_entrada)}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-800">
                        {formatTime(a.hora_salida)}
                      </td>
                      <td className="py-3 px-4">
                        {a.es_falta ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 text-[11px] font-medium">
                            Falta
                          </span>
                        ) : a.tiene_incidencia ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 text-[11px] font-medium">
                            {a.tipo_incidencia_nombre || 'Incidencia'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-medium">
                            Puntual
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-600">
                        {a.dispositivo_nombre}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Mi Horario Laboral Asignado */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden h-fit">
          <div className="px-5 py-4 border-b border-slate-200">
            <h3 className="text-sm font-semibold text-slate-900">
              Mi Horario Laboral
            </h3>
            <p className="text-xs text-slate-500">
              Turnos configurados para su usuario
            </p>
          </div>

          <div className="divide-y divide-slate-100 text-xs">
            {horarios.length === 0 ? (
              <div className="p-6 text-center text-slate-400">
                No tiene turnos asignados en HorarioLaboral.
              </div>
            ) : (
              horarios.map((h) => (
                <div
                  key={h.id}
                  className="px-5 py-3 flex items-center justify-between"
                >
                  <span className="font-medium text-slate-800">
                    {h.dia_semana}
                  </span>
                  <span className="font-mono text-slate-600">
                    {h.hora_inicio} — {h.hora_fin}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

