// Un dallage reflète ce qui l'entoure, pas seulement le ciel : la scène rendue une seconde fois, en miroir sous le sol où l'œil se tient.
import * as THREE from "three";
import { FullScreenQuad } from "three/addons/postprocessing/Pass.js";
import { PROFIL } from "./qualite.js";

const AFFLEUREMENT = 0.01;   // m : le sol lui-même n'entre pas dans son reflet
const FOND = 150;            // m : la cour et ce qui la borde, pas la ville
const ABORDS = 2;            // m : les murs de la cour débordent de son emprise
// Le miroir ne trace que ce qui porte le calque de son dallage : il coûte par dessin, pas par pixel.
const PREMIER_CALQUE = 2;
const NIVEAUX_DE_FLOU = 6;

export const REFLET = {
  tReflet: { value: null },
  uVersReflet: { value: new THREE.Matrix4() },
  tProfondeurReflet: { value: null },
  uDeReflet: { value: new THREE.Matrix4() },
  uTexelReflet: { value: new THREE.Vector2(1, 1) },
  uFocaleReflet: { value: 1 },
  uRefletActif: { value: 0 },
  uCoteReflet: { value: 0 },
  uLobeReflet: { value: 0 },
  uForceReflet: { value: 0 },
};

// Pierre polie par les pas, pas glacée : le reflet s'étale avec la rugosité et la hauteur de ce qu'il montre, plus en long qu'en large.
export const LECTURE_DU_REFLET = /* glsl */`
#ifdef REFLET_DU_DALLAGE
uniform sampler2D tReflet, tProfondeurReflet;
uniform mat4 uVersReflet, uDeReflet;
uniform vec2 uTexelReflet;
uniform float uFocaleReflet, uRefletActif, uCoteReflet, uLobeReflet, uForceReflet;
const float TORSION = 0.03, FLOU_MAX = ${NIVEAUX_DE_FLOU.toFixed(1)}, ETIREMENT = 1.4;
// rgb : la cour vue d'en dessous du dallage ; a : 1 où il y a de la pierre, 0 où c'est le ciel, que l'environnement garde.
float refleterLaCour(inout vec3 radiance, vec3 P, vec3 nPlan, vec3 nVue, float rugosite) {
  if (uRefletActif < 0.5 || nPlan.y < 0.95 || abs(P.y - uCoteReflet) > 0.02) return 0.0;
  vec4 q = uVersReflet * vec4(P, 1.0);
  vec3 nMonde = inverseTransformDirection(nVue, viewMatrix);
  vec2 uv = q.xy / q.w + nMonde.xz * TORSION;
  vec4 vu = uDeReflet * vec4(uv * 2.0 - 1.0, texture(tProfondeurReflet, uv).r * 2.0 - 1.0, 1.0);
  float apres = distance(vu.xyz / vu.w, P), avant = distance(P, cameraPosition);
  float etale = uFocaleReflet * uLobeReflet * rugosite * rugosite * apres / (avant + apres);
  float flou = clamp(log2(max(etale, 1.0)), 0.0, FLOU_MAX);
  float pas = ETIREMENT * exp2(flou) * uTexelReflet.y;
  vec4 somme = vec4(0.0);
  for (int i = -3; i <= 3; i++) somme += exp(-0.18 * float(i * i)) * textureLod(tReflet, uv + vec2(0.0, float(i) * pas), flou);
  somme /= 4.17;
  vec2 bord = smoothstep(vec2(0.0), vec2(0.04), uv) * smoothstep(vec2(0.0), vec2(0.04), 1.0 - uv);
  float couvert = clamp(somme.a, 0.0, 1.0) * bord.x * bord.y * uForceReflet;
  radiance = mix(radiance, somme.rgb / max(somme.a, 1e-3), couvert);
  return couvert;
}
#endif
`;

const SANS_REFLET = { confier() {}, confierMobiles() {}, rendre() {}, redimensionner() {}, allumer() {} };

// Changer de matière à chaque dessin est ce que le miroir coûtait : flou, il n'en garde qu'une poignée, une par teinte voisine.
const ECART_DE_TEINTE = 0.12;

function teintesMoyennes() {
  const pixel = Object.assign(document.createElement("canvas"), { width: 1, height: 1 }).getContext("2d", { willReadFrequently: true });
  return ({ color, map }) => {
    if (!map) return color.clone();
    pixel.drawImage(map.image, 0, 0, 1, 1);
    const [r, v, b] = pixel.getImageData(0, 0, 1, 1).data;
    return new THREE.Color().setRGB(r / 255, v / 255, b / 255, THREE.SRGBColorSpace).multiply(color);
  };
}

// Ce qui reflète sa salle et non le ciel garde ce reflet, que la sonde peut refaire, et sa lumière cuite : dehors le ciel éclaire, pas dedans.
const SOUS_LE_CIEL = {};
const salleDe = ({ envMap, envMapIntensity, lightMap, lightMapIntensity }) => (envMap ? { envMap, envMapIntensity, lightMap, lightMapIntensity } : SOUS_LE_CIEL);

function matieresEpurees(teinteDe) {
  const epures = [];
  const epureDe = new WeakMap();

  function epurer(maillage) {
    const vraie = maillage.material;
    const { roughness, metalness, emissive, emissiveIntensity, side } = vraie;
    const salle = salleDe(vraie);
    const teinte = teinteDe(vraie);
    const trait = { os: maillage.isSkinnedMesh === true, metal: metalness > 0.5, side, lueur: emissive.getHex() * emissiveIntensity, reflet: salle.envMap, cuite: salle.lightMap };
    const voisine = epures.find((e) => Object.keys(trait).every((cle) => e.trait[cle] === trait[cle])
      && Math.hypot(e.teinte.r - teinte.r, e.teinte.g - teinte.g, e.teinte.b - teinte.b) < ECART_DE_TEINTE);
    if (voisine) return voisine.materiau;
    const materiau = new THREE.MeshStandardMaterial({ color: teinte, roughness, metalness, emissive, emissiveIntensity, side, ...salle });
    epures.push({ trait, teinte, materiau });
    return materiau;
  }

  return (maillage) => {
    const vraie = maillage.material;
    if (!vraie.isMeshStandardMaterial) return vraie;
    if (!epureDe.has(vraie)) epureDe.set(vraie, epurer(maillage));
    return Object.assign(epureDe.get(vraie), salleDe(vraie));
  };
}

// Flou, le reflet d'une cour ne garde du décor que sa teinte et sa lumière : il se trace d'une seule matière, la teinte portée par les sommets.
// C'est le nombre de matières qui coûtait ce tracé, pas ses pixels : passé une douzaine, une image manquée sur cinq en rétina dans l'Azara.
const TEINTE = "color";

function matieresUnies(teinteDe, epure) {
  const unies = new Map();
  const teintes = new WeakSet();
  const unie = (side) => unies.get(side) ?? unies.set(side, new THREE.MeshStandardMaterial({ vertexColors: true, side })).get(side);
  const luit = ({ emissive, emissiveIntensity }) => emissive.getHex() * emissiveIntensity > 0;
  // Ce qui luit, ce qui bouge par ses os et ce qui n'a pas reçu ses sommets garde sa matière épurée.
  const seTeint = ({ isSkinnedMesh, material, geometry }) => !isSkinnedMesh && material.isMeshStandardMaterial && !luit(material) && geometry.hasAttribute(TEINTE);

  function teindre({ geometry, material }) {
    const { r, g, b } = teinteDe(material);
    const sommets = geometry.getAttribute(TEINTE);
    for (let i = 0; i < sommets.count; i++) sommets.setXYZW(i, r, g, b, 1);
    sommets.needsUpdate = true;
    teintes.add(geometry);
  }

  return {
    // Quatre octets par sommet : Metal n'aligne pas un attribut de trois.
    preparer({ isSkinnedMesh, geometry }) {
      if (isSkinnedMesh || geometry.hasAttribute(TEINTE)) return;
      geometry.setAttribute(TEINTE, new THREE.BufferAttribute(new Uint8Array(geometry.getAttribute("position").count * 4), 4, true));
    },
    vetir(maillage) {
      if (!seTeint(maillage)) return epure(maillage);
      if (!teintes.has(maillage.geometry)) teindre(maillage);
      return unie(maillage.material.side);
    },
  };
}

// Quatre prises bilinéaires à 0,75 texel, un noyau 1-3-3-1 : sous les mipmaps du GPU, réduits en boîte, un reflet flou avançait par crans quand le décor glissait.
const PRISE = 0.75;

// Une texture ne se lit pas pendant qu'elle se trace : chaque niveau de la pyramide lue se réduit depuis celle de relais, et inversement.
function pyramideDeFlou(renderer) {
  const etage = () => new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType, depthBuffer: false, minFilter: THREE.LinearMipmapLinearFilter });
  const lue = etage(), relais = etage();
  const reduction = new FullScreenQuad(new THREE.ShaderMaterial({
    uniforms: { tSource: { value: null }, uNiveau: { value: 0 }, uPrise: { value: new THREE.Vector2() } },
    vertexShader: /* glsl */`
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tSource;
      uniform float uNiveau;
      uniform vec2 uPrise;
      varying vec2 vUv;
      void main() {
        vec2 croix = vec2(uPrise.x, -uPrise.y);
        gl_FragColor = 0.25 * (textureLod(tSource, vUv + uPrise, uNiveau) + textureLod(tSource, vUv - uPrise, uNiveau)
          + textureLod(tSource, vUv + croix, uNiveau) + textureLod(tSource, vUv - croix, uNiveau));
      }`,
    depthTest: false, depthWrite: false,
  }));

  function tracer({ cible, niveau, source, lu, prise }) {
    const { tSource, uNiveau, uPrise } = reduction.material.uniforms;
    tSource.value = source.texture;
    uNiveau.value = lu;
    uPrise.value.set(prise / Math.max(1, source.width >> lu), prise / Math.max(1, source.height >> lu));
    cible.viewport.set(0, 0, Math.max(1, cible.width >> niveau), Math.max(1, cible.height >> niveau));
    renderer.setRenderTarget(cible, 0, niveau);
    reduction.render(renderer);
  }

  return {
    texture: lue.texture,
    redimensionner(largeur, hauteur) {
      for (const cible of [lue, relais]) {
        cible.setSize(largeur, hauteur);
        // three trace dans un niveau dès que `mipmaps` les compte, et la texture ne se lit que si toute la chaîne existe.
        cible.texture.mipmaps = Array(Math.floor(Math.log2(Math.max(largeur, hauteur))) + 1).fill({});
      }
    },
    flouter(miroir) {
      tracer({ cible: lue, niveau: 0, source: miroir, lu: 0, prise: 0 });
      for (const cible of [lue, relais]) tracer({ cible, niveau: 1, source: miroir, lu: 0, prise: PRISE });
      for (let niveau = 2; niveau <= NIVEAUX_DE_FLOU; niveau++) {
        tracer({ cible: lue, niveau, source: relais, lu: niveau - 1, prise: PRISE });
        if (niveau < NIVEAUX_DE_FLOU) tracer({ cible: relais, niveau, source: lue, lu: niveau - 1, prise: PRISE });
      }
    },
  };
}

// `cour` : là où l'œil voit ce dallage, hors de ses `salles`. `clos` : le volume dont rien ne se voit de la cour. `lobe` : l'étalement du reflet ; `force` : sa part dans ce que le sol renvoie.
// `uni` : le reflet est assez flou pour se tracer d'une seule matière.
export function refleterLesDallages(renderer, scene, camera, { dallages, caches }) {
  if (!PROFIL.reflets) return SANS_REFLET;
  const { definition } = PROFIL.reflets;
  const cible = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthTexture: new THREE.DepthTexture(1, 1) });
  const flou = pyramideDeFlou(renderer);
  const miroir = new THREE.PerspectiveCamera();
  const teinteDe = teintesMoyennes();
  const epure = matieresEpurees(teinteDe);
  const unies = matieresUnies(teinteDe, epure);
  const plans = dallages.map(({ cote, lobe, force, uni = false, cour, salles = [], clos = new THREE.Box3() }, rang) => ({
    cote, lobe, force, uni, cour, salles, clos,
    vetir: uni ? unies.vetir : epure,
    calque: PREMIER_CALQUE + rang,
    auDessus: new THREE.Box3(
      new THREE.Vector3(cour.min.x - ABORDS, cote, cour.min.z - ABORDS), new THREE.Vector3(cour.max.x + ABORDS, Infinity, cour.max.z + ABORDS)),
    refletes: [],
  }));
  const volume = new THREE.Box3();
  const seVoitDe = (plan) => (maillage) => {
    volume.setFromObject(maillage);
    return plan.auDessus.intersectsBox(volume) && !plan.clos.containsBox(volume);
  };
  const normale = new THREE.Vector3(0, 1, 0);
  const planDuSol = new THREE.Plane();
  const rotation = new THREE.Matrix4();
  const oeil = new THREE.Vector3();
  const vise = new THREE.Vector3();
  const coupe = new THREE.Vector4();
  const q = new THREE.Vector4();
  const fond = new THREE.Color();
  const BIAIS = new THREE.Matrix4().set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1);

  const voitLOeil = ({ cote, cour, salles }) => camera.position.y > cote && cour.containsPoint(camera.position)
    && !salles.some((salle) => salle.containsPoint(camera.position));

  function poserLeMiroir({ cote, lobe, force }) {
    camera.getWorldPosition(oeil);
    rotation.extractRotation(camera.matrixWorld);
    vise.set(0, 0, -1).applyMatrix4(rotation).add(oeil);
    miroir.position.set(oeil.x, 2 * cote - oeil.y, oeil.z);
    vise.y = 2 * cote - vise.y;
    miroir.up.set(0, 1, 0).applyMatrix4(rotation).reflect(normale);
    miroir.lookAt(vise);
    miroir.near = camera.near;
    miroir.far = FOND;
    miroir.fov = camera.fov;
    miroir.aspect = camera.aspect;
    miroir.updateProjectionMatrix();
    miroir.updateMatrixWorld();
    REFLET.uVersReflet.value.copy(BIAIS).multiply(miroir.projectionMatrix).multiply(miroir.matrixWorldInverse);

    // Plan de coupe oblique (Lengyel) : ce qui est sous le dallage ne se reflète pas.
    planDuSol.setFromNormalAndCoplanarPoint(normale, vise.set(0, cote + AFFLEUREMENT, 0)).applyMatrix4(miroir.matrixWorldInverse);
    coupe.set(planDuSol.normal.x, planDuSol.normal.y, planDuSol.normal.z, planDuSol.constant);
    const p = miroir.projectionMatrix.elements;
    q.set((Math.sign(coupe.x) + p[8]) / p[0], (Math.sign(coupe.y) + p[9]) / p[5], -1, (1 + p[10]) / p[14]);
    coupe.multiplyScalar(2 / coupe.dot(q));
    p[2] = coupe.x; p[6] = coupe.y; p[10] = coupe.z + 1; p[14] = coupe.w;
    miroir.projectionMatrixInverse.copy(miroir.projectionMatrix).invert();
    REFLET.uDeReflet.value.copy(miroir.matrixWorld).multiply(miroir.projectionMatrixInverse);
    REFLET.uCoteReflet.value = cote;
    REFLET.uLobeReflet.value = lobe;
    REFLET.uForceReflet.value = force;
  }

  function tracer(plan) {
    const { calque, refletes, vetir } = plan;
    poserLeMiroir(plan);
    miroir.layers.set(calque);
    // Une lampe hors du calque manquerait au miroir, et chaque matière se recompilerait pour son compte de lampes.
    scene.traverse((o) => { if (o.isLight) o.layers.enable(calque); });
    const visibles = caches.map((o) => o.visible);
    caches.forEach((o) => { o.visible = false; });
    renderer.getClearColor(fond);
    const alpha = renderer.getClearAlpha();
    const avant = renderer.getRenderTarget();
    // Les ombres se tracent avec l'image de l'œil : tracées ici, elles ne verraient que les objets du calque.
    const ombresSuivies = renderer.shadowMap.autoUpdate;
    const matieres = refletes.map((maillage) => maillage.material);
    try {
      refletes.forEach((maillage) => { maillage.material = vetir(maillage); });
      renderer.setClearColor(0x000000, 0);
      renderer.setRenderTarget(cible);
      renderer.clear();
      renderer.shadowMap.autoUpdate = false;
      renderer.render(scene, miroir);
      flou.flouter(cible);
    } finally {
      renderer.shadowMap.autoUpdate = ombresSuivies;
      renderer.setRenderTarget(avant);
      renderer.setClearColor(fond, alpha);
      caches.forEach((o, i) => { o.visible = visibles[i]; });
      refletes.forEach((maillage, i) => { maillage.material = matieres[i]; });
    }
  }

  let allume = true;
  function rendre() {
    const plan = allume ? plans.find(voitLOeil) ?? null : null;
    REFLET.uRefletActif.value = plan ? 1 : 0;
    if (plan) tracer(plan);
  }

  function redimensionner(largeur, hauteur) {
    cible.setSize(Math.max(1, Math.round(largeur * definition)), Math.max(1, Math.round(hauteur * definition)));
    // three ne retaille la profondeur qu'au tracé du miroir : lue d'abord par le sol, miroir éteint, elle naissait à l'ancienne taille et la cible restait incomplète.
    Object.assign(cible.depthTexture.image, { width: cible.width, height: cible.height });
    flou.redimensionner(cible.width, cible.height);
    REFLET.uTexelReflet.value.set(1 / cible.width, 1 / cible.height);
    REFLET.uFocaleReflet.value = cible.height / 2 / Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  }

  REFLET.tReflet.value = flou.texture;
  REFLET.tProfondeurReflet.value = cible.depthTexture;
  // Cheveux et barbes sont des cartes découpées : épurées elles feraient des plaques, et le flou ne les montre pas.
  const decoupe = ({ material }) => material.isMeshStandardMaterial && (material.transparent || material.alphaTest > 0);
  const refleterSur = ({ calque, refletes, uni }) => (maillage) => {
    if (decoupe(maillage)) return;
    if (uni) unies.preparer(maillage);
    maillage.layers.enable(calque);
    refletes.push(maillage);
  };

  return {
    rendre, redimensionner,
    allumer(voulu) { allume = voulu; },
    // À confier avant les niveaux de détail, dont les tuiles prennent les calques et les attributs de leur maillage et lisent sa matière.
    confier(maillages) {
      for (const plan of plans) maillages.filter(seVoitDe(plan)).forEach(refleterSur(plan));
    },
    confierMobiles(maillages) {
      for (const plan of plans) maillages.forEach(refleterSur(plan));
    },
  };
}
