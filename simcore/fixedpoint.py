"""Fixed-Point-Konventionen. Verbindlich für ALLE Feld- und Positionsdaten.

Werte werden als int32 mit Skala 1<<10 (x1024) gehalten.
Bewegungs- und Diffusionsarithmetik bleibt damit auf CPU (Numba/NumPy),
CUDA (CuPy) und WebGPU bitidentisch, weil keine Floats im Spiel sind.
"""
import numpy as np

SCALE_BITS = 10
SCALE = 1 << SCALE_BITS                 # 1024
Q31 = np.int64(1) << 31                 # Fullscale-Referenz für Normierung

def to_fixed(value: float) -> np.int64:
    return np.int64(round(value * SCALE))

def from_fixed(value: np.int64) -> float:
    return float(value) / SCALE

# Feld-Maximum: Pheromonkonzentration 0..1000 in Fixed-Point
FIELD_MAX = to_fixed(1000)
