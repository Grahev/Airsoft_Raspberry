import os, time, asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv

from db import init_db, upsert_target, set_target_active, list_targets, update_target_led,                create_player, list_players, delete_player, create_game, end_game, current_game,                record_hit, scores_by_target, scores_by_player
from mqtt_bridge import MQTTBridge

load_dotenv()

# Now read environment variables
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DB_PATH = os.getenv("DB_PATH", "airsoft.db")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def on_startup():
    init_db()
    global mqttb
    mqttb = MQTTBridge(on_hit=handle_hit, on_announce=handle_announce)
    mqttb.start()

@app.on_event("shutdown")
async def on_shutdown():
    mqttb.stop()

class LEDPayload(BaseModel):
    color: str
    time_ms: int

class GameStart(BaseModel):
    mode: str
    params: Dict[str, Any] = {}
    player_ids: List[int] = []

class TargetSelectPayload(BaseModel):
    system_id: str
    target_id: str
    active: bool

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse("static/index.html")

@app.get("/api/targets")
def api_targets():
    return {"targets": list_targets()}

@app.post("/api/targets/select")
def api_target_select(p: TargetSelectPayload):
    set_target_active(p.system_id, p.target_id, 1 if p.active else 0)
    return {"ok": True}

@app.post("/api/targets/{system_id}/{target_id}/led")
def api_target_led(system_id: str, target_id: str, payload: LEDPayload):
    update_target_led(system_id, target_id, payload.color, payload.time_ms)
    mqttb.send_led_cmd(system_id, target_id, payload.color, payload.time_ms)
    return {"ok": True}

@app.get("/api/players")
def api_players():
    return {"players": list_players()}

class PlayerPayload(BaseModel):
    name: str

@app.post("/api/players")
def api_add_player(p: PlayerPayload):
    create_player(p.name)
    return {"players": list_players()}

@app.delete("/api/players/{pid}")
def api_del_player(pid: int):
    delete_player(pid)
    return {"players": list_players()}

@app.get("/api/scores/targets")
def api_scores_targets():
    return {"scores": scores_by_target()}

@app.get("/api/scores/players")
def api_scores_players():
    return {"scores": scores_by_player()}

@app.post("/api/games/start")
def api_games_start(p: GameStart):
    gid = create_game(p.mode, p.params, p.player_ids)
    return {"game_id": gid, "game": current_game()}

@app.post("/api/games/stop")
def api_games_stop():
    g = current_game()
    if g:
        end_game(g["id"])
    return {"game": current_game()}

clients: list[WebSocket] = []

async def ws_broadcast(msg: dict):
    dead = []
    for ws in clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for d in dead:
        try:
            clients.remove(d)
        except ValueError:
            pass

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    await ws.send_json({
        "type": "snapshot",
        "targets": list_targets(),
        "players": list_players(),
        "scores_targets": scores_by_target(),
        "scores_players": scores_by_player(),
        "game": current_game()
    })
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in clients:
            clients.remove(ws)

def handle_announce(system_id: str, target_id: str):
    upsert_target(system_id, target_id, name=f"{system_id}/{target_id}", seen_ts=time.time())
    asyncio.run(ws_broadcast({"type": "announce", "targets": list_targets()}))

def handle_hit(system_id: str, target_id: str, amp: int | None):
    record_hit(system_id, target_id, amp, player_id=None)
    upsert_target(system_id, target_id, seen_ts=time.time())
    asyncio.run(ws_broadcast({
        "type": "hit",
        "system_id": system_id,
        "target_id": target_id,
        "scores_targets": scores_by_target(),
        "scores_players": scores_by_player()
    }))
