from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, dashboard, asistencias, permisos, usuarios, configuracion


@asynccontextmanager
async def lifespan(app: FastAPI):
    listener = None
    if settings.NGROK_AUTHTOKEN:
        try:
            import ngrok
            listener = await ngrok.forward(8000, authtoken=settings.NGROK_AUTHTOKEN)
            settings.NGROK_PUBLIC_URL = listener.url()
            print(f"\n=======================================================")
            print(f" TUNEL NGROK ACTIVO: {settings.NGROK_PUBLIC_URL}")
            print(f" ENDPOINT MOVIL QR : {settings.NGROK_PUBLIC_URL}/api/asistencias/marcar-qr")
            print(f"=======================================================\n")
        except Exception as exc:
            print(f"Aviso: No se pudo iniciar el túnel Ngrok automático: {exc}")
    yield
    if listener:
        try:
            import ngrok
            await ngrok.disconnect(listener.url())
        except Exception:
            pass


app = FastAPI(
    title="Sistema de Gestión de Asistencia - API",
    description="Backend con FastAPI, SQL puro (psycopg2) y túnel Ngrok integrado para lectura QR móvil.",
    version="1.0.0",
    lifespan=lifespan,
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
    return {
        "sistema": "Gestión de Asistencia API",
        "estado": "operativo",
        "ngrok_url": settings.NGROK_PUBLIC_URL or None,
        "endpoint_movil_qr": (
            f"{settings.NGROK_PUBLIC_URL}/api/asistencias/marcar-qr"
            if settings.NGROK_PUBLIC_URL
            else "/api/asistencias/marcar-qr"
        ),
    }
