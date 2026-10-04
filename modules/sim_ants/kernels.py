"""Numba-Kernels für sim_ants. Integer-Fixed-Point, deterministisch.

Reduktionsreihenfolge ist fest (Schleifenreihenfolge), damit CPU-,
CUDA- und WebGPU-Ergebnisse bitidentisch sind.
"""
import numpy as np
from numba import njit, prange
from simcore.fixedpoint import SCALE, FIELD_MAX

@njit(parallel=True, cache=True)
def diffuse_fixed(field: np.ndarray, out: np.ndarray, dt: int, evap: int) -> None:
    """Jacobi-Diffusion in int64 Fixed-Point.

    dt, evap in Fixed-Point (z.B. evap = to_fixed(0.99)).
    out muss eine zweite Buffer sein (Jacobi, nicht Gauss-Seidel!) –
    sonst divergiert die Zellreihenfolge die Ergebnisse.
    """
    n = field.shape[0]
    for y in prange(1, n - 1):
        for x in range(1, n - 1):
            s = field[y - 1, x] + field[y + 1, x] \
              + field[y, x - 1] + field[y, x + 1] \
              + 4 * field[y, x]
            # Mittelwert (1/9), dann Evaporation als Ganzzahl-Multiplikation
            v = (s * evap) // (9 * SCALE)
            if v < 0:
                v = 0
            elif v > FIELD_MAX:
                v = FIELD_MAX
            out[y, x] = v

@njit(parallel=True, cache=True)
def ants_move(ants_x: np.ndarray, ants_y: np.ndarray,
              pheromone: np.ndarray, rng_states: np.ndarray,
              n: int, size: int) -> None:
    """Ant-Bewegung: Gradient folgen mit Zufallsdrift.

    ants_x/y: uint16-Koordinaten (fixed-scale-frei, Rasterzellen).
    rng_states: pro Ameise ein eigener LCG-State – deterministisch pro
    Ameisen-ID, unabhängig von der Thread-Reihenfolge (prange!).
    """
    for i in prange(n):
        s = rng_states[i]
        s = (s * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        rng_states[i] = s
        r = (s >> 33) & 7  # 0..7: Richtung

        x = ants_x[i]; y = ants_y[i]
        if 1 <= x < size - 1 and 1 <= y < size - 1:
            # Pheromon-Gradient (Fixpoint, Richtung mit stärkstem Anstieg)
            c = pheromone[y, x]
            best = 0; bx = x; by = y
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dx == 0 and dy == 0:
                        continue
                    g = pheromone[y + dy, x + dx] - c
                    if g > best:
                        best = g; bx = x + dx; by = y + dy
            # 70% Gradient, 30% Zufall – Float-frei über r < 6
            if r < 6 and best > 0:
                ants_x[i] = bx; ants_y[i] = by
            else:
                # Zufallsschritt (Moore-Nachbarschaft, fixe Tabelle)
                dx = (r & 1) * 2 - 1 if (r & 4) == 0 else 0
                dy = (r & 2) - 1 if (r & 4) != 0 else 0
                nx = x + dx; ny = y + dy
                if 1 <= nx < size - 1 and 1 <= ny < size - 1:
                    ants_x[i] = nx; ants_y[i] = ny
            # Pheromon hinterlassen
            pheromone[ants_y[i], ants_x[i]] += SCALE * 8