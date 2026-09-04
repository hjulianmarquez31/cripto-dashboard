import asyncio
import json
import logging
from typing import List, Set
import websockets 
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Configuración básica de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(
    title="Real-Time Crypto Stream & Alert Engine",
    description="Backend en FastAPI que consume el WebSocket de Binance, procesa métricas y emite alertas en tiempo real.",
    version="1.0.0"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """Administra las conexiones WebSocket con los clientes Frontend."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("Nuevo cliente WebSocket conectado.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info("Cliente WebSocket desconectado.")

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Error enviando datos al cliente: {e}")

manager = ConnectionManager()

# Reglas de alertas configurables
ALERT_RULES = {
    "btcusdt": {"threshold_high": 100000.0, "threshold_low": 50000.0},
    "ethusdt": {"threshold_high": 4000.0, "threshold_low": 2000.0},
    "solusdt": {"threshold_high": 250.0, "threshold_low": 100.0}
}

ACTIVE_SYMBOLS: Set[str] = {"btcusdt", "ethusdt", "solusdt"}

async def binance_websocket_listener():
    """Se conecta al WebSocket oficial de Binance y retransmite eventos procesados."""
    streams = "/".join([f"{symbol}@trade" for symbol in ACTIVE_SYMBOLS])
    binance_url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    while True:
        try:
            logging.info("Iniciando conexión con el WebSocket de Binance...")
            async with websockets.connect(binance_url) as ws:
                logging.info("¡Conexión establecida exitosamente con Binance!")
                while True:
                    raw_data = await ws.recv()
                    data = json.loads(raw_data)

                    if "data" in data:
                        trade = data["data"]
                        symbol = trade["s"].lower()
                        price = float(trade["p"])
                        timestamp = trade["T"]

                        # Evaluación de alertas de precio
                        alert_msg = None
                        rules = ALERT_RULES.get(symbol)
                        if rules:
                            if price >= rules["threshold_high"]:
                                alert_msg = f"ALERTA ALTA: {symbol.upper()} superó los ${rules['threshold_high']}"
                            elif price <= rules["threshold_low"]:
                                alert_msg = f"ALERTA BAJA: {symbol.upper()} cayó por debajo de ${rules['threshold_low']}"

                        # Payload procesado para el frontend
                        payload = {
                            "symbol": symbol,
                            "price": price,
                            "timestamp": timestamp,
                            "alert": alert_msg
                        }

                        # Emitir a los clientes conectados
                        await manager.broadcast(payload)

        except Exception as e:
            logging.warning(f"Conexión con Binance interrumpida: {e}. Reconectando en 5 segundos...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Ejecuta el listener de Binance en segundo plano al arrancar FastAPI."""
    asyncio.create_task(binance_websocket_listener())

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Servidor de métricas cripto en tiempo real activo.",
        "websocket_endpoint": "/ws"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Escucha mensajes del frontend para modificar alertas dinámicamente
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "set_alert":
                    symbol = msg.get("symbol", "").lower()
                    if symbol in ALERT_RULES:
                        if "high" in msg:
                            ALERT_RULES[symbol]["threshold_high"] = float(msg["high"])
                        if "low" in msg:
                            ALERT_RULES[symbol]["threshold_low"] = float(msg["low"])
                        logging.info(f"Nuevos umbrales para {symbol}: {ALERT_RULES[symbol]}")
            except Exception as err:
                logging.error(f"Error procesando comando del cliente: {err}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)