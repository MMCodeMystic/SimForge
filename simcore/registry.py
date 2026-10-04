"""ModuleRegistry: Manifest-basiertes Laden. Kein Klassen-Scanning.

Lädt modules/*/module.json, prüft core_compat, importiert entry via importlib.
Community-Bundles: Signaturprüfung (Ed25519) kommt in Phase 7 – der Hook
ist `verify_bundle()` und bewusst schon da.
"""
from __future__ import annotations
import importlib
import json
from pathlib import Path
from typing import Any

class IncompatibleModuleError(Exception):
    pass

class ModuleRegistry:
    def __init__(self, modules_dir: Path, core_version: str):
        self.modules_dir = modules_dir
        self.core_version = core_version
        self.manifests: dict[str, Any] = {}

    def verify_bundle(self, module_dir: Path) -> None:
        """Hook für Signaturprüfung (Phase 7). Läuft VOR dem Import."""
        pass  # TODO(Phase 7): Ed25519 gegen vertrauenswürdige Publisher-Keys

    def discover(self) -> None:
        for mf in sorted(self.modules_dir.glob("*/module.json")):
            # utf-8-sig: toleriert BOM (Windows-Editoren) und liest BOM-lose Dateien identisch
            manifest = json.loads(mf.read_text(encoding="utf-8-sig"))
            from .module_base import ModuleManifest
            m = ModuleManifest(**manifest)
            if not self._compat_ok(m.core_compat):
                raise IncompatibleModuleError(
                    f"{m.id}: core_compat {m.core_compat} passt nicht zu {self.core_version}")
            self.verify_bundle(mf.parent)
            self.manifests[m.id] = m

    def _compat_ok(self, spec: str) -> bool:
        # Minimal-Range-Parser: unterstützt ">=x.y,<a.b" – reicht für Phase 1
        from packaging.version import Version
        from packaging.specifiers import SpecifierSet
        return Version(self.core_version) in SpecifierSet(spec)

    def load(self, module_id: str) -> Any:
        m = self.manifests[module_id]
        mod_path, cls_name = m.entry.split(":")
        package = f"modules.{m.id}.{mod_path.replace('/', '.')}"
        cls = getattr(importlib.import_module(package), cls_name)
        return cls()