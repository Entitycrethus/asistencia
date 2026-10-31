const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('asistencia_jwt_token')
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorDetail = 'Error en la solicitud al servidor.'
    try {
      const errData = await response.json()
      errorDetail = errData.detail || errorDetail
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail)
  }

  return response.json()
}

