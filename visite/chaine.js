/**
 * La chaîne d'image : ce qui est fait de la scène après qu'elle est rendue.
 *
 * Trois choses, dans cet ordre. L'OCCLUSION ambiante, qui pose les volumes. Le HALO,
 * qui fait déborder les hautes lumières. L'ADOUCISSEMENT des arêtes, qui vient en
 * dernier parce qu'il travaille sur l'image finie.
 *
 * L'anti-crénelage est ici et pas sur le moteur. `antialias: true` sur le
 * WebGLRenderer ne vaut que pour le tampon d'écran, dans lequel cette chaîne n'écrit
 * jamais : la scène va dans une cible hors écran. C'est donc cette cible qui est
 * multi-échantillonnée, quatre prises par pixel pour les arêtes, les cordes et les
 * échelons. Le FXAA final reprend ce que le MSAA ne voit pas : la passe d'occlusion,
 * calculée en demi-résolution, et le disque solaire.
 *
 * OCCLUSION AMBIANTE.
 *
 * Le rendu Blender passe par le lancer de rayons d'EEVEE : un angle rentrant, un
 * dessous de corniche, le pied d'une colonne y reçoivent moins de ciel que le champ
 * du mur, et c'est cet assombrissement-là qui donne aux volumes leur assise. La
 * visite n'a rien de tel — chaque face reçoit le ciel entier, quoi qu'il y ait devant
 * elle —, et une colonne posée sur un dallage y semble collée dessus. La passe
 * ci-dessous rend cette part-là.
 *
 * Il ne lit PAS le tampon de profondeur. La visite tourne en profondeur
 * logarithmique — le plaquage d'or est posé exactement sur la pierre qu'il couvre —,
 * et une profondeur logarithmique ne se reconvertit pas en distance sans connaître
 * l'encodage exact du moteur. Une passe séparée écrit donc la normale et la distance
 * en clair, en mètres, dans une cible flottante : ce qu'on y lit ne dépend d'aucun
 * réglage du moteur.
 */
import * as THREE from "three";
import { PROFIL } from "./qualite.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";

// Douze directions par pixel, en demi-résolution : c'est la passe la plus chère de
// la visite après la géométrie. Le profil léger en garde la moitié — le flou de la
// passe suivante, qui moyenne déjà neuf voisins, en avale la différence.
const ECHANTILLONS = PROFIL.occlusion;
// Une ama et demie : l'occlusion doit dire « ce coin est un coin », pas ombrer la
// cour. Plus large, elle assombrit les murs entiers dès qu'on s'en approche.
const RAYON = 1.8;
const FORCE = 0.8;
// Le second rayon, celui du CONTACT. 1,8 m dit « ce coin est un coin » ; il ne dit rien
// du pli de trois centimètres où la contremarche rencontre le giron, où le fût pose sur
// sa base, où court le joint d'une assise. C'est ce trait fin, et lui seul, que l'œil
// lit comme « photographié » : sans lui deux surfaces qui se touchent restent deux
// aplats posés l'un contre l'autre.
const RAYON_FIN = 0.08;
const FORCE_FIN = 0.7;
// Il s'éteint bien plus tôt que l'autre, et pour deux raisons qui tombent ensemble : la
// passe est en demi-résolution, et 8 cm y valent moins d'un pixel passé quinze mètres ;
// la distance est stockée en demi-flottant, dont le pas dépasse alors le rayon lui-même.
const PORTEE_FIN = [12.0, 26.0];
// Au-delà, la distance stockée en demi-flottant devient plus grossière que le rayon
// et l'occlusion se met à clignoter sur les lointains.
const PORTEE = [45.0, 120.0];

const GEOMETRIE = new THREE.ShaderMaterial({
  vertexShader: /* glsl */`
    #include <common>
    #include <skinning_pars_vertex>
    varying vec3 vN; varying float vZ;
    void main(){
      #include <skinbase_vertex>
      #include <beginnormal_vertex>
      #include <skinnormal_vertex>
      #include <begin_vertex>
      #include <skinning_vertex>
      vec4 mv = modelViewMatrix * vec4(transformed, 1.0);
      vN = normalMatrix * objectNormal; vZ = -mv.z;
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: /* glsl */`
    varying vec3 vN; varying float vZ;
    void main(){ gl_FragColor = vec4(normalize(vN) * 0.5 + 0.5, vZ); }`,
});

const OCCLUSION = {
  uniforms: {
    tGeo: { value: null }, uTanFov: { value: 0 }, uAspect: { value: 1 },
    uRayon: { value: RAYON }, uForce: { value: FORCE },
    uRayonFin: { value: RAYON_FIN }, uForceFin: { value: FORCE_FIN },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D tGeo;
    uniform float uTanFov, uAspect, uRayon, uForce, uRayonFin, uForceFin;
    varying vec2 vUv;

    // La cible garde la distance en mètres : la position de vue s'en déduit par le
    // rayon qui traverse le pixel, sans rien savoir de la projection du moteur.
    vec3 positionVue(vec2 uv, float z){
      return vec3((uv * 2.0 - 1.0) * uTanFov * vec2(uAspect, 1.0) * z, -z);
    }

    // Ce que voit UNE prise : rien si elle sort du cadre ou tombe sur le ciel, sinon la
    // part d'horizon que la scène lui bouche, atténuée quand ce qui la bouche est trop
    // loin pour l'ombrer — sans quoi une silhouette lointaine posée devant un mur proche
    // le cercle d'un halo noir.
    float voisin(vec3 P, vec3 pas, float portee, float biais){
      vec3 S = P + pas;
      vec2 uvS = 0.5 + 0.5 * (S.xy / -S.z) / (uTanFov * vec2(uAspect, 1.0));
      if (any(lessThan(uvS, vec2(0.0))) || any(greaterThan(uvS, vec2(1.0)))) return 0.0;
      float zS = texture2D(tGeo, uvS).a;
      if (zS <= 0.0) return 0.0;
      float devant = -S.z - zS;
      return step(biais, devant) * clamp(portee / max(devant, 1e-4), 0.0, 1.0);
    }

    void main(){
      vec4 g = texture2D(tGeo, vUv);
      if (g.a <= 0.0) { gl_FragColor = vec4(1.0); return; }   // le ciel n'occlut rien
      vec3 P = positionVue(vUv, g.a);
      vec3 N = normalize(g.rgb * 2.0 - 1.0);
      // Le repère tangent est arbitraire autour de la normale : il tourne sur un motif de
      // 4 × 4 pixels, que le flou 4 × 4 de la composition moyenne exactement.
      vec3 T = normalize(abs(N.z) < 0.9 ? cross(vec3(0.0, 0.0, 1.0), N) : cross(vec3(0.0, 1.0, 0.0), N));
      vec3 B = cross(N, T);
      float tour = (mod(floor(gl_FragCoord.x), 4.0) * 4.0 + mod(floor(gl_FragCoord.y), 4.0)) / 16.0;
      // Les deux rayons partagent leurs directions : la seconde échelle ne coûte qu'une
      // prise de plus par direction, pas un second parcours de l'hémisphère.
      float occ = 0.0, occFin = 0.0;
      for (int i = 0; i < ${ECHANTILLONS}; i++) {
        float fi = float(i);
        float r = sqrt((fi + 0.5) / float(${ECHANTILLONS}));
        float ang = (fi + tour) * 2.39996;              // l'angle d'or : jamais deux fois le même secteur
        vec3 dir = T * (cos(ang) * r) + B * (sin(ang) * r) + N * sqrt(max(0.0, 1.0 - r * r));
        float ecart = 0.35 + 0.65 * r;
        occ    += voisin(P, dir * uRayon    * ecart, uRayon,    0.02);
        // Le biais suit le rayon : deux centimètres sur huit condamneraient le contact
        // avant de l'avoir cherché.
        occFin += voisin(P, dir * uRayonFin * ecart, uRayonFin, 0.004);
      }
      float ao    = 1.0 - uForce    * occ    / float(${ECHANTILLONS});
      float aoFin = 1.0 - uForceFin * occFin / float(${ECHANTILLONS});
      gl_FragColor = vec4(
        mix(ao,    1.0, smoothstep(${PORTEE[0].toFixed(1)}, ${PORTEE[1].toFixed(1)}, g.a)),
        mix(aoFin, 1.0, smoothstep(${PORTEE_FIN[0].toFixed(1)}, ${PORTEE_FIN[1].toFixed(1)}, g.a)),
        0.0, 1.0);
    }`,
};

const COMPOSITION = {
  uniforms: { tDiffuse: { value: null }, tAO: { value: null }, uPas: { value: new THREE.Vector2() } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse, tAO;
    uniform vec2 uPas;
    varying vec2 vUv;
    void main(){
      // Un tirage au hasard par pixel laisse, après neuf voisins, un grain qui marbre tout
      // ce que seul le ciel éclaire. Seize voisins couvrent le motif de rotation entier.
      // Pas de guidage par la profondeur : le débord tient dans deux texels.
      vec2 ao = vec2(0.0);
      for (int y = -2; y <= 1; y++)
        for (int x = -2; x <= 1; x++)
          ao += texture2D(tAO, vUv + vec2(float(x), float(y)) * uPas).rg;
      ao /= 16.0;
      vec4 c = texture2D(tDiffuse, vUv);
      gl_FragColor = vec4(c.rgb * ao.x * ao.y, c.a);
    }`,
};

// L'ÉTALONNAGE, en toute fin : bascule de teinte, vignettage, grain.
//
// Il travaille sur l'image AFFICHÉE, pas sur le linéaire : c'est le geste d'un
// laboratoire, pas d'un moteur, et une bascule chaud/froid appliquée avant le
// tonemapping serait mangée par la courbe d'ACES.
//
// La bascule est ce qui reste quand on a tout réglé. La lumière du soleil est chaude,
// l'ombre qu'elle laisse est FROIDE — c'est le ciel qui l'éclaire, pas lui —, et cet
// écart-là est ce qui sépare une photographie d'un rendu. Le nuanceur de matière le
// pose déjà là où il connaît les deux, la brume aussi ; ici il est posé sur la clarté,
// donc partout, y compris dans ce qu'aucun des deux ne sait.
//
// Le GRAIN, lui, ne ressemble à rien de physique dans cette scène : rien ne le produit,
// aucune source ne le demande. Il est là parce que l'ABSENCE de grain est ce qui reste
// de plus reconnaissable dans une image de synthèse — une surface parfaitement propre
// n'existe dans aucune photographie —, et il vit dans les ombres, où l'argentique et le
// capteur le mettent, jamais dans les blancs.
const ETALONNAGE = {
  uniforms: { tDiffuse: { value: null }, uTemps: { value: 0 },
              uFroid: { value: new THREE.Color(0.94, 0.97, 1.06) },
              uChaud: { value: new THREE.Color(1.05, 1.00, 0.94) },
              uVignette: { value: 0.30 }, uGrain: { value: 0.016 } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform vec3 uFroid, uChaud;
    uniform float uTemps, uVignette, uGrain;
    varying vec2 vUv;
    void main(){
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      float clair = dot(c, vec3(0.2126, 0.7152, 0.0722));
      c *= mix(uFroid, uChaud, smoothstep(0.12, 0.88, clair));

      vec2 d = vUv - 0.5;
      c *= 1.0 - uVignette * dot(d, d);

      // Le grain change à chaque image : figé, il se lit en salissure d'objectif.
      float g = fract(sin(dot(vUv + fract(uTemps), vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
      c += g * uGrain * (1.0 - clair);
      gl_FragColor = vec4(c, 1.0);
    }`,
};

/**
 * `horsGeo` : ce qui ne doit pas entrer dans la passe de géométrie. Le dôme de ciel
 * en fait partie — il enveloppe la scène, et il occluerait tout.
 */
export function chaine(renderer, scene, camera, horsGeo = []) {
  const cibleGeo = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: true });
  const cibleAO = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false });

  const teinteFond = new THREE.Color();
  const composeur = new EffectComposer(renderer,
    new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }));
  composeur.addPass(new RenderPass(scene, camera));
  const passeAO = new ShaderPass(OCCLUSION);
  passeAO.renderToScreen = false;
  const passeComposition = new ShaderPass(COMPOSITION);
  passeComposition.uniforms.tAO.value = cibleAO.texture;
  composeur.addPass(passeComposition);

  // Le halo passe AVANT la sortie, donc avant le tonemapping : la cible du composeur
  // est en demi-flottant et garde le linéaire, et c'est là seulement que le soleil sur
  // l'or vaut cinq et le calcaire à l'ombre un dixième. Après ACES tout est ramené
  // sous 1 et il n'y a plus de haute lumière à faire déborder.
  // Le seuil se lit dans ce linéaire-là : à 0,62 d'exposition, le blanc de l'écran est
  // atteint vers 2,6 — un seuil de 1,2 ne prend donc que ce qui brûle vraiment.
  const halo = PROFIL.halo && new UnrealBloomPass(
    new THREE.Vector2(1, 1), PROFIL.halo.force, PROFIL.halo.rayon, PROFIL.halo.seuil);
  if (halo) composeur.addPass(halo);
  composeur.addPass(new OutputPass());

  // Après la sortie, et pas avant : le FXAA cherche ses arêtes sur la luminance
  // perçue, celle de l'image affichée. Sur du linéaire non borné il prendrait chaque
  // reflet pour une arête et laisserait passer tout le reste.
  const arretes = new ShaderPass(FXAAShader);
  composeur.addPass(arretes);
  // Après le FXAA et pas avant : le grain posé plus tôt lui donnerait des arêtes à
  // chercher partout, et il l'effacerait en même temps.
  const etalonnage = new ShaderPass(ETALONNAGE);
  composeur.addPass(etalonnage);
  passeAO.uniforms.tGeo.value = cibleGeo.texture;

  function redimensionner(l, h) {
    const p = renderer.getPixelRatio();
    composeur.setSize(l, h);
    cibleGeo.setSize(Math.round(l * p * 0.5), Math.round(h * p * 0.5));
    cibleAO.setSize(cibleGeo.width, cibleGeo.height);
    halo?.setSize(l * p, h * p);
    arretes.material.uniforms.resolution.value.set(1 / (l * p), 1 / (h * p));
    passeComposition.uniforms.uPas.value.set(1 / cibleAO.width, 1 / cibleAO.height);
    passeAO.uniforms.uTanFov.value = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    passeAO.uniforms.uAspect.value = camera.aspect;
  }

  function rendre() {
    for (const o of horsGeo) o.visible = false;
    scene.overrideMaterial = GEOMETRIE;
    renderer.getClearColor(teinteFond);
    const alphaFond = renderer.getClearAlpha();
    // Alpha nul = pas de géométrie : c'est ainsi que la passe suivante reconnaît le
    // ciel, la distance étant stockée dans ce même canal.
    renderer.setClearColor(0x000000, 0);
    renderer.setRenderTarget(cibleGeo);
    renderer.clear();
    renderer.render(scene, camera);
    scene.overrideMaterial = null;
    renderer.setClearColor(teinteFond, alphaFond);
    for (const o of horsGeo) o.visible = true;

    etalonnage.uniforms.uTemps.value = performance.now() * 0.001;
    passeAO.render(renderer, cibleAO, null, 0, false);
    renderer.setRenderTarget(null);
    composeur.render();
  }

  return { rendre, redimensionner };
}
