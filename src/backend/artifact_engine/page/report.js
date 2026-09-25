/* Interactive report renderer — one scene per chapter, every value from the run.
   The payload (window.__BIOQL_REPORT) carries chapters, scenes, beats and PyMOL
   meshes; this file only draws them. No number is computed here that the payload
   does not already state.  MOLEVERA / BIOQL */
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.183.2/+esm";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/controls/OrbitControls.js/+esm";
import { RoomEnvironment } from "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/environments/RoomEnvironment.js/+esm";
import { CSS2DRenderer, CSS2DObject } from "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/renderers/CSS2DRenderer.js/+esm";
import { EffectComposer } from "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/postprocessing/EffectComposer.js/+esm";
import { RenderPass } from "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/postprocessing/RenderPass.js/+esm";
import { GTAOPass } from "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/postprocessing/GTAOPass.js/+esm";
import { OutputPass } from "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/postprocessing/OutputPass.js/+esm";

const R = window.__BIOQL_REPORT;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const NARROW = matchMedia("(max-width: 980px)").matches;
// English is the report's own language; Spanish is the toggle.
const S = { lang: "en", ch: 0, beat: 0, playing: false, t: 0 };

const COL = { bg: 0x0b0f14, ss: { H: 0x6f8aa8, S: 0xa9bfd4, L: 0x56697d } };

/* Values come from the pipeline, not from a person, but they still reach the DOM:
   escape everything before it is written as HTML. */
const esc = v => String(v ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ── three.js stage ───────────────────────────────────────────────────── */
const host = $("#stage");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, NARROW ? 1.5 : 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
host.appendChild(renderer.domElement);
const labels = new CSS2DRenderer();
labels.domElement.className = "labels";
host.appendChild(labels.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(COL.bg);
scene.fog = new THREE.FogExp2(COL.bg, 0.0042);
const camera = new THREE.PerspectiveCamera(36, 1, 0.3, 4000);
camera.position.set(0, 0, 140);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.minDistance = 4;
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;
scene.add(new THREE.HemisphereLight(0xdfe8f5, 0x1e170f, 0.7));
const key = new THREE.DirectionalLight(0xffffff, 1.7); key.position.set(-30, 45, 40); scene.add(key);
const fill = new THREE.DirectionalLight(0xc9d8ff, 0.45); fill.position.set(40, -10, 30); scene.add(fill);
const rim = new THREE.DirectionalLight(0x8fb8ff, 0.6); rim.position.set(10, 20, -50); scene.add(rim);

// Ambient occlusion is what makes a cartoon read as a solid object rather than a
// flat ribbon. Faded or see-through meshes must not cast it, or a ghosted layer
// darkens everything behind it.
const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }));
composer.addPass(new RenderPass(scene, camera));
let gtao = null;
if (!NARROW) {
  try {
    gtao = new GTAOPass(scene, camera, 1, 1);
    gtao.output = GTAOPass.OUTPUT.Default;
    gtao.blendIntensity = 0.9;
    gtao.updateGtaoMaterial({ radius: 2.6, distanceExponent: 1.4, thickness: 1.6, scale: 1.25, samples: 14 });
    gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 12 });
    const base = gtao._overrideVisibility.bind(gtao);
    gtao._overrideVisibility = function () {
      base();
      this.scene.traverse(o => {
        if (o.isMesh && o.visible && o.material && (o.material.opacity < 0.95 || !o.material.depthWrite)) {
          o.visible = false;
          this._visibilityCache.push(o);
        }
      });
    };
    composer.addPass(gtao);
  } catch (e) { gtao = null; }
}
composer.addPass(new OutputPass());

const world = new THREE.Group();
scene.add(world);

function clearWorld() {
  while (world.children.length) {
    const o = world.children.pop();
    o.traverse?.(n => { n.geometry?.dispose?.(); n.material?.dispose?.(); if (n.element) n.element.remove(); });
    world.remove(o);
  }
}
function label(text, cls = "") {
  const d = document.createElement("div");
  d.className = "tag " + cls; d.textContent = text;
  const o = new CSS2DObject(d); o.center.set(0.5, 1); return o;
}
function resize() {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h); labels.setSize(w, h); composer.setSize(w, h);
  gtao?.setSize(w, h);
  camera.aspect = w / Math.max(1, h); camera.updateProjectionMatrix();
}
addEventListener("resize", resize);

/* ── mesh decoding (same packing the builder writes) ──────────────────── */
const meshCache = new Map();
async function meshGeometry(k) {
  if (meshCache.has(k)) return meshCache.get(k);
  const m = R.meshes[k]; if (!m) return null;
  const bin = Uint8Array.from(atob(m.b64), c => c.charCodeAt(0));
  const buf = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
  const nv = m.nv, nt = m.nt;
  const p16 = new Int16Array(buf, 0, nv * 3), pos = new Float32Array(nv * 3);
  for (let i = 0; i < nv * 3; i++) pos[i] = p16[i] * m.scale;
  const nor = new Int8Array(buf, nv * 6, nv * 3);
  const idx = new Uint32Array(buf.slice(nv * 9, nv * 9 + nt * 12));
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.BufferAttribute(nor, 3, true));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  g.computeBoundingSphere();
  meshCache.set(k, g);
  return g;
}
function plddtColor(b) {           // the scale every folding model uses
  if (b == null) return new THREE.Color(0x56697d);
  if (b >= 90) return new THREE.Color(0x2f6fd0);
  if (b >= 70) return new THREE.Color(0x56b4e9);
  if (b >= 50) return new THREE.Color(0xe9c46a);
  return new THREE.Color(0xe4574c);
}
const DOM_COL = [0x5b8def, 0xe9a032, 0x2dd4bf, 0xd0577f, 0x8b74f4, 0x7ed08a];

function paintMesh(geom, m, mode, domains) {
  const nv = geom.attributes.position.count, idx = geom.index.array;
  const col = new Float32Array(nv * 3), done = new Uint8Array(nv);
  const resKeys = Object.keys(m.resEnd).map(Number).sort((a, b) => a - b);
  let t0 = 0;
  for (const ri of resKeys) {
    const t1 = m.resEnd[ri], res = m.res[ri] || {};
    let c;
    if (mode === "plddt") c = plddtColor(res.b);
    else if (mode === "domains") {
      c = new THREE.Color(0x3a4757);
      domains?.forEach((d, i) => { if (ri >= d.from && ri < d.to) c = new THREE.Color(DOM_COL[i % DOM_COL.length]); });
    } else c = new THREE.Color(COL.ss[res.ss] ?? COL.ss.L);
    for (let tr = t0; tr < t1; tr++) for (let k = 0; k < 3; k++) {
      const v = idx[3 * tr + k];
      if (!done[v]) { done[v] = 1; col[3 * v] = c.r; col[3 * v + 1] = c.g; col[3 * v + 2] = c.b; }
    }
    t0 = t1;
  }
  geom.setAttribute("color", new THREE.BufferAttribute(col, 3));
}

async function addCartoon(k, { grow = true, mode = "ss", domains = null } = {}) {
  const g = await meshGeometry(k); const m = R.meshes[k];
  if (!g) return null;
  paintMesh(g, m, mode, domains);
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.42, metalness: 0.05, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(g, mat);
  mesh.userData.meta = m;
  world.add(mesh);
  const box = new THREE.Box3().setFromObject(mesh), sz = box.getSize(new THREE.Vector3()).length();
  mesh.userData.fit = sz;
  if (grow && !REDUCED) { g.setDrawRange(0, 0); mesh.userData.grow = { t: 0, total: m.nt }; }
  return mesh;
}

/* ── ribbon helpers (sequence as a strip of cells) ─────────────────────── */
function ribbon(seq, { perRow = 60, cell = 1.6, colorFn, y0 = 0 } = {}) {
  const g = new THREE.Group();
  const geo = new THREE.PlaneGeometry(cell * 0.92, cell * 0.92);
  const mat = new THREE.MeshBasicMaterial({ vertexColors: false, transparent: true });
  const inst = new THREE.InstancedMesh(geo, mat, seq.length);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), Sc = new THREE.Vector3(1, 1, 1);
  const rows = Math.ceil(seq.length / perRow);
  for (let i = 0; i < seq.length; i++) {
    const r = Math.floor(i / perRow), c = i % perRow;
    M.compose(new THREE.Vector3((c - perRow / 2) * cell, y0 + (rows / 2 - r) * cell * 1.15, 0), Q, Sc);
    inst.setMatrixAt(i, M);
    inst.setColorAt(i, new THREE.Color(colorFn ? colorFn(seq[i], i) : 0x88a0b8));
  }
  inst.instanceColor.needsUpdate = true;
  g.add(inst);
  g.userData.inst = inst; g.userData.perRow = perRow; g.userData.cell = cell; g.userData.rows = rows;
  return g;
}
function cellPos(g, i) {
  const { perRow, cell, rows } = g.userData;
  const r = Math.floor(i / perRow), c = i % perRow;
  return new THREE.Vector3((c - perRow / 2) * cell, (rows / 2 - r) * cell * 1.15, 0);
}

/* ── scenes ───────────────────────────────────────────────────────────── */
const SCENES = {
  async cover(sc) {
    const mesh = sc.mesh ? await addCartoon(sc.mesh, { grow: false, mode: "ss" }) : null;
    fit(mesh ? mesh.userData.fit * 1.25 : 120);
    return { tick: (dt) => { world.rotation.y += dt * 0.12; } };
  },

  async protein_chain(sc) {
    const AA_COL = a => "AVLIMFWYC".includes(a) ? 0xe9a032 : "DEKRH".includes(a) ? 0x5b8def : "STNQ".includes(a) ? 0x2dd4bf : 0x7b8a9c;
    const g = ribbon(sc.seq, { perRow: 60, colorFn: AA_COL });
    world.add(g);
    if (sc.signal > 0) {
      const t = label(S.lang === "es" ? "péptido señal" : "signal peptide", "sig");
      t.position.copy(cellPos(g, Math.max(0, Math.floor(sc.signal / 2)))).add(new THREE.Vector3(0, 2.2, 0));
      world.add(t);
    }
    (sc.domains || []).forEach((d, i) => {
      const t = label(d.name, "dom");
      t.position.copy(cellPos(g, Math.floor((d.start + d.end) / 2))).add(new THREE.Vector3(0, -2.4, 0));
      t.element.style.borderColor = "#" + DOM_COL[i % DOM_COL.length].toString(16).padStart(6, "0");
      world.add(t);
    });
    fit(Math.max(70, g.userData.perRow * 1.9));
    return {
      focus: (f) => {
        const inst = g.userData.inst;
        for (let i = 0; i < sc.seq.length; i++) {
          let c = AA_COL(sc.seq[i]);
          if (f.cleave && i < sc.signal) c = 0xd0577f;
          if (f.cys && sc.cys.includes(i)) c = 0xe9c46a;
          if (f.domains) {
            c = 0x3a4757;
            (sc.domains || []).forEach((d, k) => { if (i >= d.start && i < d.end) c = DOM_COL[k % DOM_COL.length]; });
          }
          inst.setColorAt(i, new THREE.Color(c));
        }
        inst.instanceColor.needsUpdate = true;
      },
    };
  },

  async cartoon(sc) {
    const mesh = sc.mesh ? await addCartoon(sc.mesh, { grow: true, mode: "ss", domains: sc.domains }) : null;
    if (!mesh) return gapScene();
    const size = mesh.userData.fit;
    fit(size * 1.25);
    const res = mesh.userData.meta.res || [];
    return {
      tick: (dt) => { if (!fly) world.rotation.y += dt * 0.08; },
      focus: (f) => {
        if (f.color) paintMesh(mesh.geometry, mesh.userData.meta, f.color, sc.domains);
        if (f.grow && !REDUCED) {
          mesh.geometry.setDrawRange(0, 0);
          mesh.userData.grow = { t: 0, total: mesh.userData.meta.nt };
          fit(size * 1.25, { snap: false });
        }
        // a domain sentence flies to that domain; a confidence one pulls back to the whole fold
        if (f.color === "domains" && sc.domains?.length && res.length) {
          const d = sc.domains[0], mid = res[Math.floor((d.from + d.to) / 2)];
          if (mid) lookAt(mid.p, size * 0.75);
        } else if (f.color === "plddt") {
          fit(size * 1.1, { snap: false, angle: -0.35, height: 0.3 });
        }
      },
    };
  },

  async transcript(sc) {
    const B_COL = { A: 0x4ba3e3, U: 0xe9a032, G: 0x7ed08a, C: 0xd0577f, N: 0x556 };
    const g = ribbon(sc.seq, { perRow: 80, cell: 1.25, colorFn: b => B_COL[b] ?? 0x556 });
    world.add(g);
    (sc.regions || []).forEach(r => {
      const t = label(r.name, "reg");
      t.position.copy(cellPos(g, Math.floor((r.start + r.end) / 2))).add(new THREE.Vector3(0, 1.8, 0));
      world.add(t);
    });
    fit(120);
    const paint = (f) => {
      const inst = g.userData.inst;
      for (let i = 0; i < sc.seq.length; i++) {
        let c = B_COL[sc.seq[i]] ?? 0x556;
        if (f.region) {
          const r = (sc.regions || []).find(x => x.name === f.region);
          c = r && i >= r.start && i < r.end ? c : 0x2a3340;
        }
        if (f.kozak && sc.kozak >= 0) c = (i >= sc.kozak && i < sc.kozak + 6) ? 0xffffff : 0x2a3340;
        inst.setColorAt(i, new THREE.Color(c));
      }
      inst.instanceColor.needsUpdate = true;
    };
    return {
      focus: (f) => {
        paint(f);
        const r = f.region && (sc.regions || []).find(x => x.name === f.region);
        if (r) lookAt(cellPos(g, Math.floor((r.start + r.end) / 2)), 44);
        else if (f.kozak && sc.kozak >= 0) lookAt(cellPos(g, sc.kozak), 26);
        else if (f.regions) fit(124, { snap: false });
      },
    };
  },

  async translation(sc) {
    const g = ribbon(sc.cds, { perRow: 90, cell: 1.1, colorFn: () => 0x3a4757 });
    world.add(g);
    const prot = ribbon(sc.protein, { perRow: 30, cell: 2.2, colorFn: () => 0x2dd4bf, y0: -26 });
    world.add(prot);
    prot.userData.inst.count = 0;
    fit(130);
    let i = 0, acc = 0, lastLook = -1;
    return {
      tick: (dt) => {
        if (REDUCED) { prot.userData.inst.count = sc.protein.length; return; }
        acc += dt * 26;
        if (!fly && i < sc.n_codons && i % 24 === 0 && i !== lastLook) {
          lastLook = i;
          lookAt(cellPos(g, Math.min(i * 3, sc.cds.length - 1)), 58, 1.2);
        }
        while (acc > 1 && i < sc.n_codons) {
          const inst = g.userData.inst;
          for (let k = 0; k < 3; k++) inst.setColorAt(i * 3 + k, new THREE.Color(0xe9a032));
          inst.instanceColor.needsUpdate = true;
          prot.userData.inst.count = Math.min(++i, sc.protein.length);
          acc -= 1;
        }
      },
    };
  },

  async rna3d(sc) {
    const withMesh = (sc.elements || []).filter(e => e.mesh);
    if (!withMesh.length) return gapScene();
    let x = -((withMesh.length - 1) * 30) / 2, biggest = 60;
    for (const e of withMesh) {
      const mesh = await addCartoon(e.mesh, { grow: true, mode: "ss" });
      if (!mesh) continue;
      mesh.position.x = x;
      const t = label(`${e.name} · ${e.n} nt`, "reg");
      t.position.set(x, 18, 0); world.add(t);
      biggest = Math.max(biggest, mesh.userData.fit * 1.6);
      x += 30;
    }
    fit(biggest);
    return { tick: (dt) => { world.rotation.y += dt * 0.15; } };
  },

  async quantum(sc) {
    const n = Math.max(1, Math.min(Number(sc.n_qubits) || 0, 64));
    const geo = new THREE.BoxGeometry(2.1, 2.1, 2.1);
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.35, metalness: 0.2 });
    const inst = new THREE.InstancedMesh(geo, mat, n);
    const per = Math.ceil(Math.sqrt(n)), M = new THREE.Matrix4(), Q = new THREE.Quaternion(), Sc = new THREE.Vector3(1, 1, 1);
    for (let i = 0; i < n; i++) {
      M.compose(new THREE.Vector3(((i % per) - per / 2) * 3.2, (per / 2 - Math.floor(i / per)) * 3.2, 0), Q, Sc);
      inst.setMatrixAt(i, M); inst.setColorAt(i, new THREE.Color(0x223040));
    }
    inst.instanceColor.needsUpdate = true;
    world.add(inst);
    const t = label(`${sc.n_qubits} qubits · ${sc.n_terms} ${S.lang === "es" ? "términos" : "terms"}`, "reg");
    t.position.set(0, per * 1.9, 0); world.add(t);
    fit(per * 5.2);
    let k = 0, acc = 0;
    return {
      tick: (dt) => {
        acc += dt * 8;
        while (acc > 1 && k < n) { inst.setColorAt(k++, new THREE.Color(0xe9a032)); inst.instanceColor.needsUpdate = true; acc -= 1; }
        world.rotation.y = Math.sin(performance.now() / 3400) * 0.25;
      },
    };
  },

  async molecule(sc) {
    if (!sc.atoms?.length) return gapScene();
    const EL = { C: 0x9aa7b4, N: 0x4b7ee3, O: 0xe4574c, F: 0x7ed08a, Cl: 0x5fc98a, Br: 0xb4643c,
                 I: 0x9b59b6, S: 0xe9c46a, P: 0xe08a3c, H: 0xdfe7ef, B: 0xd9a3a3, Si: 0xc8b28a, Se: 0xd0843c };
    const K = 3.4;                                   // Å -> scene units
    const heavy = sc.atoms.map((a, i) => ({ ...a, i })).filter(a => a.e !== "H");
    const sph = new THREE.IcosahedronGeometry(1, 3);
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.32, metalness: 0.08 });
    const balls = new THREE.InstancedMesh(sph, mat, heavy.length);
    const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3();
    heavy.forEach((a, k) => {
      M.compose(new THREE.Vector3(a.p[0] * K, a.p[1] * K, a.p[2] * K), Q.identity(), V.setScalar(a.r * K * 0.30));
      balls.setMatrixAt(k, M);
      balls.setColorAt(k, new THREE.Color(EL[a.e] ?? 0x8899aa));
    });
    balls.instanceColor.needsUpdate = true;
    world.add(balls);

    const keep = new Set(heavy.map(a => a.i));
    const bonds = (sc.bonds || []).filter(b => keep.has(b[0]) && keep.has(b[1]));
    const cyl = new THREE.CylinderGeometry(1, 1, 1, 12, 1, true);
    const sticks = new THREE.InstancedMesh(cyl, mat.clone(), bonds.length * 2);
    const UP = new THREE.Vector3(0, 1, 0);
    let k = 0;
    for (const [i, j, order] of bonds) {
      const a = new THREE.Vector3(...sc.atoms[i].p).multiplyScalar(K);
      const b = new THREE.Vector3(...sc.atoms[j].p).multiplyScalar(K);
      const mid = a.clone().add(b).multiplyScalar(0.5);
      const rad = (order >= 2 ? 0.20 : 0.14) * K * 0.5;
      for (const [from, to, at] of [[a, mid, i], [mid, b, j]]) {
        const d = to.clone().sub(from), len = d.length();
        Q.setFromUnitVectors(UP, d.clone().normalize());
        M.compose(from.clone().add(to).multiplyScalar(0.5), Q, V.set(rad, len, rad));
        sticks.setMatrixAt(k, M);
        sticks.setColorAt(k, new THREE.Color(EL[sc.atoms[at].e] ?? 0x8899aa));
        k++;
      }
    }
    sticks.instanceColor.needsUpdate = true;
    world.add(sticks);
    fit((sc.span || 10) * K * 2.5, { height: 0.12 });
    return {
      tick: (dt) => {
        if (fly) return;
        world.rotation.y += dt * 0.24;
        world.rotation.x = Math.sin(performance.now() / 5200) * 0.14;
      },
      focus: (f) => { if (f.spin) fit((sc.span || 10) * K * 2.1, { snap: false, angle: 0.5, height: 0.28 }); },
    };
  },

  async rules(sc) {
    (sc.rules || []).forEach((r, i) => {
      const frac = Math.max(0.03, Math.min(1.6, Number(r.value) / r.limit));
      const w = 30 * Math.min(frac, 1.6);
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, 3.4, 3.4),
        new THREE.MeshStandardMaterial({ color: r.pass ? 0x7ed08a : 0xe4574c, roughness: 0.4 }));
      m.position.set(-18 + w / 2, 12 - i * 8, 0);
      world.add(m);
      const lim = new THREE.Mesh(new THREE.BoxGeometry(0.5, 5, 0.5),
        new THREE.MeshStandardMaterial({ color: 0x8b9bb0 }));
      lim.position.set(-18 + 30, 12 - i * 8, 0);
      world.add(lim);
      const t = label(`${r.name} ${r.value} / ${r.limit}`, "reg");
      t.position.set(-18 + Math.max(w, 6) + 12, 14 - i * 8, 0);
      world.add(t);
    });
    fit(66);
    return {};
  },

  async endpoints(sc) {
    const items = (sc.items || []).slice(0, 40);
    if (!items.length) return gapScene();
    const per = Math.ceil(Math.sqrt(items.length));
    items.forEach((it, i) => {
      const v = Math.max(0, Math.min(1, Number(it.value) <= 1 ? Number(it.value) : 1));
      const h = 1.5 + v * 11;
      const m = new THREE.Mesh(new THREE.BoxGeometry(4.2, h, 4.2),
        new THREE.MeshStandardMaterial({ color: v > 0.66 ? 0xe4574c : v > 0.33 ? 0xe9c46a : 0x7ed08a, roughness: 0.4 }));
      m.position.set(((i % per) - per / 2) * 6.4, h / 2 - 8 + (per / 2 - Math.floor(i / per)) * 16, 0);
      world.add(m);
      const t = label(it.name, "reg");
      t.position.copy(m.position).add(new THREE.Vector3(0, h / 2 + 2.4, 0));
      world.add(t);
    });
    fit(per * 12 + 24);
    return {
      focus: (f) => {
        world.children.forEach((o, i) => {
          if (!o.material || !items[i]) return;
          o.material.opacity = !f.group || items[i].group === f.group ? 1 : 0.18;
          o.material.transparent = true;
        });
      },
    };
  },

  async pk(sc) {
    const t12 = Number(sc.half_life_h) || 0, f = Math.max(0, Math.min(1, Number(sc.bioavailability) / 100));
    const pts = [];
    for (let h = 0; h <= 96; h += 1.5) {
      const c = f * (Math.exp(-0.693 * h / (t12 || 24)) - Math.exp(-h / 0.8));
      pts.push(new THREE.Vector3(h * 0.5 - 24, Math.max(0, c) * 42 - 12, 0));
    }
    world.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: 0x2dd4bf })));
    const axis = [new THREE.Vector3(-24, -12, 0), new THREE.Vector3(26, -12, 0)];
    world.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(axis),
      new THREE.LineBasicMaterial({ color: 0x2a3746 })));
    if (t12) {
      const t = label(`t½ ${t12.toFixed(1)} h`, "reg");
      t.position.set(t12 * 0.5 - 24, 6, 0); world.add(t);
    }
    fit(72);
    return {};
  },

  async complex(sc) {
    let fitTo = 80;
    if (sc.mesh) {
      const mesh = await addCartoon(sc.mesh, { grow: true, mode: "ss" });
      if (mesh) fitTo = mesh.userData.fit * 1.15;
    }
    if (sc.ligand?.length) {
      const g = new THREE.Group();
      const sph = new THREE.IcosahedronGeometry(1, 2);
      const mat = new THREE.MeshStandardMaterial({ color: 0xe9a032, roughness: 0.3, emissive: 0x3a2a08 });
      const heavy = sc.ligand.filter(a => a.e !== "H");
      const inst = new THREE.InstancedMesh(sph, mat, heavy.length);
      const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3();
      heavy.forEach((a, i) => {
        M.compose(new THREE.Vector3(a.p[0], a.p[1], a.p[2]), Q.identity(), V.setScalar(a.r * 0.42));
        inst.setMatrixAt(i, M);
      });
      g.add(inst);
      if (sc.site && typeof sc.site.center_x === "number") {
        g.position.set(sc.site.center_x, sc.site.center_y, sc.site.center_z);
      }
      world.add(g);
    }
    fit(fitTo);
    return { tick: (dt) => { world.rotation.y += dt * 0.12; } };
  },

  async binders(sc) {
    const bs = (sc.binders || []).slice(0, 12);
    if (!bs.length) return gapScene();
    bs.forEach((b, i) => {
      const p = Math.max(0, Math.min(1, Number(b.plddt) / 100));
      const h = 2 + p * 16;
      const m = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.7, h, 16),
        new THREE.MeshStandardMaterial({ color: p > 0.8 ? 0x7ed08a : p > 0.6 ? 0xe9c46a : 0xe4574c, roughness: 0.38 }));
      m.position.set((i - bs.length / 2) * 5.2, h / 2 - 8, 0);
      world.add(m);
      const t = label(`${b.id} · pLDDT ${b.plddt ?? "—"}`, "reg");
      t.position.copy(m.position).add(new THREE.Vector3(0, h / 2 + 2, 0));
      world.add(t);
    });
    fit(bs.length * 7 + 28);
    return { tick: (dt) => { world.rotation.y += dt * 0.1; } };
  },

  async score(sc) {
    const parts = (sc.parts || []).filter(p => Number(p.weighted) > 0);
    let y = -10;
    parts.forEach((p, i) => {
      const h = Math.max(0.6, Number(p.weighted) * 60);
      const m = new THREE.Mesh(new THREE.BoxGeometry(14, h, 8),
        new THREE.MeshStandardMaterial({ color: DOM_COL[i % DOM_COL.length], roughness: 0.4 }));
      m.position.set(0, y + h / 2, 0);
      world.add(m);
      const t = label(`${p.name} ${Number(p.weighted).toFixed(3)}`, "reg");
      t.position.set(12, y + h / 2 + 1.6, 0);
      world.add(t);
      y += h;
    });
    if (typeof sc.composite === "number") {
      const line = new THREE.Mesh(new THREE.BoxGeometry(24, 0.5, 9),
        new THREE.MeshStandardMaterial({ color: 0xffffff }));
      line.position.set(0, -10 + sc.composite * 60, 0);
      world.add(line);
      const t = label(`compuesta ${sc.composite}`, "reg");
      t.position.set(-16, -10 + sc.composite * 60 + 2, 0);
      world.add(t);
    }
    fit(76);
    return { tick: (dt) => { world.rotation.y = Math.sin(performance.now() / 4200) * 0.3; } };
  },

  async sequences(sc) {
    const items = (sc.items || []).filter(i => i.seq);
    if (!items.length) return gapScene();
    const AA = a => "AVLIMFWYC".includes(a) ? 0xe9a032 : "DEKRH".includes(a) ? 0x5b8def : "STNQ".includes(a) ? 0x2dd4bf : 0x7b8a9c;
    items.forEach((it, row) => {
      const g = ribbon(it.seq, { perRow: it.seq.length, cell: 2.1, colorFn: AA, y0: (items.length / 2 - row) * 5.4 });
      world.add(g);
    });
    fit(Math.max(60, (items[0].seq.length + 4) * 2.4));
    return {};
  },

  async variants(sc) {
    const vs = (sc.variants || []).filter(v => v.optimized);
    if (!vs.length) return gapScene();
    const AA = a => "AVLIMFWYC".includes(a) ? 0xe9a032 : "DEKRH".includes(a) ? 0x5b8def : "STNQ".includes(a) ? 0x2dd4bf : 0x7b8a9c;
    vs.forEach((v, row) => {
      const y = (vs.length / 2 - row) * 7.6;
      const changed = new Set((v.changes || []).map(c => c.pos - 1));
      const g = ribbon(v.optimized, {
        perRow: v.optimized.length, cell: 2.1, y0: y,
        colorFn: (a, i) => (changed.has(i) ? 0xffffff : AA(a)),
      });
      world.add(g);
      (v.changes || []).forEach(c => {
        const t = label(`${c.from}${c.pos}${c.to}`, "sig");
        t.position.copy(cellPos(g, c.pos - 1)).add(new THREE.Vector3(0, 2.6, 0));
        world.add(t);
      });
      if (typeof v.score === "number") {
        const t = label(v.score.toFixed(3), "reg");
        t.position.set((v.optimized.length / 2 + 2) * 2.1, y + 1, 0);
        world.add(t);
      }
    });
    fit(Math.max(64, (vs[0].optimized.length + 8) * 2.4));
    return {};
  },

  async ranking(sc) {
    const items = (sc.items || []).slice(0, 10);
    if (!items.length) return gapScene();
    const best = Math.max(...items.map(i => Number(i.score) || 0), 0.0001);
    items.forEach((it, i) => {
      const w = 34 * (Number(it.score) || 0) / best;
      const m = new THREE.Mesh(new THREE.BoxGeometry(Math.max(w, 0.6), 3.6, 3.6),
        new THREE.MeshStandardMaterial({ color: DOM_COL[i % DOM_COL.length], roughness: 0.4 }));
      m.position.set(-20 + w / 2, 14 - i * 7, 0);
      world.add(m);
      const t = label(`${it.rank ?? i + 1}. ${it.seq} · ${Number(it.score ?? 0).toFixed(3)}`, "reg");
      t.position.set(-20 + w + 12, 16 - i * 7, 0);
      world.add(t);
    });
    fit(items.length * 8 + 34);
    return {};
  },

  async safety(sc) { return meterScene(sc); },
  async panel(sc) { return gapScene(true); },
};

function gapScene(quiet = false) {
  const geo = new THREE.TorusKnotGeometry(9, 2.4, 140, 18);
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: quiet ? 0x33414f : 0x4a3b2a, roughness: 0.6, wireframe: true }));
  world.add(m); fit(46);
  return { tick: (dt) => { world.rotation.y += dt * 0.25; world.rotation.x += dt * 0.1; } };
}
function meterScene(sc) {
  const bars = [
    ["epítopos MHC-II / MHC-II epitopes", sc.epitopes, 200],
    ["9-mers hidrofóbicos / hydrophobic 9-mers", sc.hydrophobic, 60],
    ["accesibilidad del lazo / loop accessibility", sc.loop_accessibility, 1],
  ].filter(b => b[1] != null);
  bars.forEach((b, i) => {
    const frac = Math.max(0.02, Math.min(1, Number(b[1]) / b[2]));
    const g = new THREE.BoxGeometry(44 * frac, 4, 4);
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: frac > 0.6 ? 0xe4574c : frac > 0.3 ? 0xe9c46a : 0x7ed08a, roughness: 0.4 }));
    m.position.set(-22 + 22 * frac, 10 - i * 10, 0);
    world.add(m);
    const t = label(`${b[0].split(" / ")[S.lang === "es" ? 0 : 1]}: ${b[1]}`, "reg");
    t.position.set(0, 14 - i * 10, 0); world.add(t);
  });
  fit(70);
  return {};
}

let fly = null, lastInput = performance.now();
["pointerdown", "wheel", "keydown"].forEach(ev =>
  addEventListener(ev, () => { lastInput = performance.now(); }, { passive: true }));

function fit(size, { angle = 0.22, height = 0.18, snap = true } = {}) {
  const d = Math.max(12, size / (2 * Math.tan((camera.fov * Math.PI / 180) / 2)));
  const to = new THREE.Vector3(Math.sin(angle) * d, height * d, Math.cos(angle) * d);
  if (snap) {
    camera.position.copy(to);
    controls.target.set(0, 0, 0);
    controls.update();
    fly = null;
  } else {
    flyTo(to, new THREE.Vector3(0, 0, 0));
  }
  return d;
}

function flyTo(pos, target = new THREE.Vector3(0, 0, 0), dur = 1.8) {
  fly = { fp: camera.position.clone(), ft: controls.target.clone(),
          tp: pos.clone(), tt: target.clone(), t: 0, dur: REDUCED ? 0.001 : dur };
}

/** Frame a point of the current scene: `d` is how far back to sit from it. */
function lookAt(point, d = 40, dur = 1.8) {
  const p = new THREE.Vector3(...(Array.isArray(point) ? point : [point.x, point.y, point.z]));
  flyTo(p.clone().add(new THREE.Vector3(d * 0.34, d * 0.22, d)), p, dur);
}

/* ── chapter flow ─────────────────────────────────────────────────────── */
let active = null;
async function setChapter(i) {
  S.ch = Math.max(0, Math.min(i, R.chapters.length - 1));
  S.beat = 0;
  const ch = R.chapters[S.ch];
  clearWorld();
  world.rotation.set(0, 0, 0);
  const build = SCENES[ch.scene?.type] || (() => gapScene(true));
  active = (await build(ch.scene)) || {};
  renderChapter();
  applyBeat();
}
const T = {
  en: { measured: "measured", checked: "checked here", gap: "not measured", note: "note",
        kicker: "chapter", data: "Everything in this run", checks: "Recomputed and checked",
        annex: "Values no chapter shows", values: "values in the result", annexed: "in the annex" },
  es: { measured: "medido", checked: "comprobado aquí", gap: "sin medir", note: "nota",
        kicker: "capítulo", data: "Todo lo que trae esta corrida", checks: "Recalculado y comprobado",
        annex: "Valores que ningún capítulo muestra", values: "valores del resultado", annexed: "en el anexo" },
};

function renderChapter() {
  const ch = R.chapters[S.ch], t = T[S.lang];
  $("#kicker").textContent = `${t.kicker} ${S.ch + 1}`;
  $("#ch-title").textContent = ch.title[S.lang];
  $("#ch-index").textContent = `${S.ch + 1} / ${R.chapters.length} · ${ch.beats.length}`;
  $("#beats").innerHTML = ch.beats.map((b, i) => {
    const lab = b.kind === "check" ? t.checked : b.kind === "gap" ? t.gap : b.kind === "note" ? t.note : "";
    return `<li class="beat ${esc(b.kind)}" data-i="${i}">` +
      (lab ? `<div class="lab">${esc(lab)}</div>` : "") +
      `<div class="txt">${esc(b[S.lang])}</div>` +
      (b.paths?.length ? `<button class="src" title="${esc(b.paths.join("\n"))}">${b.paths.length}</button>` : "") +
      `</li>`;
  }).join("");
  $$("#beats .beat").forEach(el => el.onclick = () => { S.beat = +el.dataset.i; applyBeat(); });
  $$("#nav button").forEach((b, i) => {
    b.classList.toggle("on", i === S.ch);
    b.classList.toggle("gap", R.chapters[i].status === "gap");
  });
  renderBand(ch);
}

/* The band under the animation: this chapter's own figures, each drawn against the
   largest of its group so the bars mean something instead of decorating. */
function bandRows(ch) {
  const sc = ch.scene || {}, out = [];
  const push = (k, v, unit, max) => {
    if (v == null || v === "" || Number.isNaN(Number(v))) return;
    out.push({ k, v, unit: unit || "", frac: max ? Math.max(0.04, Math.min(1, Number(v) / max)) : null });
  };
  if (Array.isArray(sc.stats)) sc.stats.forEach(x => push(x[S.lang] || x.es, x.value, x.unit));
  if (sc.properties) for (const [k, v] of Object.entries(sc.properties).slice(0, 6))
    if (typeof v === "number") push(k.replace(/_/g, " "), v, "");
  if (sc.props) for (const [k, v] of Object.entries(sc.props))
    if (typeof v === "number") push(k.replace(/_/g, " "), v, "");
  if (Array.isArray(sc.regions) && sc.seq) {
    const n = sc.seq.length;
    sc.regions.forEach(r => push(r.name, r.end - r.start, "nt", n));
  }
  if (Array.isArray(sc.rules)) sc.rules.forEach(r => push(r.name, r.value, `/ ${r.limit}`, r.limit));
  if (Array.isArray(sc.parts)) {
    const m = Math.max(...sc.parts.map(p => Number(p.weighted) || 0), 0.001);
    sc.parts.forEach(p => push(p.name, Number(p.weighted).toFixed(3), "", Number(p.weighted) / m * m));
    if (sc.composite != null) push("composite", sc.composite, "", 1);
  }
  if (Array.isArray(sc.items) && sc.items.length && sc.items[0].value !== undefined)
    sc.items.slice(0, 8).forEach(i => push(i.name.replace(/_/g, " "), i.value, i.unit || "", i.value <= 1 ? 1 : null));
  if (Array.isArray(sc.items) && sc.items.length && sc.items[0].score !== undefined) {
    const m = Math.max(...sc.items.map(i => Number(i.score) || 0), 0.001);
    sc.items.slice(0, 6).forEach(i => push(i.seq || i.rank, Number(i.score).toFixed(3), "", Number(i.score) / m));
  }
  if (sc.n_qubits) { push("qubits", sc.n_qubits, ""); push("terms", sc.n_terms, ""); push("contacts", sc.n_contacts, ""); }
  if (sc.energy != null) push("VQE", Number(sc.energy).toFixed(3), "Ha",
    sc.reference ? Math.abs(Number(sc.energy) / Number(sc.reference)) : null);
  if (sc.epitopes != null) push("MHC-II epitopes", sc.epitopes, "");
  if (sc.half_life_h != null) push("half-life", Number(sc.half_life_h).toFixed(1), "h");
  if (sc.bioavailability != null) push("bioavailability", Number(sc.bioavailability).toFixed(1), "%", 100);
  if (Array.isArray(sc.binders)) {
    sc.binders.slice(0, 6).forEach(b => push(b.id, b.plddt, "pLDDT", 100));
  }
  const m = R.meshes[sc.mesh];
  if (m) { push("residues", m.n_res, ""); push("triangles", m.nt, ""); }
  return out.slice(0, 7);
}

function renderBand(ch) {
  const rows = bandRows(ch);
  $("#band").innerHTML = rows.map(r =>
    `<div class="bar"><div class="bk">${esc(r.k)}</div>` +
    `<div class="bv">${esc(r.v)}${r.unit ? `<small>${esc(r.unit)}</small>` : ""}</div>` +
    (r.frac != null ? `<div class="track"><div class="fill" style="width:${(r.frac * 100).toFixed(1)}%"></div></div>` : "") +
    `</div>`).join("");
}
function applyBeat() {
  const ch = R.chapters[S.ch], b = ch.beats[S.beat];
  $$("#beats .beat").forEach((el, i) => el.classList.toggle("on", i === S.beat));
  if (b && active?.focus) active.focus(b.focus || {});
}
function nextBeat() {
  const ch = R.chapters[S.ch];
  if (S.beat + 1 < ch.beats.length) { S.beat++; applyBeat(); }
  else if (S.ch + 1 < R.chapters.length) setChapter(S.ch + 1);
  else S.playing = false;
}

/* ── loop ─────────────────────────────────────────────────────────────── */
let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  world.children.forEach(o => {
    const g = o.userData?.grow;
    if (g && o.geometry) {
      g.t = Math.min(1, g.t + dt * 0.55);
      o.geometry.setDrawRange(0, Math.floor(g.total * 3 * g.t));
      if (g.t >= 1) delete o.userData.grow;
    }
  });
  active?.tick?.(dt);
  if (S.playing) {
    S.t += dt;
    $("#prog").style.width = `${Math.min(100, (S.t / 7.2) * 100)}%`;
    if (S.t > 7.2) { S.t = 0; nextBeat(); }
  }
  if (fly) {
    fly.t += dt / fly.dur;
    const u = Math.min(1, fly.t), e = u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
    camera.position.lerpVectors(fly.fp, fly.tp, e);
    controls.target.lerpVectors(fly.ft, fly.tt, e);
    if (u >= 1) fly = null;
  }
  controls.autoRotate = !REDUCED && !fly && now - lastInput > 7000;
  controls.autoRotateSpeed = 0.35;
  controls.update();
  composer.render();
  labels.render(scene, camera);
  requestAnimationFrame(frame);
}

/* ── chrome ───────────────────────────────────────────────────────────── */
function boot() {
  $("#title").textContent = R.title[S.lang] || "";
  $("#subject").textContent = R.subject || "";
  $("#nav").innerHTML = R.chapters.map((c, i) => `<button title="${esc(c.title[S.lang])}">${i + 1}</button>`).join("");
  $$("#nav button").forEach((b, i) => b.onclick = () => setChapter(i));
  $("#prev").onclick = () => setChapter(S.ch - 1);
  $("#next").onclick = () => nextBeat();
  $("#play").onclick = () => {
    S.playing = !S.playing; S.t = 0;
    $("#play").textContent = S.playing ? "❚❚" : "▶";
    if (!S.playing) $("#prog").style.width = "0";
  };
  $("#lang").onclick = () => { S.lang = S.lang === "es" ? "en" : "es"; boot(); setChapter(S.ch); };
  const c = R.coverage, t = T[S.lang];
  $("#coverage").textContent = `${c.leaves.toLocaleString(S.lang)} ${t.values} · ${c.annex} ${t.annexed}`;
  $("#dlg-title").textContent = t.data;
  $("#h-checks").textContent = t.checks;
  $("#h-annex").textContent = t.annex;
  $("#lang").textContent = S.lang === "es" ? "EN" : "ES";
  $("#checks").innerHTML = (R.checks || []).map(k =>
    `<li class="${k.ok ? "ok" : "bad"}">${esc(k[S.lang])}</li>`).join("");
  $("#annex").innerHTML = (R.annex || []).map(a =>
    `<tr><td>${esc(a.path)}</td><td>${esc(typeof a.value === "object" ? JSON.stringify(a.value) : a.value)}</td></tr>`).join("");
  $("#dl").onclick = () => {
    const blob = new Blob([JSON.stringify(R.result, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `bioql_${R.pipeline}_${R.digest}.json`; a.click();
  };
}
addEventListener("keydown", e => {
  if (e.key === "ArrowRight") nextBeat();
  if (e.key === "ArrowLeft") setChapter(S.ch - 1);
  if (e.key === " ") { e.preventDefault(); $("#play").click(); }
});

boot(); resize(); setChapter(0); requestAnimationFrame(frame);
