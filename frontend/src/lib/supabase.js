import { createClient } from '@supabase/supabase-js'

const envUrl = import.meta.env.VITE_SUPABASE_URL || ''
const envKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

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
 * Suscribe un callback al WebSocket de Supabase Realtime para escuchar
 * cambios en tiempo real (INSERT, UPDATE, DELETE) en las tablas del esquema público.
 */
export function subscribeToAttendanceRealtime(onRealtimeEvent) {
  const supabase = getSupabaseClient()
  if (!supabase) {
    return () => {}
  }

  const channel = supabase
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
    .subscribe()

  return () => {
    supabase.removeChannel(channel)
  }
}

