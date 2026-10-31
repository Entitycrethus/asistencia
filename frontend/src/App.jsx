import React, { useState, useEffect, useCallback } from 'react'
import {
  Activity,
  ClipboardList,
  FileCheck2,
  Users,
  Settings,
  LogOut,
  ShieldCheck,
  Database,
} from 'lucide-react'
import { apiFetch } from './lib/api'
import { subscribeToAttendanceRealtime, getSupabaseClient } from './lib/supabase'
import LoginView from './components/LoginView'
import MonitorView from './components/MonitorView'
import AsistenciasIncidenciasView from './components/AsistenciasIncidenciasView'
import PermisosView from './components/PermisosView'
import PersonalHorariosView from './components/PersonalHorariosView'
import ConfiguracionView from './components/ConfiguracionView'

const TABS = [
  { id: 'monitor', label: 'Monitor en Vivo', icon: Activity },
  { id: 'asistencias', label: 'Asistencias e Incidencias', icon: ClipboardList },
  { id: 'permisos', label: 'Permisos', icon: FileCheck2 },
  { id: 'personal', label: 'Personal y Horarios', icon: Users },
  { id: 'configuracion', label: 'Configuración', icon: Settings },
]

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('asistencia_user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })

  const [activeTab, setActiveTab] = useState('monitor')
  const [resumen, setResumen] = useState(null)
  const [usuarios, setUsuarios] = useState([])
  const [dispositivos, setDispositivos] = useState([])
  const [realtimeStatus, setRealtimeStatus] = useState('IDLE')
  const [lastRealtimeEvent, setLastRealtimeEvent] = useState(null)

  const cargarTodo = useCallback(async () => {
    if (!user) return
    try {
      const [resDashboard, resUsuarios, resDispositivos] = await Promise.all([
        apiFetch('/api/dashboard/resumen'),
        apiFetch('/api/usuarios'),
        apiFetch('/api/configuracion/dispositivos'),
      ])
      setResumen(resDashboard)
      setUsuarios(resUsuarios)
      setDispositivos(resDispositivos)
    } catch (err) {
      console.error('Error al cargar datos del dashboard:', err)
    }
  }, [user])

  useEffect(() => {
    cargarTodo()
  }, [cargarTodo])

  // Suscripción al WebSocket de Supabase Realtime
  useEffect(() => {
    if (!user) return
    const sb = getSupabaseClient()
    if (sb) {
      setRealtimeStatus('SUBSCRIBED')
    } else {
      setRealtimeStatus('LOCAL')
    }

    const unsubscribe = subscribeToAttendanceRealtime((payload) => {
      const timeStr = new Date().toLocaleTimeString()
      setLastRealtimeEvent(`${payload.table || 'tabla'} (${payload.eventType}) ${timeStr}`)
      cargarTodo()
    })

    return () => {
      unsubscribe()
    }
  }, [user, cargarTodo])

  const handleLogout = () => {
    localStorage.removeItem('asistencia_jwt_token')
    localStorage.removeItem('asistencia_user')
    setUser(null)
  }

  if (!user) {
    return <LoginView onLoginSuccess={(u) => setUser(u)} />
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Barra de navegación minimalista */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <span className="text-sm font-semibold tracking-tight text-slate-900 block leading-none">
                  Control de Asistencia
                </span>
                <span className="text-[11px] text-slate-400">
                  Dashboard Administrativo
                </span>
              </div>
            </div>

            <nav className="hidden md:flex items-center gap-1">
              {TABS.map((tab) => {
                const Icon = tab.icon
                const active = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                      active
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                )
              })}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab('configuracion')}
              className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer ${
                resumen?.supabase_conectado
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
              title="Estado de conexión con Supabase"
            >
              <Database className="w-3 h-3" />
              <span>
                {resumen?.supabase_conectado ? 'Supabase Conectado' : 'Modo Demo Local'}
              </span>
            </button>

            <div className="text-right hidden sm:block">
              <div className="text-xs font-medium text-slate-900">
                {user.nombres} {user.apellidos}
              </div>
              <div className="text-[11px] text-slate-400">
                {user.rol_nombre || 'Administrador'}
              </div>
            </div>

            <button
              onClick={handleLogout}
              title="Cerrar sesión"
              className="p-2 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Navegación móvil */}
        <div className="md:hidden border-t border-slate-100 px-4 py-2 flex items-center gap-1 overflow-x-auto">
          {TABS.map((tab) => {
            const Icon = tab.icon
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium shrink-0 ${
                  active
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
      </header>

      {/* Contenido principal */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'monitor' && (
          <MonitorView
            resumen={resumen}
            usuarios={usuarios}
            dispositivos={dispositivos}
            onRefresh={cargarTodo}
            realtimeStatus={realtimeStatus}
            lastRealtimeEvent={lastRealtimeEvent}
          />
        )}

        {activeTab === 'asistencias' && (
          <AsistenciasIncidenciasView usuarios={usuarios} />
        )}

        {activeTab === 'permisos' && (
          <PermisosView usuarios={usuarios} onChanged={cargarTodo} />
        )}

        {activeTab === 'personal' && (
          <PersonalHorariosView usuarios={usuarios} onChanged={cargarTodo} />
        )}

        {activeTab === 'configuracion' && (
          <ConfiguracionView
            dispositivos={dispositivos}
            onChanged={cargarTodo}
          />
        )}
      </main>
    </div>
  )
}

