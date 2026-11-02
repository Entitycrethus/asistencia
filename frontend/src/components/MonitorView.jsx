import React, { useState } from 'react'
import {
  Users,
  UserCheck,
  AlertTriangle,
  FileCheck,
  Play,
  Radio,
  Clock,
  ArrowUpRight,
  ArrowDownLeft,
  Smartphone,
  RefreshCw,
  UserX,
} from 'lucide-react'
import { apiFetch } from '../lib/api'

function formatHour(val) {
  if (!val) return '—'
  const str = String(val)
  if (str.includes('T')) {
    return str.split('T')[1].slice(0, 8)
  }
  return str.slice(0, 8)
}

export default function MonitorView({
  resumen,
  usuarios,
  dispositivos,
  onRefresh,
  realtimeStatus,
  lastRealtimeEvent,
}) {
  const [simUserId, setSimUserId] = useState('')
  const [simDispositivoId, setSimDispositivoId] = useState(1)
  const [forzarTardanza, setForzarTardanza] = useState(false)
  const [simulando, setSimulando] = useState(false)
  const [evaluandoFaltas, setEvaluandoFaltas] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const metricas = resumen?.metricas || {
    total_personal: 0,
    presentes_hoy: 0,
    faltas_hoy: 0,
    pendientes_ingreso: 0,
    salidas_registradas: 0,
    incidencias_hoy: 0,
    permisos_hoy: 0,
    dispositivos_activos: 0,
    total_dispositivos: 0,
  }

  const asistenciasHoy = resumen?.asistencias_hoy || []
  const historialReciente = resumen?.historial_reciente || []
  const flujoHorario = resumen?.flujo_horario || []
  const maxFlujo = Math.max(...flujoHorario.map((f) => f.marcajes), 1)

  const handleSimularMarcaje = async (e) => {
    e.preventDefault()
    const targetUserId = simUserId ? Number(simUserId) : usuarios[0]?.id
    if (!targetUserId) return

    setSimulando(true)
    setFeedback(null)
    try {
      const resp = await apiFetch('/api/dashboard/simular-asistencia', {
        method: 'POST',
        body: JSON.stringify({
          usuario_id: targetUserId,
          dispositivo_id: Number(simDispositivoId) || 1,
          forzar_tardanza: forzarTardanza,
        }),
      })
      setFeedback({
        type: 'success',
        text: resp.mensaje,
      })
      onRefresh()
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err.message,
      })
    } finally {
      setSimulando(false)
    }
  }

  const handleEvaluarFaltas = async () => {
    setEvaluandoFaltas(true)
    setFeedback(null)
    try {
      const resp = await apiFetch('/api/dashboard/evaluar-faltas', {
        method: 'POST',
        body: JSON.stringify({
          fecha: resumen?.fecha || null,
          forzar_cierre: true,
        }),
      })
      setFeedback({
        type: 'success',
        text: resp.mensaje,
      })
      onRefresh()
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err.message,
      })
    } finally {
      setEvaluandoFaltas(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Barra superior de estado en tiempo real y simulador provisional */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Radio className="w-3 h-3" />
              {realtimeStatus === 'SUBSCRIBED'
                ? 'Supabase Realtime Activo'
                : 'Monitoreo Activo'}
            </span>
            <span className="text-xs text-slate-400">
              Fecha: {resumen?.fecha || 'Hoy'}
            </span>
            {lastRealtimeEvent && (
              <span className="text-xs text-slate-500 font-mono">
                Último evento WS: {lastRealtimeEvent}
              </span>
            )}
          </div>
          <h2 className="text-base font-semibold text-slate-900">
            Flujo de Asistencia en Tiempo Real
          </h2>
          <p className="text-xs text-slate-500">
            Las faltas se marcan automáticamente al superarse la hora de salida del horario laboral de cada colaborador.
          </p>
        </div>

        {/* Simulador provisional de marcaje y cierre de faltas */}
        <form
          onSubmit={handleSimularMarcaje}
          className="flex flex-wrap items-center gap-2 bg-slate-50 p-3 rounded-lg border border-slate-200"
        >
          <span className="text-xs font-medium text-slate-600 mr-1">
            Simulador:
          </span>

          <select
            value={simUserId || (usuarios[0]?.id ?? '')}
            onChange={(e) => setSimUserId(e.target.value)}
            className="text-xs bg-white border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-800 focus:outline-none focus:border-slate-900"
          >
            {usuarios.map((u) => (
              <option key={u.id} value={u.id}>
                {u.codigo} — {u.nombres} {u.apellidos}
              </option>
            ))}
          </select>

          <select
            value={simDispositivoId}
            onChange={(e) => setSimDispositivoId(e.target.value)}
            className="text-xs bg-white border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-800 focus:outline-none focus:border-slate-900"
          >
            {dispositivos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nombre}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-1.5 text-xs text-slate-600 px-1 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={forzarTardanza}
              onChange={(e) => setForzarTardanza(e.target.checked)}
              className="rounded border-slate-300 text-slate-900 focus:ring-0"
            />
            <span>Tardanza</span>
          </label>

          <button
            type="submit"
            disabled={simulando || usuarios.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-900 hover:bg-slate-800 text-white disabled:opacity-50 transition-colors cursor-pointer"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{simulando ? 'Procesando...' : 'Simular Asistencia'}</span>
          </button>

          <button
            type="button"
            onClick={handleEvaluarFaltas}
            disabled={evaluandoFaltas}
            title="Evalúa y marca como falta a quienes no registraron asistencia al cierre de su horario"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 disabled:opacity-50 transition-colors cursor-pointer"
          >
            <UserX className="w-3.5 h-3.5 text-red-600" />
            <span>{evaluandoFaltas ? 'Evaluando...' : 'Evaluar Faltas'}</span>
          </button>

          <button
            type="button"
            onClick={onRefresh}
            title="Actualizar datos"
            className="p-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>

      {feedback && (
        <div
          className={`px-4 py-2.5 rounded-lg border text-xs flex items-center justify-between ${
            feedback.type === 'error'
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'bg-slate-900 border-slate-900 text-white'
          }`}
        >
          <span>{feedback.text}</span>
          <button
            onClick={() => setFeedback(null)}
            className="text-xs underline opacity-80 hover:opacity-100 cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Tarjetas de métricas principales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-medium">Presentes Hoy</span>
            <UserCheck className="w-4 h-4 text-slate-700" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-slate-900">
              {metricas.presentes_hoy}
            </span>
            <span className="text-xs text-slate-400">
              / {metricas.total_personal} activos
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {metricas.salidas_registradas} salidas completadas hoy
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-medium">Faltas del Día</span>
            <UserX className="w-4 h-4 text-red-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-slate-900">
              {metricas.faltas_hoy ?? 0}
            </span>
            <span className="text-xs text-slate-400">ausencias</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {metricas.pendientes_ingreso} aún en horario de ingreso
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-medium">Incidencias Hoy</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-slate-900">
              {metricas.incidencias_hoy}
            </span>
            <span className="text-xs text-slate-400">registradas</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Tardanzas, faltas o salidas anticipadas
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-medium">Permisos y Dispositivos</span>
            <FileCheck className="w-4 h-4 text-slate-700" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-slate-900">
              {metricas.permisos_hoy}
            </span>
            <span className="text-xs text-slate-400">permisos vigentes</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {metricas.dispositivos_activos} de {metricas.total_dispositivos} lectores activos
          </p>
        </div>
      </div>

      {/* Gráfica de flujo horario + Historial de Acceso en vivo */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tabla principal de Asistencias de Hoy (2 columnas) */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Registros de Asistencia del Día
              </h3>
              <p className="text-xs text-slate-500">
                Incluye ingresos, salidas y faltas generadas al cierre del horario laboral
              </p>
            </div>
            <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md">
              {asistenciasHoy.length} registros
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Personal</th>
                  <th className="py-3 px-4">Cargo</th>
                  <th className="py-3 px-4">Dispositivo</th>
                  <th className="py-3 px-4">Hora Entrada</th>
                  <th className="py-3 px-4">Hora Salida</th>
                  <th className="py-3 px-4">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {asistenciasHoy.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-slate-400">
                      Aún no se registran asistencias en la fecha seleccionada.
                    </td>
                  </tr>
                ) : (
                  asistenciasHoy.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-900">
                          {a.usuario_nombre}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {a.usuario_codigo}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-600">{a.cargo_nombre}</td>
                      <td className="py-3 px-4 text-slate-600">
                        <span className="inline-flex items-center gap-1 text-slate-600">
                          <Smartphone className="w-3.5 h-3.5 text-slate-400" />
                          {a.dispositivo_nombre}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-800">
                        {formatHour(a.hora_entrada)}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-800">
                        {formatHour(a.hora_salida)}
                      </td>
                      <td className="py-3 px-4">
                        {a.es_falta ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-red-50 text-red-700 border border-red-200">
                            Falta (Sin Marcaje)
                          </span>
                        ) : a.tiene_incidencia ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                            {a.tipo_incidencia_nombre || 'Incidencia'}
                          </span>
                        ) : a.hora_salida ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700">
                            Jornada Completa
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Puntual / En Curso
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          
        </div>

        {/* Feed lateral en vivo: HistorialAcceso */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Historial de Acceso en Vivo
              </h3>
              <p className="text-xs text-slate-500">
                Eventos de lectura QR (Entrada / Salida)
              </p>
            </div>
            <Clock className="w-4 h-4 text-slate-400" />
          </div>

          <div className="divide-y divide-slate-100 overflow-y-auto max-h-[420px]">
            {historialReciente.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                Sin lecturas recientes en HistorialAcceso.
              </div>
            ) : (
              historialReciente.map((h) => {
                const esEntrada = String(h.accion).toUpperCase().includes('ENTRADA')
                return (
                  <div
                    key={h.id}
                    className="px-5 py-3.5 flex items-start justify-between gap-3 hover:bg-slate-50/70 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`mt-0.5 w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${
                          esEntrada
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                            : 'bg-slate-100 border-slate-200 text-slate-700'
                        }`}
                      >
                        {esEntrada ? (
                          <ArrowDownLeft className="w-3.5 h-3.5" />
                        ) : (
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        )}
                      </div>
                      <div>
                        <div className="text-xs font-medium text-slate-900">
                          {h.usuario_nombre}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {h.dispositivo_nombre}
                        </div>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span
                        className={`inline-block text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                          esEntrada
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {h.accion}
                      </span>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                        {formatHour(h.fecha_hora)}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
