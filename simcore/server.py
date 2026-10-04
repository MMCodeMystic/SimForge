"""FastAPI-App Phase 2: Keyframes, Checksummen (1 Hz, AOI), Events.

Architektur:
  - Tick-Thread simuliert (mit _sim_lock).
  - WebSocket-Handler: Join-Burst (alle AOI-Keyframes), dann
    Checksum-Sender-Task (alle CHECKSUM_EVERY Ticks) + Command-Empfang.
  - Drift-Healing ist CLIENT-GETRIEBEN: Client vergleicht Hashes und
    fordert Keyframes an. Der Server pushed keine Rotation mehr.
"""
from __future__ import annotations
import asyncio
import struct
import threading
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import protocol
from .chunks import CHUNK, chunk_bytes, chunk_hashes, quantize
from .fixedpoint import FIELD_MAX, to_fixed
from .module_base import World
from .registry import ModuleRegistry
from .tick import TickStats, run_loop, TICK_HZ

CORE_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parent.parent
CHECKSUM_EVERY = 30        # Ticks zwischen Checksum-Runden (30 Hz -> 1 s)
FOOD_AMOUNT = to_fixed(400)

app = FastAPI(title="SimForge")

registry = ModuleRegistry(ROOT / "modules", CORE_VERSION)
registry.discover()

stats = TickStats()
_loaded: dict = {}
_world: World | None = None
_loop_thread: threading.Thread | None = None
_loop_on = threading.Event()
_sim_lock = threading.Lock()
_conns: set["ClientConn"] = set()

class ClientConn:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.aoi = (0, 0, 255, 255)  # x0, y0, x1, y1 (Zell-Koordinaten)

    def chunks_in_aoi(self, size: int) -> list[tuple[int, int]]:
        n = size // CHUNK
        x0, y0, x1, y1 = self.aoi
        cx0 = max(0, x0 // CHUNK); cx1 = min(n - 1, x1 // CHUNK)
        cy0 = max(0, y0 // CHUNK); cy1 = min(n - 1, y1 // CHUNK)
        return [(cx, cy) for cy in range(cy0, cy1 + 1)
                        for cx in range(cx0, cx1 + 1)]

def _make_world() -> World:
    import numpy as np
    w = World(size=256)
    w.fields["pheromone"] = np.zeros((w.size, w.size), dtype=np.int64)
    return w

def _snapshot() -> tuple:
    """Konsistenter Lesestand des Feldes (quantisiert + Chunk-Hashes)."""
    with _sim_lock:
        q = quantize(_world.fields["pheromone"])
        h = chunk_hashes(q, _world.size)
        return q, h

def _apply_food_spike(x: int, y: int) -> None:
    """5x5-Diamant-Spike. MUSS bitidentisch im Client nachgebaut werden
    (siehe index.html applyFoodSpike) – gleiche Formel, gleiche Rundung."""
    field = _world.fields["pheromone"]
    n = field.shape[0]
    with _sim_lock:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                w = 3 - (abs(dx) + abs(dy))
                if w <= 0:
                    continue
                yy, xx = y + dy, x + dx
                if 0 <= yy < n and 0 <= xx < n:
                    v = int(field[yy, xx]) + FOOD_AMOUNT * w // 3
                    field[yy, xx] = min(v, int(FIELD_MAX))

def _sim_step(tick: int, dt: int) -> None:
    with _sim_lock:
        for mod in _loaded.values():
            mod.step(tick, dt, _world)

@app.on_event("startup")
async def _startup() -> None:
    global _world, _loop_thread
    _world = _make_world()
    for mid in registry.manifests:
        mod = registry.load(mid)
        mod.setup(_world)
        _loaded[mid] = mod
    _loop_on.set()
    _loop_thread = threading.Thread(
        target=run_loop, args=(_sim_step, stats, _loop_on.is_set), daemon=True)
    _loop_thread.start()

@app.get("/api/modules")
async def list_modules():
    return {"core": CORE_VERSION, "tick_hz": TICK_HZ,
            "modules": [{"id": m.id, "name": m.name, "version": m.version}
                        for m in registry.manifests.values()]}

@app.get("/api/stats")
async def get_stats():
    return {"tick": stats.tick, "last_tick_ms": round(stats.last_tick_ms, 3),
            "max_tick_ms": round(stats.max_tick_ms, 3)}

@app.websocket("/ws/sim")
async def ws_sim(ws: WebSocket) -> None:
    await ws.accept()
    size = _world.size
    conn = ClientConn(ws)
    _conns.add(conn)
    sender: asyncio.Task | None = None
    try:
        # --- Join-Burst: alle AOI-Keyframes, Client hat sofort ein Bild ---
        q, _ = _snapshot()
        for cx, cy in conn.chunks_in_aoi(size):
            data = protocol.pack_keyframe(cx, cy, chunk_bytes(q, cx, cy))
            await ws.send_bytes(protocol.Frame(
                protocol.FRAME_KEYFRAME, 0, stats.tick, 0, data).pack())

        # --- Checksum-Sender: 1 Hz, nur AOI-Chunks ---
        async def checksum_sender() -> None:
            last = -1
            while conn in _conns:
                if stats.tick - last >= CHECKSUM_EVERY:
                    last = stats.tick
                    _, h = _snapshot()
                    n = size // CHUNK
                    entries = [(cx, cy, int(h[cy * n + cx]))
                               for cx, cy in conn.chunks_in_aoi(size)]
                    await ws.send_bytes(protocol.Frame(
                        protocol.FRAME_CHECKSUM, 0, stats.tick, 0,
                        protocol.pack_checksums(entries)).pack())
                await asyncio.sleep(0.05)
        sender = asyncio.create_task(checksum_sender())

        # --- Command-Empfang ---
        while True:
            data = await ws.receive_bytes()
            frame = protocol.unpack(data)
            if frame.frame_type != protocol.FRAME_COMMAND:
                continue
            cmd = frame.payload[0]
            if cmd == protocol.CMD_SUBSCRIBE_AOI:
                conn.aoi = struct.unpack_from("!HHHH", frame.payload, 1)
            elif cmd == protocol.CMD_REQ_KEYFRAME:
                cnt = frame.payload[1]
                q, _ = _snapshot()
                n = size // CHUNK
                for i in range(cnt):
                    cx = frame.payload[2 + 2 * i]
                    cy = frame.payload[3 + 2 * i]
                    if cx < n and cy < n:
                        data = protocol.pack_keyframe(cx, cy, chunk_bytes(q, cx, cy))
                        await ws.send_bytes(protocol.Frame(
                            protocol.FRAME_KEYFRAME, 0, stats.tick, 0, data).pack())
            elif cmd == protocol.CMD_PLACE_FOOD:
                x, y = struct.unpack_from("!HH", frame.payload, 1)
                _apply_food_spike(x, y)
                # Broadcast an ALLE Clients (auch Absender – idempotent, da
                # der Client beim Senden selbst nichts anwendet).
                payload = protocol.pack_event(protocol.EV_FOOD, x, y,
                                               int(FOOD_AMOUNT))
                frame_out = protocol.Frame(protocol.FRAME_EVENT, 0,
                                           stats.tick, 0, payload).pack()
                dead = []
                for c in _conns:
                    try:
                        await c.ws.send_bytes(frame_out)
                    except Exception:
                        dead.append(c)
                for c in dead:
                    _conns.discard(c)
    except WebSocketDisconnect:
        pass
    finally:
        _conns.discard(conn)
        if sender:
            sender.cancel()

app.mount("/", StaticFiles(directory=str(ROOT / "frontend"), html=True),
          name="frontend")