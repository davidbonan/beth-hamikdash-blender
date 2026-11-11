// Le dallage de l'Azara reflète la cour, pas seulement le ciel : la scène rendue une seconde fois, en miroir sous le sol.
import * as THREE from "three";
import { PROFIL } from "./qualite.js";

const COTE = 0;              // m : le dallage de l'Azara
const AFFLEUREMENT = 0.01;   // m : le sol lui-même n'entre pas dans son reflet
const FOND = 150;            // m : la cour et ce qui la borde, pas la ville
const ABORDS = 2;            // m : les murs de la cour débordent de son emprise
// Le miroir ne trace que ce qui porte ce calque : il coûte par dessin, pas par pixel.
const CALQUE_REFLETE = 2;
// Le reflet garde la matrice de l'image où il a été tracé : d'une image à l'autre il reste juste dans le monde, à la parallaxe d'un pas près.
const UNE_IMAGE_SUR = 2;

export const REFLET = {
  tReflet: { value: null },
  uVersReflet: { value: new THREE.Matrix4() },
  tProfondeurReflet: { value: null },
  uDeReflet: { value: new THREE.Matrix4() },
  uTexelReflet: { value: new THREE.Vector2(1, 1) },
  uFocaleReflet: { value: 1 },
  uRefletActif: { value: 0 },
};

// Pierre polie par les pas, pas glacée : le reflet s'étale avec la rugosité et la hauteur de ce qu'il montre, plus en long qu'en large.
export const LECTURE_DU_REFLET = /* glsl */`
#ifdef REFLET_DU_DALLAGE
uniform sampler2D tReflet, tProfondeurReflet;
uniform mat4 uVersReflet, uDeReflet;
uniform vec2 uTexelReflet;
uniform float uFocaleReflet, uRefletActif;
const float LOBE = 0.15, TORSION = 0.03, FLOU_MAX = 6.0, ETIREMENT = 1.4;
// rgb : la cour vue d'en dessous du dallage ; a : 1 où il y a de la pierre, 0 où c'est le ciel, que l'environnement garde.
float refleterLaCour(inout vec3 radiance, vec3 P, vec3 nPlan, vec3 nVue, float rugosite) {
  if (uRefletActif < 0.5 || nPlan.y < 0.95 || abs(P.y - ${COTE.toFixed(3)}) > 0.02) return 0.0;
  vec4 q = uVersReflet * vec4(P, 1.0);
  vec3 nMonde = inverseTransformDirection(nVue, viewMatrix);
  vec2 uv = q.xy / q.w + nMonde.xz * TORSION;
  vec4 vu = uDeReflet * vec4(uv * 2.0 - 1.0, texture(tProfondeurReflet, uv).r * 2.0 - 1.0, 1.0);
  float apres = distance(vu.xyz / vu.w, P), avant = distance(P, cameraPosition);
  float etale = uFocaleReflet * LOBE * rugosite * rugosite * apres / (avant + apres);
  float flou = clamp(log2(max(etale, 1.0)), 0.0, FLOU_MAX);
  float pas = ETIREMENT * exp2(flou) * uTexelReflet.y;
  vec4 somme = vec4(0.0);
  for (int i = -3; i <= 3; i++) somme += exp(-0.18 * float(i * i)) * textureLod(tReflet, uv + vec2(0.0, float(i) * pas), flou);
  somme /= 4.17;
  vec2 bord = smoothstep(vec2(0.0), vec2(0.04), uv) * smoothstep(vec2(0.0), vec2(0.04), 1.0 - uv);
  float couvert = clamp(somme.a, 0.0, 1.0) * bord.x * bord.y;
  radiance = mix(radiance, somme.rgb / max(somme.a, 1e-3), couvert);
  return couvert;
}
#endif
`;

const SANS_REFLET = { confier() {}, confierMobiles() {}, rendre() {}, redimensionner() {}, allumer() {} };

// Changer de matière à chaque dessin est ce que le miroir coûtait : flou, il n'en garde qu'une poignée, une par teinte voisine.
const ECART_DE_TEINTE = 0.12;

function matieresEpurees() {
  const epures = [];
  const epureDe = new WeakMap();
  const pixel = Object.assign(document.createElement("canvas"), { width: 1, height: 1 }).getContext("2d", { willReadFrequently: true });

  function teinteMoyenne(carte) {
    pixel.drawImage(carte.image, 0, 0, 1, 1);
    const [r, v, b] = pixel.getImageData(0, 0, 1, 1).data;
    return new THREE.Color().setRGB(r / 255, v / 255, b / 255, THREE.SRGBColorSpace);
  }

  function epurer(maillage) {
    const { color, map, roughness, metalness, emissive, emissiveIntensity, side } = maillage.material;
    const teinte = map ? teinteMoyenne(map).multiply(color) : color.clone();
    const trait = { os: maillage.isSkinnedMesh === true, metal: metalness > 0.5, side, lueur: emissive.getHex() * emissiveIntensity };
    const voisine = epures.find((e) => e.os === trait.os && e.metal === trait.metal && e.side === side && e.lueur === trait.lueur
      && Math.hypot(e.teinte.r - teinte.r, e.teinte.g - teinte.g, e.teinte.b - teinte.b) < ECART_DE_TEINTE);
    if (voisine) return voisine.materiau;
    const materiau = new THREE.MeshStandardMaterial({ color: teinte, roughness, metalness, emissive, emissiveIntensity, side });
    epures.push({ ...trait, teinte, materiau });
    return materiau;
  }

  return (maillage) => {
    const vraie = maillage.material;
    if (!vraie.isMeshStandardMaterial) return vraie;
    if (!epureDe.has(vraie)) epureDe.set(vraie, epurer(maillage));
    return epureDe.get(vraie);
  };
}

// `salles` : là où l'œil n'est plus dans la cour. `clos` : le volume dont rien ne se voit de la cour.
export function refleterLeDallage(renderer, scene, camera, { cour, salles, clos, caches }) {
  if (!PROFIL.reflets) return SANS_REFLET;
  const { definition } = PROFIL.reflets;
  const cible = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter,
    depthTexture: new THREE.DepthTexture(1, 1),
  });
  const miroir = new THREE.PerspectiveCamera();
  miroir.layers.set(CALQUE_REFLETE);
  const auDessusDuDallage = new THREE.Box3(
    new THREE.Vector3(cour.min.x - ABORDS, COTE, cour.min.z - ABORDS), new THREE.Vector3(cour.max.x + ABORDS, Infinity, cour.max.z + ABORDS));
  const volume = new THREE.Box3();
  const seVoitDeLaCour = (maillage) => {
    volume.setFromObject(maillage);
    return auDessusDuDallage.intersectsBox(volume) && !clos.containsBox(volume);
  };
  const normale = new THREE.Vector3(0, 1, 0);
  const plan = new THREE.Plane();
  const rotation = new THREE.Matrix4();
  const oeil = new THREE.Vector3();
  const vise = new THREE.Vector3();
  const coupe = new THREE.Vector4();
  const q = new THREE.Vector4();
  const fond = new THREE.Color();
  const BIAIS = new THREE.Matrix4().set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1);
  const refletes = [];
  const epure = matieresEpurees();

  const dansLaCour = (p) => p.y > COTE && cour.containsPoint(p) && !salles.some((s) => s.containsPoint(p));

  function poserLeMiroir() {
    camera.getWorldPosition(oeil);
    rotation.extractRotation(camera.matrixWorld);
    vise.set(0, 0, -1).applyMatrix4(rotation).add(oeil);
    miroir.position.set(oeil.x, 2 * COTE - oeil.y, oeil.z);
    vise.y = 2 * COTE - vise.y;
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
    plan.setFromNormalAndCoplanarPoint(normale, vise.set(0, COTE + AFFLEUREMENT, 0)).applyMatrix4(miroir.matrixWorldInverse);
    coupe.set(plan.normal.x, plan.normal.y, plan.normal.z, plan.constant);
    const p = miroir.projectionMatrix.elements;
    q.set((Math.sign(coupe.x) + p[8]) / p[0], (Math.sign(coupe.y) + p[9]) / p[5], -1, (1 + p[10]) / p[14]);
    coupe.multiplyScalar(2 / coupe.dot(q));
    p[2] = coupe.x; p[6] = coupe.y; p[10] = coupe.z + 1; p[14] = coupe.w;
    miroir.projectionMatrixInverse.copy(miroir.projectionMatrix).invert();
    REFLET.uDeReflet.value.copy(miroir.matrixWorld).multiply(miroir.projectionMatrixInverse);
  }

  function tracer() {
    poserLeMiroir();
    // Une lampe hors du calque manquerait au miroir, et chaque matière se recompilerait pour son compte de lampes.
    scene.traverse((o) => { if (o.isLight) o.layers.enable(CALQUE_REFLETE); });
    const visibles = caches.map((o) => o.visible);
    caches.forEach((o) => { o.visible = false; });
    renderer.getClearColor(fond);
    const alpha = renderer.getClearAlpha();
    const avant = renderer.getRenderTarget();
    // Les ombres se tracent avec l'image de l'œil : tracées ici, elles ne verraient que les objets du calque.
    const ombresSuivies = renderer.shadowMap.autoUpdate;
    const matieres = refletes.map((maillage) => maillage.material);
    try {
      refletes.forEach((maillage) => { maillage.material = epure(maillage); });
      renderer.setClearColor(0x000000, 0);
      renderer.setRenderTarget(cible);
      renderer.clear();
      renderer.shadowMap.autoUpdate = false;
      renderer.render(scene, miroir);
    } finally {
      renderer.shadowMap.autoUpdate = ombresSuivies;
      renderer.setRenderTarget(avant);
      renderer.setClearColor(fond, alpha);
      caches.forEach((o, i) => { o.visible = visibles[i]; });
      refletes.forEach((maillage, i) => { maillage.material = matieres[i]; });
    }
  }

  let allume = true, images = 0;
  function rendre() {
    const voulu = allume && dansLaCour(camera.position);
    REFLET.uRefletActif.value = voulu ? 1 : 0;
    if (!voulu) images = 0;
    else if (images++ % UNE_IMAGE_SUR === 0) tracer();
  }

  function redimensionner(largeur, hauteur) {
    cible.setSize(Math.max(1, Math.round(largeur * definition)), Math.max(1, Math.round(hauteur * definition)));
    REFLET.uTexelReflet.value.set(1 / cible.width, 1 / cible.height);
    REFLET.uFocaleReflet.value = cible.height / 2 / Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    images = 0;
  }

  REFLET.tReflet.value = cible.texture;
  REFLET.tProfondeurReflet.value = cible.depthTexture;
  // Cheveux et barbes sont des cartes découpées : épurées elles feraient des plaques, et le flou ne les montre pas.
  const decoupe = ({ material }) => material.isMeshStandardMaterial && (material.transparent || material.alphaTest > 0);
  const refleter = (maillage) => {
    if (decoupe(maillage)) return;
    maillage.layers.enable(CALQUE_REFLETE);
    refletes.push(maillage);
  };

  return {
    rendre, redimensionner,
    allumer(voulu) { allume = voulu; },
    // À confier avant les niveaux de détail, dont les tuiles prennent les calques de leur maillage et lisent sa matière.
    confier(maillages) {
      maillages.filter(seVoitDeLaCour).forEach(refleter);
    },
    confierMobiles(maillages) { maillages.forEach(refleter); },
  };
}
