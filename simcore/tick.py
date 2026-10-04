"""Master-Tick-Loop. 30 Hz Bewegung, Diffusion jeden 4. Tick (dt=4*Tick-dt).

Eisenregeln:
 1. Ein Master-Tick-Zähler, abgeleitet von der Wanduhr NUR fürs Pacing.
 2. Überlast -> Tick-Dauer für ALLE gleichmäßig verlängern, NIE Ticks skippen.
    Ein übersprungener Diffusions-Tick ist sofort Client/Server-Divergenz.
 3. Tick-Zeit wird gemessen und als Metrik geführt (Entscheidungsgrundlage
    für die Worker-Aufteilung in Phase 6).
"""
from __future__ import annotations
import time
from typing import Callable
from .fixedpoint import SCALE

TICK_HZ = 30
TICK_DT = SCALE // TICK_HZ              # Fixed-Point dt pro Tick
DIFFUSION_EVERY = 4                     # Diffusion läuft auf jedem 4. Master-Tick
DIFFUSION_DT = TICK_DT * DIFFUSION_EVERY  #.dt der Diffusion = 4 Ticks, explizit kodiert

class TickStats:
    def __init__(self):
        self.last_tick_ms: float = 0.0
        self.max_tick_ms: float = 0.0
        self.tick: int = 0

def run_loop(step_fn: Callable[[int, int], None],
             stats: TickStats, running: Callable[[], bool]) -> None:
    """step_fn(tick, dt) – dt in Fixed-Point, wechselt zwischen TICK_DT und 0.

    Bei Diffusion-Ticks wird step_fn(tick, DIFFUSION_DT) aufgerufen, sonst
    (tick, 0). Das Modul entscheidet anhand dt>0, ob Diffusion läuft.
    """
    period = 1.0 / TICK_HZ
    drift = 0.0
    while running():
        t0 = time.perf_counter()
        tick = stats.tick
        is_diff_tick = tick % DIFFUSION_EVERY == 0
        step_fn(tick, DIFFUSION_DT if is_diff_tick else 0)
        stats.tick = tick + 1
        elapsed = time.perf_counter() - t0
        stats.last_tick_ms = elapsed * 1000
        stats.max_tick_ms = max(stats.max_tick_ms, stats.last_tick_ms)
        # Überlast: periode dynamisch anheben, Ticks NIEMALS skippen
        budget = period * (1.25 if elapsed > period else 1.0)
        drift += budget - elapsed
        if drift > 0:
            time.sleep(drift)
            drift = 0.0
        # drift < 0 (Tick zu lang) -> wir hängen hinterher, laufen ohne Sleep weiter
