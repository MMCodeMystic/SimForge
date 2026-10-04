// Simulations- und Protokoll-Logik. Unverändert gegenüber der
// Zwischenphase davor: dieselbe Integer-Arithmetik, dieselben Frames.
"use strict";

export const SIZE = 256, CHUNK = 64, NCHUNK = SIZE / CHUNK;
const SCALE = 1024, FM = 1000 * SCALE;      // FIELD_MAX
const EVAP = 1014;                          // = to_fixed(0.99)
const DENOM = 9 * SCALE;                    // Jacobi 1/9
const FOOD = 400 * SCALE;                   // = to_fixed(400)
const HEADER = 24;

export function startSim({ canvas, info }) {
  const ctx = canvas.getContext("2d");

  let field = new Int32Array(SIZE * SIZE);
  let buf   = new Int32Array(SIZE * SIZE);
  let tick = 0, synced = false;
  let matches = 0, mismatches = 0, lastReq = 0;

  const ws = new WebSocket(`ws://${location.host}/ws/sim`);
  ws.binaryType = "arraybuffer";

  function packFrame(type, payload) {
    const b = new ArrayBuffer(HEADER + payload.length);
    const d = new DataView(b);
    d.setUint8(0, 0x53); d.setUint8(1, 0x4D); d.setUint8(2, 0x46); d.setUint8(3, 0x31);
    d.setUint8(4, type); d.setUint8(5, 0);
    d.setUint16(6, 0);
    d.setUint32(8, tick);
    d.setUint32(12, payload.length);
    d.setUint32(16, 0); d.setUint32(20, 0);
    new Uint8Array(b, HEADER).set(payload);
    return b;
  }
  const send = (type, payload) => ws.send(packFrame(type, payload));

  function diffuse() {
    for (let y = 1; y < SIZE - 1; y++) {
      const row = y * SIZE;
      for (let x = 1; x < SIZE - 1; x++) {
        const i = row + x;
        const s = field[i - SIZE] + field[i + SIZE]
                + field[i - 1] + field[i + 1] + 4 * field[i];
        let v = Math.floor((s * EVAP) / DENOM);
        if (v > FM) v = FM;
        buf[i] = v;
      }
    }
    const t = field; field = buf; buf = t;
  }

  const qbuf = new Uint8Array(SIZE * SIZE);
  function quantize() {
    for (let i = 0; i < field.length; i++) {
      const f = field[i];
      let v = 0;
      if (f > 0) { v = Math.floor((f * 255) / FM); if (v > 255) v = 255; }
      qbuf[i] = v;
    }
    return qbuf;
  }
  function hashChunk(cx, cy) {
    let h = 2166136261;
    const x0 = cx * CHUNK, y0 = cy * CHUNK;
    for (let y = 0; y < CHUNK; y++) {
      const row = (y0 + y) * SIZE + x0;
      for (let x = 0; x < CHUNK; x++) {
        h = Math.imul(h ^ qbuf[row + x], 16777619) >>> 0;
      }
    }
    return h >>> 0;
  }

  function applyKeyframe(p) {
    const cx = p[0], cy = p[1], data = p.subarray(2);
    for (let y = 0; y < CHUNK; y++) {
      const dst = (cy * CHUNK + y) * SIZE + cx * CHUNK;
      for (let x = 0; x < CHUNK; x++) {
        field[dst + x] = Math.round((data[y * CHUNK + x] * FM) / 255);
      }
    }
  }
  function applyFoodSpike(x, y) {
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -2; dx <= 2; dx++) {
        const w = 3 - (Math.abs(dx) + Math.abs(dy));
        if (w <= 0) continue;
        const yy = y + dy, xx = x + dx;
        if (yy >= 0 && yy < SIZE && xx >= 0 && xx < SIZE) {
          const i = yy * SIZE + xx;
          let v = field[i] + Math.floor((FOOD * w) / 3);
          if (v > FM) v = FM;
          field[i] = v;
        }
      }
    }
  }

  function render() {
    const img = ctx.createImageData(SIZE, SIZE);
    const px = img.data;
    for (let i = 0; i < SIZE * SIZE; i++) {
      const v = field[i] > 0 ? Math.floor((field[i] * 255) / FM) : 0;
      const o = i * 4;
      px[o] = 0; px[o + 1] = v; px[o + 2] = v >> 2; px[o + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }

  ws.onopen = () => {
    const b = new Uint8Array(9); b[0] = 0x01;
    const dv = new DataView(b.buffer);
    dv.setUint16(1, 0); dv.setUint16(3, 0); dv.setUint16(5, 255); dv.setUint16(7, 255);
    send(0x04, b);
  };

  ws.onmessage = (ev) => {
    const d = new DataView(ev.data);
    if (d.getUint32(0) !== 0x534D4631) return;
    const type = d.getUint8(4);
    const frameTick = d.getUint32(8);
    if (!synced) { tick = frameTick; synced = true; }
    if (frameTick - tick > 120) tick = frameTick;
    const p = new Uint8Array(ev.data, HEADER);

    if (type === 0x01) {
      applyKeyframe(p);
    } else if (type === 0x02) {
      const x = d.getUint16(HEADER + 1), y = d.getUint16(HEADER + 3);
      applyFoodSpike(x, y);
    } else if (type === 0x03) {
      const count = d.getUint16(HEADER);
      quantize();
      const want = [];
      for (let i = 0; i < count; i++) {
        const off = HEADER + 2 + i * 6;
        const cx = d.getUint8(off), cy = d.getUint8(off + 1);
        const serverHash = d.getUint32(off + 2);
        if (hashChunk(cx, cy) === serverHash) matches++;
        else { mismatches++; if (cx < NCHUNK && cy < NCHUNK) want.push(cx, cy); }
      }
      if (want.length && performance.now() - lastReq > 1000) {
        lastReq = performance.now();
        const b = new Uint8Array(2 + want.length);
        b[0] = 0x02; b[1] = want.length / 2;
        b.set(want, 2);
        send(0x04, b);
      }
    }
  };
  ws.onclose = () => { info.textContent = "getrennt"; };

  setInterval(() => {
    if (!synced) return;
    tick++;
    if (tick % 4 === 0) diffuse();
    if (tick % 2 === 0) render();
  }, 1000 / 30);

  setInterval(() => {
    info.textContent = `Tick ${tick} · Hash ok ${matches} · korrigiert ${mismatches}`
      + ` · ${synced ? "verbunden" : "wartet"}`;
  }, 500);

  canvas.addEventListener("click", (e) => {
    const r = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - r.left) / r.width * SIZE);
    const y = Math.floor((e.clientY - r.top) / r.height * SIZE);
    const b = new Uint8Array(5); b[0] = 0x03;
    new DataView(b.buffer).setUint16(1, x);
    new DataView(b.buffer).setUint16(3, y);
    send(0x04, b);
  });
}
