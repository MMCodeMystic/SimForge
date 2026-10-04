"""Chunk-Layout und Hashing. Basis für Keyframes, Checksummen, AOI.

Der Hash läuft über die QUANTISIERTE (uint8) Sicht. Unsichtbare Drift
in niedrigen Fixed-Point-Bits löst damit keine Korrektur aus – nur
Abweichung, die im Bild ankommt. Client und Server quantisieren mit
derselben Formel, damit die Hashes vergleichbar sind.
"""
from __future__ import annotations
import numpy as np
from numba import njit
from .fixedpoint import FIELD_MAX

CHUNK = 64  # Chunk-Kantenlänge in Zellen; 256er-Grid -> 4x4 Chunks

def quantize(field: np.ndarray, maxv: int = int(FIELD_MAX)) -> np.ndarray:
    """int32-Fixed-Point-Feld -> uint8-Array. Exakt dieselbe Formel
    wie im Client (floor(v*255/maxv), geclampt auf [0,255])."""
    norm = np.clip(field.astype(np.float64) / maxv, 0.0, 1.0)
    return (norm * 255).astype(np.uint8)

@njit(cache=True)
def _hash_chunks(quant: np.ndarray, n: int, chunk: int, out: np.ndarray) -> None:
    """FNV-1a (32 bit) pro Chunk, deterministische Reihenfolge."""
    for cy in range(n):
        for cx in range(n):
            h = np.uint32(2166136261)
            for y in range(chunk):
                for x in range(chunk):
                    b = quant[cy * chunk + y, cx * chunk + x]
                    h = (h ^ np.uint32(b)) * np.uint32(16777619)
            out[cy * n + cx] = h

def chunk_hashes(quant: np.ndarray, size: int) -> np.ndarray:
    """Alle Chunk-Hashes eines size×size-quantisierten Feldes."""
    n = size // CHUNK
    out = np.zeros(n * n, dtype=np.uint32)
    _hash_chunks(quant, n, CHUNK, out)
    return out

def chunk_bytes(quant: np.ndarray, cx: int, cy: int) -> bytes:
    """Roher uint8-Block eines Chunks (Keyframe-Payload)."""
    q = quant[cy * CHUNK:(cy + 1) * CHUNK, cx * CHUNK:(cx + 1) * CHUNK]
    return np.ascontiguousarray(q).tobytes()