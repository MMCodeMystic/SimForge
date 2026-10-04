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