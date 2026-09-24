// Injectée par serveur.py avant le module de la visite : ce que la page vit, rapporté au terminal.
(() => {
  const client = Math.random().toString(36).slice(2, 8);
  const ua = /iPhone|iPad/.test(navigator.userAgent) ? "ios" : /Mobile/.test(navigator.userAgent) ? "mobile" : "bureau";
  const depart = performance.now();
  const file = [];
  const noter = (type, donnees) => file.push({ client, ua, t: +((performance.now() - depart) / 1000).toFixed(2), type, ...donnees });
  const vider = () => {
    if (!file.length) return;
    const lot = file.splice(0);
    fetch("/__journal", { method: "POST", body: JSON.stringify(lot), keepalive: true }).catch(() => {});
  };
  setInterval(vider, 500);
  addEventListener("pagehide", vider);

  const texte = (v) => {
    if (v instanceof Error) return `${v.message}\n${v.stack ?? ""}`;
    if (typeof v === "object") { try { return JSON.stringify(v).slice(0, 500); } catch { return String(v); } }
    return String(v);
  };
  for (const niveau of ["log", "info", "warn", "error"]) {
    const original = console[niveau].bind(console);
    console[niveau] = (...args) => {
      noter("console", { niveau, message: args.map(texte).join(" ").slice(0, 2000) });
      original(...args);
    };
  }
  addEventListener("error", (e) => noter("erreur", { message: e.message, source: `${e.filename}:${e.lineno}:${e.colno}`,
                                                     pile: e.error?.stack?.slice(0, 2000) }));
  addEventListener("unhandledrejection", (e) => noter("rejet", { message: texte(e.reason).slice(0, 2000) }));

  // La mémoire GPU que la page réserve, estimée à chaque allocation : c'est elle qui fait perdre le contexte sur iPhone.
  const octets = { textures: 0, tampons: 0, rendus: 0 };
  const tailles = new Map();
  const compter = (famille, objet, taille, forme = "") => {
    if (!objet) return;
    octets[famille] += taille - (tailles.get(objet)?.taille ?? 0);
    tailles.set(objet, { famille, taille, forme });
  };
  const oublier = (famille, objet) => {
    if (!objet || !tailles.has(objet)) return;
    octets[famille] -= tailles.get(objet).taille;
    tailles.delete(objet);
  };
  // Les plus grosses allocations vivantes, pour savoir qui paie la mémoire.
  window.__allocations = (n = 30) => [...tailles.values()].sort((a, b) => b.taille - a.taille).slice(0, n)
    .map(({ famille, taille, forme }) => `${famille} ${(taille / 1048576).toFixed(1)} Mo ${forme}`);
  const parTexel = (gl, format) => {
    const f = {
      [gl.RGBA8]: 4, [gl.SRGB8_ALPHA8]: 4, [gl.RGBA16F]: 8, [gl.RGBA32F]: 16, [gl.R8]: 1, [gl.RG8]: 2,
      [gl.R16F]: 2, [gl.RG16F]: 4, [gl.R32F]: 4, [gl.DEPTH_COMPONENT24]: 4, [gl.DEPTH24_STENCIL8]: 4,
      [gl.DEPTH_COMPONENT16]: 2, [gl.DEPTH_COMPONENT32F]: 4, [gl.RGB8]: 4, [gl.RGBA]: 4, [gl.RGB]: 4,
    }[format];
    return f ?? 4;
  };
  let appels = 0, triangles = 0, perdu = false;
  // Ce qu'une image rendue à la main a tracé : remis à zéro par l'appel.
  window.__compter = (rendre) => {
    const a0 = appels, t0 = triangles;
    rendre();
    return { appels: appels - a0, triangles: Math.round(triangles - t0) };
  };

  function instrumenter(gl, toile) {
    if (gl.__sonde) return;
    gl.__sonde = true;
    toile.addEventListener("webglcontextlost", () => { perdu = true; noter("contexte_perdu", { ...memoire() }); vider(); });
    toile.addEventListener("webglcontextrestored", () => {
      perdu = false;
      tailles.clear();
      for (const famille in octets) octets[famille] = 0;
      noter("contexte_rendu", {});
    });
    const liee = (cible) => gl.getParameter({ [gl.TEXTURE_2D]: gl.TEXTURE_BINDING_2D, [gl.TEXTURE_CUBE_MAP]: gl.TEXTURE_BINDING_CUBE_MAP,
      [gl.TEXTURE_3D]: gl.TEXTURE_BINDING_3D, [gl.TEXTURE_2D_ARRAY]: gl.TEXTURE_BINDING_2D_ARRAY }[cible] ?? gl.TEXTURE_BINDING_2D);
    const envelopper = (nom, avant) => {
      const original = gl[nom].bind(gl);
      gl[nom] = (...args) => { avant?.(...args); return original(...args); };
      return original;
    };
    envelopper("texStorage2D", (cible, niveaux, format, l, h) => {
      const faces = cible === gl.TEXTURE_CUBE_MAP ? 6 : 1;
      compter("textures", liee(cible), l * h * parTexel(gl, format) * faces * (niveaux > 1 ? 4 / 3 : 1), `${l}x${h}x${faces} f${format} n${niveaux}`);
    });
    envelopper("texStorage3D", (cible, _niveaux, format, l, h, p) => compter("textures", liee(cible), l * h * p * parTexel(gl, format)));
    envelopper("texImage2D", (cible, niveau, format, ...reste) => {
      if (niveau !== 0) return;
      const [l, h] = typeof reste[0] === "number" ? reste : [reste[2]?.width ?? 0, reste[2]?.height ?? 0];
      const faces = cible >= gl.TEXTURE_CUBE_MAP_POSITIVE_X && cible <= gl.TEXTURE_CUBE_MAP_NEGATIVE_Z ? 6 : 1;
      const texture = liee(faces === 6 ? gl.TEXTURE_CUBE_MAP : cible);
      if (faces === 6 && cible !== gl.TEXTURE_CUBE_MAP_POSITIVE_X) return;
      compter("textures", texture, l * h * parTexel(gl, format) * faces * 4 / 3, `${l}x${h}x${faces} f${format} img`);
    });
    envelopper("deleteTexture", (t) => oublier("textures", t));
    envelopper("bufferData", (cible, taille) => {
      const liaison = cible === gl.ELEMENT_ARRAY_BUFFER ? gl.ELEMENT_ARRAY_BUFFER_BINDING
        : cible === gl.ARRAY_BUFFER ? gl.ARRAY_BUFFER_BINDING : null;
      if (liaison === null) return;
      compter("tampons", gl.getParameter(liaison), typeof taille === "number" ? taille : taille?.byteLength ?? 0, cible === gl.ELEMENT_ARRAY_BUFFER ? "index" : "sommets");
    });
    envelopper("deleteBuffer", (b) => oublier("tampons", b));
    envelopper("renderbufferStorageMultisample", (_c, prises, format, l, h) =>
      compter("rendus", gl.getParameter(gl.RENDERBUFFER_BINDING), l * h * Math.max(prises, 1) * parTexel(gl, format), `${l}x${h} x${prises} f${format}`));
    envelopper("renderbufferStorage", (_c, format, l, h) =>
      compter("rendus", gl.getParameter(gl.RENDERBUFFER_BINDING), l * h * parTexel(gl, format), `${l}x${h} f${format}`));
    envelopper("deleteRenderbuffer", (r) => oublier("rendus", r));
    envelopper("drawElements", (mode, n) => { appels++; if (mode === gl.TRIANGLES) triangles += n / 3; });
    envelopper("drawArrays", (mode, _p, n) => { appels++; if (mode === gl.TRIANGLES) triangles += n / 3; });
    envelopper("drawElementsInstanced", (mode, n, _t, _o, k) => { appels++; if (mode === gl.TRIANGLES) triangles += n / 3 * k; });
    // `?perte=<n>` : le contexte tombe au n-ième nuanceur, en pleine compilation — le crash qu'un iPhone fait au lancement.
    const perteAu = Number(new URLSearchParams(location.search).get("perte")) || Infinity;
    let nuanceurs = 0;
    const createShader = gl.createShader.bind(gl);
    gl.createShader = (type) => {
      if (++nuanceurs === perteAu) gl.getExtension("WEBGL_lose_context").loseContext();
      const s = createShader(type);
      if (!s) noter("shader_nul", { perdu: gl.isContextLost(), ...memoire() });
      return s;
    };
    // Le coût d'une image entière, GPU compris : la lecture d'un pixel attend que tout soit tracé. Médiane de `n` images.
    // Le coût d'une image en régime, GPU compris : `n` images enchaînées, puis la lecture d'un pixel d'une
    // cible à part attend que toutes soient tracées. Le plus lent de CPU et GPU fixe ce débit.
    let temoin = null;
    const attendreLeGPU = () => {
      if (!temoin) {
        const t = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, t);
        gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, 1, 1);
        temoin = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, temoin);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
      }
      gl.bindFramebuffer(gl.FRAMEBUFFER, temoin);
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4));
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    };
    window.__chrono = (n = 60) => {
      window.__rendre();
      attendreLeGPU();
      const t0 = performance.now();
      for (let i = 0; i < n; i++) window.__rendre();
      attendreLeGPU();
      return +((performance.now() - t0) / n).toFixed(2);
    };
    // Ce qu'un iPhone à court de mémoire fait subir à la page, à la demande.
    // iOS rend parfois le contexte qu'il a retiré : ce que la page devient alors se vérifie ici.
    const perte = gl.getExtension("WEBGL_lose_context");
    window.__perdreContexte = () => perte.loseContext();
    window.__restituerContexte = () => perte.restoreContext();
    noter("contexte", { version: gl.getParameter(gl.VERSION), rendu: gl.getParameter(gl.RENDERER),
                        maxTexture: gl.getParameter(gl.MAX_TEXTURE_SIZE), samples: gl.getParameter(gl.MAX_SAMPLES),
                        floatColor: !!gl.getExtension("EXT_color_buffer_float"), halfColor: !!gl.getExtension("EXT_color_buffer_half_float"),
                        floatBlend: !!gl.getExtension("EXT_float_blend"), largeur: toile.width, hauteur: toile.height, dpr: devicePixelRatio });
  }
  const getContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, ...reste) {
    const gl = getContext.call(this, type, ...reste);
    if (gl && /webgl/.test(type)) instrumenter(gl, this);
    return gl;
  };
  const mo = (n) => +(n / 1048576).toFixed(1);
  const memoire = () => ({ texturesMo: mo(octets.textures), tamponsMo: mo(octets.tampons), rendusMo: mo(octets.rendus),
                           totalMo: mo(octets.textures + octets.tampons + octets.rendus) });

  // Le rythme : chaque intervalle entre deux images, résumé toutes les deux secondes.
  let durees = [], derniere = performance.now(), appelsParImage = [], trianglesParImage = [];
  const image = (maintenant) => {
    durees.push(maintenant - derniere);
    derniere = maintenant;
    appelsParImage.push(appels);
    trianglesParImage.push(triangles);
    appels = 0;
    triangles = 0;
    requestAnimationFrame(image);
  };
  requestAnimationFrame(image);
  const quantile = (t, q) => t.length ? t[Math.min(t.length - 1, Math.floor(q * t.length))] : 0;
  const moyenne = (t) => t.length ? t.reduce((a, b) => a + b, 0) / t.length : 0;
  window.__rythme = [];
  setInterval(() => {
    if (!durees.length) return;
    const tri = [...durees].sort((a, b) => a - b);
    const etat = (() => { try { return window.__etat?.(); } catch { return null; } })();
    const mesure = {
      ips: +(1000 / moyenne(durees)).toFixed(1), p50: +quantile(tri, 0.5).toFixed(1), p95: +quantile(tri, 0.95).toFixed(1),
      max: +tri[tri.length - 1].toFixed(1), saccades: durees.filter((d) => d > 50).length,
      appels: Math.round(moyenne(appelsParImage)), triangles: Math.round(moyenne(trianglesParImage)),
      ...memoire(), perdu, echelle: etat?.echelle, lieu: etat?.lieu, pret: !!window.__pret,
    };
    window.__rythme.push(mesure);
    noter("rythme", mesure);
    durees = []; appelsParImage = []; trianglesParImage = [];
  }, 2000);

  // Ce que ordre.py demande : un corps de fonction asynchrone, dont le retour revient au terminal.
  const Asynchrone = Object.getPrototypeOf(async () => {}).constructor;
  async function ecouter() {
    for (;;) {
      try {
        const r = await fetch(`/__ordre?client=${client}&ua=${ua}`);
        if (r.status !== 200) continue;
        const { id, code } = await r.json();
        let resultat, erreur;
        try { resultat = await new Asynchrone(code)(); } catch (e) { erreur = texte(e); }
        await fetch("/__resultat", { method: "POST", body: JSON.stringify({ id, resultat, erreur }) });
      } catch {
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }
  ecouter();
  noter("demarrage", { url: location.href, navigateur: navigator.userAgent, ecran: `${innerWidth}x${innerHeight}@${devicePixelRatio}` });
})();
