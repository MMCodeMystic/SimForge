"""KernelArray: dünne Abstraktion über NumPy/CuPy (Python Array API).

Die Kernel schreiben gegen xp (array module), nie direkt gegen numpy.
Damit bleibt der spätere CuPy-Wechsel ein Einzeiler in dieser Datei.
"""
from __future__ import annotations
from typing import Any

try:  # CuPy nur, wenn installiert UND CUDA vorhanden
    import cupy as xp  # type: ignore
    _GPU = xp.is_available()
except Exception:
    import numpy as xp  # type: ignore
    _GPU = False

backend = "cupy" if _GPU else "numpy"

def backend_mod() -> Any:
    return xp

def is_gpu() -> bool:
    return _GPU