# Sistema de Gestión de Asistencia (FastAPI + React + Supabase)

Panel administrativo y de monitoreo en tiempo real para el control de asistencia institucional, estructurado según el modelo entidad-relación original.

## Estructura del Proyecto

- `backend/`: API REST con **FastAPI**, validación con modelos **Pydantic (`BaseModel`)**, encriptación de contraseñas con **Bcrypt**, sesiones **JWT** y consultas mediante el cliente oficial **`supabase-py`** (`supabase.table(...).select(...).execute()`).
- `frontend/`: Aplicación web en **React + Vite + Tailwind CSS** de estética minimalista (sin emojis, iconografía vectorial con `lucide-react`) y suscripción WebSocket en vivo con **`@supabase/supabase-js` (Supabase Realtime)**.

---

## Cómo conectar tus credenciales de Supabase

Tienes dos formas de vincular tu base de datos de Supabase:

1. **Desde los archivos `.env`:**
   - En `backend/.env`:
     ```env
     SUPABASE_URL=https://tu-proyecto.supabase.co
     SUPABASE_KEY=tu-anon-o-service-role-key
     ```
   - En `frontend/.env`:
     ```env
     VITE_API_URL=http://127.0.0.1:8000
     VITE_SUPABASE_URL=https://tu-proyecto.supabase.co
     VITE_SUPABASE_ANON_KEY=tu-anon-key
     ```
2. **Directamente desde la interfaz web:**
   - En la pestaña **Configuración** del Dashboard puedes pegar tu `SUPABASE_URL` y `SUPABASE_KEY` para vincular tanto el backend como el WebSocket en vivo sin reiniciar el servidor.

---

## Ejecución del Proyecto

### 1. Iniciar el Backend (FastAPI)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python -m pip install -r requirements.txt
.\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Documentación interactiva disponible en: `http://127.0.0.1:8000/docs`

### 2. Iniciar el Frontend (React)

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Panel disponible en: `http://localhost:5173`

