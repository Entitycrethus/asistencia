import asyncio
from datetime import datetime
from typing import List, Dict, Any
from fastapi import WebSocket


class ConnectionManager:
    """
    Gestiona las conexiones WebSocket activas de los clientes en React
    y transmite en tiempo real cada cambio (INSERT / UPDATE / DELETE) ocurrido en la BD.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    def notify_from_sync(self, event_type: str = "DB_CHANGE", table: str = "asistencia"):
        """
        Permite que las funciones síncronas de SQL (psycopg2) disparen un evento
        WebSocket inmediato a todos los navegadores conectados cuando entra una petición
        desde Postman o desde la App Móvil (Ngrok).
        """
        payload = {
            "eventType": event_type,
            "table": table,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)


ws_manager = ConnectionManager()

