// Lädt Header/Footer-Fragmente zur Laufzeit per fetch (kein Build-Tool).
// Phase 3 kann das durch Modul-Bundles ersetzen; die Funktionen
// mountHeader/mountFooter bleiben als Schnittstelle stabil.
export async function mountHeader(target) {
  const res = await fetch("partials/header.html");
  target.innerHTML = await res.text();
}

export async function mountFooter(target) {
  const res = await fetch("partials/footer.html");
  target.innerHTML = await res.text();
}