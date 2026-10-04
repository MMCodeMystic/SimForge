// Entry-Modul: Layout initialisieren, dann Simulation starten.
import { mountHeader, mountFooter } from "./layout.js";
import { startSim } from "./sim.js";

async function main() {
  await mountHeader(document.getElementById("site-header"));
  await mountFooter(document.getElementById("site-footer"));
  startSim({
    canvas: document.getElementById("c"),
    info: document.getElementById("info"),
  });
}

main();