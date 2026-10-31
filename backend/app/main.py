from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, dashboard, asistencias, permisos, usuarios, configuracion

app = FastAPI(
    title="Sistema de Gestión de Asistencia - API",
    description="Backend con FastAPI, Pydantic y cliente Supabase para el monitoreo y gestión de asistencia.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(asistencias.router)
app.include_router(permisos.router)
app.include_router(usuarios.router)
app.include_router(configuracion.router)


@app.get("/")
def root():
    return {"sistema": "Gestión de Asistencia API", "estado": "operativo"}

