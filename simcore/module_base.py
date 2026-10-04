"""Modul-Vertrag: Manifest + Basisklasse.

Das Manifest ist der Vertrag zwischen Modul und Core. Die Registry
lädt nur Manifeste, scannt keine Klassen. Capabilities begrenzen,
was ein Modul im Runtime-Kontext darf (wird Phase 7/Store erzwingen).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol
import numpy as np

@dataclass
class ModuleManifest:
    id: str
    name: str
    version: str
    core_compat: str            # z.B. ">=0.1,<0.2"
    entry: str                  # "module.py:AntsModule" – vom Ersteller kompiliert geliefert
    fields: dict[str, str] = field(default_factory=dict)      # Feldname -> dtype (alles Fixed-Point!)
    capabilities: list[str] = field(default_factory=list)     # z.B. ["grid:write", "events:emit"]
    i18n: dict[str, str] = field(default_factory=dict)        # locale -> katalogdatei
    theme_tokens: dict[str, str] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

class SimModule(Protocol):
    manifest: ModuleManifest
    def setup(self, world: "World") -> None: ...
    def step(self, tick: int, dt: int, world: "World") -> None: ...
    def teardown(self) -> None: ...

@dataclass
class World:
    """Der simulierte Zustand. Bewusst banal für Phase 1."""
    size: int                                  # Grid-Kantenlänge (quadrisch)
    fields: dict[str, np.ndarray] = None       # name -> int32[size,size], Fixed-Point
    entities: dict[str, np.ndarray] = None     # name -> strukturiertes Array (uint16-Koordinaten)
    def __post_init__(self):
        if self.fields is None: self.fields = {}
        if self.entities is None: self.entities = {}
