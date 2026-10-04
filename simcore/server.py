# ============================================================
"""FastAPI-App: /api/modules, /ws/sim (RAW_FIELD-Upload), StaticFiles.

Phase 1 bewusst in-process: kein Worker-Prozess. Die Tick-Loop läuft
in einem Thread, der WebSocket pusht quantisierte Rohbilder (0x10).
Phase 2 ersetzt RAW_FIELD durch Keyframes/Events/Checksummen.
"""
from __future__ import annotations
import asyncio
import threading
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import protocol
from .event_bus import EventBus
from .module_base import World
from .registry import ModuleRegistry
from .tick import TickStats, run_loop, TICK_HZ, DIFFUSION_EVERY

CORE_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="SimForge")

registry = ModuleRegistry(ROOT / "modules", CORE_VERSION)
registry.discover()

bus = EventBus()
stats = TickStats()
_loaded = {}  # module_id -> Instanz
_world = None
_loop_thread: threading.Thread | None = None
_loop_on = threading.Event()

def world() -> World:
    return _world

def _make_world() -> World:
    w = World(size=256)
    from .fixedpoint import FIELD_MAX
    import numpy as np
    w.fields["pheromone"] = np.zeros((w.size, w.size), dtype=np.int64)
    w.entities["ants"] = np.zeros(10_000, dtype=[("x", "<u2"), ("y", "<u2")])
    return w

def _sim_step(tick: int, dt: int) -> None:
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
    _loop_thread = threading.Thread(target=run_loop,
                                    args=(_sim_step, stats, _loop_on.is_set),
                                    daemon=True)
    _loop_thread.start()

@app.get("/api/modules")
async def list_modules():
    return {"core": CORE_VERSION, "tick_hz": TICK_HZ,
            "diffusion_every": DIFFUSION_EVERY,
            "modules": [ {"id": m.id, "name": m.name, "version": m.version,
                          "capabilities": m.capabilities}
                         for m in registry.manifests.values() ]}

@app.get("/api/stats")
async def get_stats():
    return {"tick": stats.tick, "last_tick_ms": round(stats.last_tick_ms, 3),
            "max_tick_ms": round(stats.max_tick_ms, 3)}

@app.websocket("/ws/sim")
async def ws_sim(ws: WebSocket) -> None:
    await ws.accept()
    from .fixedpoint import FIELD_MAX
    session = stats.tick  # Platzhalter bis Auth (Phase 6)
    last_sent = -1
    try:
        while True:
            # Throttle: 1 Frame pro Diffusions-Intervall reicht fürs Rohbild
            if stats.tick - last_sent >= DIFFUSION_EVERY:
                field = _world.fields["pheromone"]
                payload = protocol.quantize_field_u8(field, int(FIELD_MAX))
                frame = protocol.Frame(protocol.FRAME_RAW_FIELD, 0, stats.tick,
                                       session, payload)
                await ws.send_bytes(frame.pack())
                last_sent = stats.tick
            await asyncio.sleep(1 / TICK_HZ)
    except WebSocketDisconnect:
        pass

app.mount("/", StaticFiles(directory=str(ROOT / "frontend"), html=True),
          name="frontend")
