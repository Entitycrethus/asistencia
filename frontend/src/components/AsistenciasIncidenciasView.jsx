import React, { useState, useEffect } from 'react'
import {
  Calendar,
  FileText,
  CheckCircle2,
  AlertCircle,
  Search,
  UserX,
  Clock,
  UserCheck,
  Filter,
} from 'lucide-react'
import { apiFetch } from '../lib/api'

function formatTime(val) {
  if (!val) return '—'
  const str = String(val)
  return str.includes('T') ? str.split('T')[1].slice(0, 8) : str.slice(0, 8)
}

export default function AsistenciasIncidenciasView({ usuarios, lastRealtimeEvent }) {
  const [asistencias, setAsistencias] = useState([])
  const [incidencias, setIncidencias] = useState([])
  const [tiposIncidencia, setTiposIncidencia] = useState([])
  const [resumenUsuarios, setResumenUsuarios] = useState([])

  const [filtroFecha, setFiltroFecha] = useState('')
  const [filtroUsuario, setFiltroUsuario] = useState('')
  const [filtroTipoIncidencia, setFiltroTipoIncidencia] = useState('')
  const [soloFaltasAsist, setSoloFaltasAsist] = useState(false)

  const [editIncId, setEditIncId] = useState(null)
  const [justificacionTexto, setJustificacionTexto] = useState('')
  const [loading, setLoading] = useState(false)

  const cargarDatos = async () => {
    setLoading(true)
    try {
      const paramsAsist = new URLSearchParams()
      if (filtroFecha) paramsAsist.append('fecha', filtroFecha)
      if (filtroUsuario) paramsAsist.append('usuario_id', filtroUsuario)
      if (soloFaltasAsist) paramsAsist.append('solo_faltas', 'true')
      const queryAsist = paramsAsist.toString() ? `?${paramsAsist.toString()}` : ''

      const paramsInc = new URLSearchParams()
      if (filtroUsuario) paramsInc.append('usuario_id', filtroUsuario)
      if (filtroTipoIncidencia)
        paramsInc.append('tipo_incidencia_id', filtroTipoIncidencia)
      const queryInc = paramsInc.toString() ? `?${paramsInc.toString()}` : ''

      const [asistData, incData, tiposData, resumenData] = await Promise.all([
        apiFetch(`/api/asistencias${queryAsist}`),
        apiFetch(`/api/asistencias/incidencias${queryInc}`),
        apiFetch('/api/asistencias/tipos-incidencia'),
        apiFetch('/api/asistencias/resumen-usuarios'),
      ])
      setAsistencias(asistData)
      setIncidencias(incData)
      setTiposIncidencia(tiposData)
      setResumenUsuarios(resumenData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargarDatos()
  }, [filtroFecha, filtroUsuario, filtroTipoIncidencia, soloFaltasAsist, lastRealtimeEvent])

  const guardarJustificacion = async (incId) => {
    try {
      await apiFetch(`/api/asistencias/incidencias/${incId}/justificar`, {
        method: 'PATCH',
        body: JSON.stringify({ justificacion: justificacionTexto }),
      })
      setEditIncId(null)
      setJustificacionTexto('')
      cargarDatos()
    } catch (err) {
      alert(err.message)
    }
  }

  // Calcular totales (del usuario seleccionado o generales)
  const filasResumenActivas = filtroUsuario
    ? resumenUsuarios.filter((r) => String(r.usuario_id) === String(filtroUsuario))
    : resumenUsuarios

  const totales = filasResumenActivas.reduce(
    (acc, r) => {
      acc.asistencias += r.total_asistencias
      acc.faltas += r.total_faltas
      acc.faltasJustificadas += r.faltas_justificadas
      acc.faltasInjustificadas += r.faltas_injustificadas
      acc.tardanzas += r.total_tardanzas
      acc.salidasAnticipadas += r.total_salidas_anticipadas
      return acc
    },
    {
      asistencias: 0,
      faltas: 0,
      faltasJustificadas: 0,
      faltasInjustificadas: 0,
      tardanzas: 0,
      salidasAnticipadas: 0,
    }
  )

  const usuarioSeleccionadoObj = filtroUsuario
    ? usuarios.find((u) => String(u.id) === String(filtroUsuario))
    : null

  return (
    <div className="space-y-6">
      {/* Barra de filtros */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Control de Faltas, Asistencias e Incidencias
          </h2>
          <p className="text-xs text-slate-500">
            {usuarioSeleccionadoObj
              ? `Mostrando métricas y registros de: ${usuarioSeleccionadoObj.nombres} ${usuarioSeleccionadoObj.apellidos} (${usuarioSeleccionadoObj.codigo})`
              : 'Seleccione un colaborador para filtrar cuántas faltas, tardanzas y asistencias acumula'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Filtro por Colaborador */}
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filtroUsuario}
              onChange={(e) => setFiltroUsuario(e.target.value)}
              className="text-xs bg-transparent text-slate-800 focus:outline-none"
            >
              <option value="">Todos los colaboradores</option>
              {usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.codigo} — {u.nombres} {u.apellidos}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro por Tipo de Incidencia (Tardanza, Falta, Salida anticipada) */}
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filtroTipoIncidencia}
              onChange={(e) => setFiltroTipoIncidencia(e.target.value)}
              className="text-xs bg-transparent text-slate-800 focus:outline-none"
            >
              <option value="">Todos los tipos de incidencia</option>
              {tiposIncidencia.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro por Fecha */}
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="date"
              value={filtroFecha}
              onChange={(e) => setFiltroFecha(e.target.value)}
              className="text-xs bg-transparent text-slate-800 focus:outline-none"
            />
          </div>

          {(filtroFecha || filtroUsuario || filtroTipoIncidencia || soloFaltasAsist) && (
            <button
              onClick={() => {
                setFiltroFecha('')
                setFiltroUsuario('')
                setFiltroTipoIncidencia('')
                setSoloFaltasAsist(false)
              }}
              className="text-xs text-slate-600 hover:text-slate-900 underline cursor-pointer px-1"
            >
              Limpiar filtros
            </button>
          )}
        </div>
      </div>

      {/* Tarjetas de Resumen (globales o del usuario filtrado) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Total de Faltas</span>
            <UserX className="w-4 h-4 text-red-600" />
          </div>
          <div className="text-2xl font-semibold text-slate-900">
            {totales.faltas}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            {totales.faltasInjustificadas} sin justificar · {totales.faltasJustificadas} justificadas
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Total de Tardanzas</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-semibold text-slate-900">
            {totales.tardanzas}
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
            {totales.salidasAnticipadas}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Antes de su hora de salida
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Asistencias Efectivas</span>
            <UserCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-semibold text-slate-900">
            {totales.asistencias}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Días con marcaje de entrada
          </p>
        </div>
      </div>

      {/* Tabla Resumen de Faltas e Incidencias por Usuario */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Consolidado de Faltas e Incidencias por Usuario
            </h3>
            <p className="text-xs text-slate-500">
              Haga clic en un colaborador para filtrar sus faltas e incidencias específicas
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Código</th>
                <th className="py-3 px-4">Colaborador</th>
                <th className="py-3 px-4">Cargo</th>
                <th className="py-3 px-4 text-center">Asistencias</th>
                <th className="py-3 px-4 text-center">Tardanzas</th>
                <th className="py-3 px-4 text-center">Salidas Ant.</th>
                <th className="py-3 px-4 text-center">Faltas Totales</th>
                <th className="py-3 px-4 text-right">Filtro Rápido</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {resumenUsuarios.map((r) => {
                const seleccionado = String(filtroUsuario) === String(r.usuario_id)
                return (
                  <tr
                    key={r.usuario_id}
                    className={`transition-colors ${
                      seleccionado ? 'bg-slate-100/90' : 'hover:bg-slate-50/70'
                    }`}
                  >
                    <td className="py-3 px-4 font-mono text-slate-500">
                      {r.codigo}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-900">
                      {r.usuario_nombre}
                    </td>
                    <td className="py-3 px-4 text-slate-600">{r.cargo_nombre}</td>
                    <td className="py-3 px-4 text-center font-mono text-slate-700">
                      {r.total_asistencias}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {r.total_tardanzas > 0 ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-medium">
                          {r.total_tardanzas}
                        </span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center font-mono text-slate-600">
                      {r.total_salidas_anticipadas}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {r.total_faltas > 0 ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-semibold">
                          {r.total_faltas} falta(s)
                        </span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() =>
                          setFiltroUsuario(
                            seleccionado ? '' : String(r.usuario_id)
                          )
                        }
                        className={`px-2.5 py-1 rounded text-xs font-medium border cursor-pointer ${
                          seleccionado
                            ? 'bg-slate-900 text-white border-slate-900'
                            : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        {seleccionado ? 'Quitar filtro' : 'Ver historial'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tabla de Incidencias y Justificaciones */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Bandeja de Incidencias ({incidencias.length})
            </h3>
            <p className="text-xs text-slate-500">
              Detalle de Tardanzas, Faltas y Salidas Anticipadas con opción a justificar
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Colaborador</th>
                <th className="py-3 px-4">Fecha</th>
                <th className="py-3 px-4">Tipo</th>
                <th className="py-3 px-4">Descripción</th>
                <th className="py-3 px-4">Justificación</th>
                <th className="py-3 px-4 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {incidencias.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No existen incidencias para los filtros seleccionados.
                  </td>
                </tr>
              ) : (
                incidencias.map((inc) => {
                  const esFalta = String(inc.tipo_incidencia_nombre)
                    .toLowerCase()
                    .includes('falta')
                  return (
                    <tr key={inc.id} className="hover:bg-slate-50/70">
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-900">
                          {inc.usuario_nombre}
                        </div>
                        <div className="text-[11px] font-mono text-slate-400">
                          {inc.usuario_codigo}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600">
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
                      <td className="py-3 px-4 text-slate-600 max-w-xs">
                        {inc.descripcion}
                      </td>
                      <td className="py-3 px-4 text-slate-700">
                        {editIncId === inc.id ? (
                          <input
                            type="text"
                            value={justificacionTexto}
                            onChange={(e) => setJustificacionTexto(e.target.value)}
                            placeholder="Escriba el sustento o descargo..."
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

      {/* Historial de Asistencia Filtrado */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Listado General de Asistencias y Faltas ({asistencias.length})
            </h3>
            <p className="text-xs text-slate-500">
              Registros de la tabla Asistencia (los registros sin hora de entrada corresponden a faltas)
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={soloFaltasAsist}
                onChange={(e) => setSoloFaltasAsist(e.target.checked)}
                className="rounded border-slate-300 text-slate-900 focus:ring-0"
              />
              <span>Mostrar solo faltas</span>
            </label>
            {loading && <span className="text-xs text-slate-400">Cargando...</span>}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">ID</th>
                <th className="py-3 px-4">Colaborador</th>
                <th className="py-3 px-4">Fecha</th>
                <th className="py-3 px-4">Entrada</th>
                <th className="py-3 px-4">Salida</th>
                <th className="py-3 px-4">Estado</th>
                <th className="py-3 px-4">Dispositivo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {asistencias.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50/70">
                  <td className="py-3 px-4 font-mono text-slate-400">#{a.id}</td>
                  <td className="py-3 px-4 font-medium text-slate-900">
                    {a.usuario_nombre}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-600">{a.fecha}</td>
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
                        Asistió
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-600">
                    {a.dispositivo_nombre}
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
