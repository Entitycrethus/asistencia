import { createClient } from '@supabase/supabase-js'

const envUrl = import.meta.env.VITE_SUPABASE_URL || ''
const envKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export function getSupabaseClient() {
  const storedUrl = localStorage.getItem('agy_supabase_url') || envUrl
  const storedKey = localStorage.getItem('agy_supabase_key') || envKey

  const isConfigured =
    Boolean(storedUrl) &&
    Boolean(storedKey) &&
    !storedUrl.includes('tu-proyecto.supabase.co') &&
    !storedKey.includes('tu-anon-key')

  if (!isConfigured) {
    return null
  }

  try {
    return createClient(storedUrl, storedKey, {
      realtime: {
        params: {
          eventsPerSecond: 10,
        },
      },
    })
  } catch {
    return null
  }
}

/**
 * Conecta en tiempo real tanto al WebSocket de FastAPI (ws://127.0.0.1:8000/ws/asistencia)
 * como al canal `postgres_changes` de Supabase Realtime.
 * Así, cualquier petición desde Postman, desde el celular con Ngrok o directo en Supabase
 * actualiza la pantalla al instante sin recargar.
 */
export function subscribeToAttendanceRealtime(onRealtimeEvent, onStatusChange) {
  let isClosed = false
  let backendSocket = null
  let reconnectTimer = null

  // 1. Conexión al WebSocket directo de FastAPI (/ws/asistencia)
  const wsBase = apiUrl.replace(/^http/, 'ws')
  const connectBackendWs = () => {
    if (isClosed) return
    try {
      backendSocket = new WebSocket(`${wsBase}/ws/asistencia`)
      backendSocket.onopen = () => {
        if (onStatusChange) onStatusChange('SUBSCRIBED')
      }
      backendSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (onRealtimeEvent) onRealtimeEvent(data)
        } catch {
          if (onRealtimeEvent) onRealtimeEvent({ table: 'asistencia', eventType: 'UPDATE' })
        }
      }
      backendSocket.onclose = () => {
        if (!isClosed) {
          reconnectTimer = setTimeout(connectBackendWs, 2500)
        }
      }
    } catch {
      // ignore ws init error
    }
  }

  connectBackendWs()

  // 2. Conexión al WebSocket de Supabase Realtime (postgres_changes)
  const supabase = getSupabaseClient()
  let channel = null
  if (supabase) {
    channel = supabase
      .channel('asistencia-realtime-feed')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public' },
        (payload) => {
          if (onRealtimeEvent) {
            onRealtimeEvent(payload)
          }
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED' && onStatusChange) {
          onStatusChange('SUBSCRIBED')
        }
      })
  }

  return () => {
    isClosed = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (backendSocket) {
      try {
        backendSocket.close()
      } catch {
        // ignore
      }
    }
    if (supabase && channel) {
      supabase.removeChannel(channel)
    }
  }
}
