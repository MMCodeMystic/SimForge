"""Event-Bus: Module emitte diskrete Events (Food platziert, etc.).

Feld-Entwicklung gehört NICHT hierher; Events sind dünn und diskret.
Phase 2 serialisiert sie als Event-Frames ins Protokoll.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class Event:
    type: str
    tick: int
    payload: dict[str, Any]

class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: str, fn: Callable[[Event], None]) -> None:
        self._subs.setdefault(event_type, []).append(fn)

    def emit(self, event: Event) -> None:
        for fn in self._subs.get(event.type, []):
            fn(event)