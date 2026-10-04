// i18n mit Fallback-Kette: key -> aktuelle Sprache -> en -> key selbst.
// Module (Phase 3) mergen ihre Keys später via registerCatalog() rein.

const catalogs = {};          // locale -> {key: text}
let current = localStorage.getItem("simforge.locale") || "de";
const listeners = new Set();

export const LOCALES = ["de", "en"];

export async function initI18n() {
  for (const loc of LOCALES) {
    const res = await fetch(`i18n/${loc}.json`);
    catalogs[loc] = await res.json();
  }
  document.documentElement.lang = current;
}

export function t(key) {
  return catalogs[current]?.[key] ?? catalogs["en"]?.[key] ?? key;
}

export function setLocale(loc) {
  if (!LOCALES.includes(loc)) return;
  current = loc;
  localStorage.setItem("simforge.locale", loc);
  document.documentElement.lang = loc;
  for (const fn of listeners) fn();
}

export function getLocale() { return current; }

export function onLocaleChange(fn) { listeners.add(fn); }

// Für Module (Phase 3): eigene Keys nachregistrieren
export function registerCatalog(locale, catalog) {
  catalogs[locale] = { ...(catalogs[locale] || {}), ...catalog };
}

// Alle [data-i18n]-Elemente neu beschriften
export function applyI18n(root = document) {
  root.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
}