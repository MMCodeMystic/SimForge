// Header/Footer laden + Toolbar dynamisch aufbauen (Theme- und
// Sprach-Umschalter). Der Toolbar-Aufbau bleibt hier zentral, damit
// Module in Phase 3 nur noch Items registrieren müssen.

import { t, setLocale, getLocale, LOCALES, applyI18n } from "./i18n.js";
import { THEMES, setTheme, getTheme } from "./theme.js";

export async function mountHeader(target) {
  const res = await fetch("partials/header.html");
  target.innerHTML = await res.text();
  buildToolbar(target.querySelector(".toolbar"));
  refresh(target);
}

export async function mountFooter(target) {
  const res = await fetch("partials/footer.html");
  target.innerHTML = await res.text();
  refresh(target);
}

function buildToolbar(bar) {
  // Theme-Buttons
  for (const name of THEMES) {
    const b = document.createElement("button");
    b.dataset.theme = name;
    b.addEventListener("click", () => setTheme(name));
    bar.appendChild(b);
  }
  bar.insertAdjacentHTML("beforeend", '<span class="spacer"></span>');

  // Sprach-Select
  const sel = document.createElement("select");
  sel.id = "locale-select";
  sel.addEventListener("change", () => setLocale(sel.value));
  bar.appendChild(sel);
  sel.style.visibility = "hidden";   // Optionen nach i18n-Init befüllt
}

// Beschriftung nach jedem Sprach- oder Theme-Wechsel auffrischen
function refresh(root) {
  root.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll(".toolbar button[data-theme]").forEach(b => {
    b.textContent = t(`theme.${b.dataset.theme}`);
    b.dataset.themeActive = b.dataset.theme === getTheme() ? "1" : "0";
  });
  const sel = root.querySelector("#locale-select");
  if (sel && sel.style.visibility === "hidden") {
    sel.innerHTML = LOCALES
      .map(l => `<option value="${l}">${t(`locale.${l}`)}</option>`).join("");
    sel.value = getLocale();
    sel.style.visibility = "visible";
  } else if (sel) {
    sel.value = getLocale();
  }
}

export function onUIRefresh(fn) { refreshListeners.add(fn); }
const refreshListeners = new Set();
// wird von main.js bei locale/theme-Änderungen aufgerufen:
export function refreshAll() {
  refresh(document);
  refreshListeners.forEach(fn => fn());
}
