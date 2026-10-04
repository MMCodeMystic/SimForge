import { mountHeader, mountFooter, refreshAll } from "./layout.js";
import { initI18n, setLocale, onLocaleChange } from "./i18n.js";
import { initTheme } from "./theme.js";
import { startSim } from "./sim.js";

async function main() {
  initTheme();
  await initI18n();

  await mountHeader(document.getElementById("site-header"));
  await mountFooter(document.getElementById("site-footer"));
  refreshAll();

  onLocaleChange(() => refreshAll());
  document.addEventListener("theme-changed", () => refreshAll());

  startSim({
    canvas: document.getElementById("c"),
    info: document.getElementById("info"),
  });
}

main();