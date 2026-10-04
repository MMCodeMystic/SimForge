# Changelog

## 0.1.0 – Phase 1
### Added
- simcore-Kern: Fixed-Point-Konvention (Skala 1024), ModuleRegistry mit Manifest-Loading und core_compat-Range-Check, EventBus, Binary-Protokoll v1 (struct-Header, Master-Tick in jedem Frame), Master-Tick-Loop 30 Hz mit Diffusion auf jedem 4. Tick (dt = 4 × Tick-dt), Tick-Zeit-Messung mit Verlangsamung statt Tick-Skip.
- Modul sim-ants: Numba-Kernels für Diffusion (Jacobi, deterministische Reihenfolge) und Ameisenbewegung (pro Ameise eigener LCG-State, thread-reihenfolge-unabhängig).
- FastAPI: /api/modules, /api/stats, /ws/sim mit rohem uint8-Feldbild (Frame 0x10) zur Verifikation.
- Frontend: Canvas-Verifikationsansicht mit Tick-Anzeige und FPS-Zähler.
### Notes
- Kein Worker-Prozess, bewusst in-process; Aufteilung erst nach Tick-Messung (Phase 6).
- Kein Delta-Encoding; Rohbild dient nur der Verifikation und wird in Phase 2 durch Keyframes/Events/Checksummen ersetzt.

## 0.2.0 – Phase 2
### Added
- Chunk-System (64×64): Quantisierung int32→uint8, FNV-1a-Chunk-Hashes über die quantisierte Sicht; nur sichtbare Abweichung triggert Korrektur.
- Protokoll v1 vollständig: Keyframe-, Event- und Checksum-Frames, Command-Pfad (AOI-Subscribe, Keyframe-Anfrage, Futter platzieren). Rohbild-Frame 0x10 deprecated.
- Server: Join-Burst mit AOI-Keyframes, Checksum-Runden jede Sekunde (nur AOI-Chunks), Event-Broadcast an alle Clients, Simulations-Lock zwischen Tick-Thread und Snapshots.
- Frontend: lokale Feld-Simulation mit identischer Integer-Arithmetik, Hash-Abgleich, gedrosselte Keyframe-Anforderung, Futter-Klick als Command.
### Changed
- Server sendet keine kontinuierlichen Bilddaten mehr; Verkehr ist jetzt Join-Burst + 1 Hz Checksummen + Events. Drift-Healing ist client-getrieben.
### Measurements
- Server-Tick 0,38 ms bei 10.000 Ameisen (Budget 33 ms), bestätigt in-process-Betrieb ohne Worker-Prozess für die aktuelle Last.
- max_tick_ms ~312 ms ist einmalige Numba-JIT-Kompilierung beim ersten Tick, kein Lastproblem.