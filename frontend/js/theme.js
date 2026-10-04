// Theme-Verwaltung: Basis-Theme (dark/bright) + Custom-Overlay.
// Custom-Werte landen in localStorage und werden als Inline-Styles
// auf body.theme-custom gesetzt – so bleibt die Token-Kaskade intakt:
// custom überschreibt nur, was der Nutzer definiert hat.

export const THEMES = ["dark", "bright"];

let baseTheme = localStorage.getItem("simforge.theme") || "dark";
let custom = JSON.parse(localStorage.getItem("simforge.customTheme") || "{}");

export function initTheme() {
  apply();
}

function apply() {
  document.body.classList.remove("theme-dark", "theme-bright", "theme-custom");
  document.body.classList.add(`theme-${baseTheme}`);
  const overlay = document.querySelector("body.theme-custom");
  // Custom-Tokens als Inline-CSS-Variabten auf body setzen:
  const style = document.body.style;
  for (const k of Object.keys(custom)) style.removeProperty(`--${k}`);
  if (Object.keys(custom).length) {
    document.body.classList.add("theme-custom");
    for (const [k, v] of Object.entries(custom)) style.setProperty(`--${k}`, v);
  }
  localStorage.setItem("simforge.theme", baseTheme);
  localStorage.setItem("simforge.customTheme", JSON.stringify(custom));
  document.dispatchEvent(new CustomEvent("theme-changed"));
}

export function setTheme(name) {
  if (!THEMES.includes(name)) return;
  baseTheme = name;
  apply();
}
export function getTheme() { return baseTheme; }

export function setCustomToken(key, value) {   // z.B. ("accent", "#ff8a3d")
  if (value == null) delete custom[key]; else custom[key] = value;
  apply();
}
export function clearCustomTheme() {
  custom = {};
  apply();
}

// Feld-Farben fürs Canvas-Rendering. sim.js ruft das bei jedem
// theme-changed-Event neu, render() nutzt die gecachten Werte.
let fieldColors = null;
export function getThemeColors() {
  const cs = getComputedStyle(document.body);
  fieldColors = {
    empty: [ +cs.getPropertyValue("--field-empty-r"),
             +cs.getPropertyValue("--field-empty-g"),
             +cs.getPropertyValue("--field-empty-b") ],
    low:   [ +cs.getPropertyValue("--field-low-r"),
             +cs.getPropertyValue("--field-low-g"),
             +cs.getPropertyValue("--field-low-b") ],
    high:  [ +cs.getPropertyValue("--field-high-r"),
             +cs.getPropertyValue("--field-high-g"),
             +cs.getPropertyValue("--field-high-b") ],
  };
  return fieldColors;
}
