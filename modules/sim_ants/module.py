"""sim_ants – Modell, Controller, View-Config. Erste Manifest-Modul-Instanz."""
from __future__ import annotations
import numpy as np

from simcore.event_bus import EventBus
from simcore.fixedpoint import SCALE, to_fixed
from simcore.module_base import ModuleManifest, World

try:
    from .kernels import ants_move, diffuse_fixed  # als Paket (modules.sim_ants)
except ImportError:
    from kernels import ants_move, diffuse_fixed  # direkter Start in modules/sim_ants

MAX_ANTS = 10_000

class AntsModule:
    manifest = ModuleManifest(
        id="sim_ants", name="Ameisen", version="0.1.0",
        core_compat=">=0.1,<0.2", entry="module:AntsModule",
        fields={"pheromone": "i4"},
        capabilities=["grid:write", "events:emit"])

    def setup(self, world: World, bus: EventBus | None = None) -> None:
        n = world.size
        world.fields.setdefault("pheromone", np.zeros((n, n), dtype=np.int64))
        self._buf = np.zeros_like(world.fields["pheromone"])
        # Startcluster in der Mitte
        m = n // 2
        world.fields["pheromone"][m-4:m+5, m-4:m+5] = to_fixed(500)
        ax = np.random.default_rng(42).integers(2, n-2, MAX_ANTS).astype("<u2")
        ay = np.random.default_rng(43).integers(2, n-2, MAX_ANTS).astype("<u2")
        world.entities["ants_x"] = ax
        world.entities["ants_y"] = ay
        self._rng = np.random.default_rng(7).integers(
            1, 2**63, MAX_ANTS, dtype=np.uint64)

    def step(self, tick: int, dt: int, world: World) -> None:
        f = world.fields["pheromone"]
        if dt > 0:  # Diffusions-Tick (dt = 4 * Tick-dt)
            evap = to_fixed(0.99)
            diffuse_fixed(f, self._buf, dt, evap)
            f[1:-1, 1:-1] = self._buf[1:-1, 1:-1]
        # Bewegung läuft JEDEM Master-Tick (30 Hz)
        ants_move(world.entities["ants_x"], world.entities["ants_y"],
                  f, self._rng, MAX_ANTS, world.size)

    def teardown(self) -> None:
        pass