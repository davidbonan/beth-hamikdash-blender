/**
 * Occlusion ambiante en espace écran.
 *
 * Le rendu Blender passe par le lancer de rayons d'EEVEE : un angle rentrant, un
 * dessous de corniche, le pied d'une colonne y reçoivent moins de ciel que le champ
 * du mur, et c'est cet assombrissement-là qui donne aux volumes leur assise. La
 * visite n'a rien de tel — chaque face reçoit le ciel entier, quoi qu'il y ait devant
 * elle —, et une colonne posée sur un dallage y semble collée dessus. Ce fichier
 * rend cette part-là, et rien d'autre.
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

// Douze directions par pixel, en demi-résolution : c'est la passe la plus chère de
// la visite après la géométrie. Le profil léger en garde la moitié — le flou de la
// passe suivante, qui moyenne déjà neuf voisins, en avale la différence.
const ECHANTILLONS = PROFIL.occlusion;
// Une ama et demie : l'occlusion doit dire « ce coin est un coin », pas ombrer la
// cour. Plus large, elle assombrit les murs entiers dès qu'on s'en approche.
const RAYON = 1.8;
const FORCE = 0.8;
// Au-delà, la distance stockée en demi-flottant devient plus grossière que le rayon
// et l'occlusion se met à clignoter sur les lointains.
const PORTEE = [45.0, 120.0];

const GEOMETRIE = new THREE.ShaderMaterial({
  vertexShader: /* glsl */`
    varying vec3 vN; varying float vZ;
    void main(){
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      vN = normalMatrix * normal; vZ = -mv.z;
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
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D tGeo;
    uniform float uTanFov, uAspect, uRayon, uForce;
    varying vec2 vUv;

    // La cible garde la distance en mètres : la position de vue s'en déduit par le
    // rayon qui traverse le pixel, sans rien savoir de la projection du moteur.
    vec3 positionVue(vec2 uv, float z){
      return vec3((uv * 2.0 - 1.0) * uTanFov * vec2(uAspect, 1.0) * z, -z);
    }
    float alea(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

    void main(){
      vec4 g = texture2D(tGeo, vUv);
      if (g.a <= 0.0) { gl_FragColor = vec4(1.0); return; }   // le ciel n'occlut rien
      vec3 P = positionVue(vUv, g.a);
      vec3 N = normalize(g.rgb * 2.0 - 1.0);
      // Le repère tangent est arbitraire autour de la normale : il est tourné par
      // pixel, ce qui échange le bruit de bande contre un bruit fin que le flou de la
      // passe suivante avale.
      vec3 T = normalize(abs(N.z) < 0.9 ? cross(vec3(0.0, 0.0, 1.0), N) : cross(vec3(0.0, 1.0, 0.0), N));
      vec3 B = cross(N, T);
      float tour = alea(gl_FragCoord.xy);
      float occ = 0.0;
      for (int i = 0; i < ${ECHANTILLONS}; i++) {
        float fi = float(i);
        float r = sqrt((fi + 0.5) / float(${ECHANTILLONS}));
        float ang = (fi + tour) * 2.39996;              // l'angle d'or : jamais deux fois le même secteur
        vec3 dir = T * (cos(ang) * r) + B * (sin(ang) * r) + N * sqrt(max(0.0, 1.0 - r * r));
        vec3 S = P + dir * uRayon * (0.35 + 0.65 * r);
        vec2 uvS = 0.5 + 0.5 * (S.xy / -S.z) / (uTanFov * vec2(uAspect, 1.0));
        if (uvS.x < 0.0 || uvS.x > 1.0 || uvS.y < 0.0 || uvS.y > 1.0) continue;
        float zS = texture2D(tGeo, uvS).a;
        if (zS <= 0.0) continue;
        float devant = -S.z - zS;                       // la scène est-elle devant l'échantillon
        // Sans cette atténuation, une silhouette lointaine posée devant un mur proche
        // le cercle d'un halo noir : elle est devant, mais bien trop loin pour l'ombrer.
        occ += step(0.02, devant) * clamp(uRayon / max(devant, 1e-4), 0.0, 1.0);
      }
      float ao = 1.0 - uForce * occ / float(${ECHANTILLONS});
      gl_FragColor = vec4(vec3(mix(ao, 1.0, smoothstep(${PORTEE[0].toFixed(1)}, ${PORTEE[1].toFixed(1)}, g.a))), 1.0);
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
      // L'occlusion est calculée en demi-résolution et bruitée par pixel : la moyenne
      // sur neuf voisins est ce qui la rend lisible. Elle n'est pas guidée par la
      // profondeur — à ce rayon, le débord tient dans deux pixels.
      float ao = 0.0;
      for (int y = -1; y <= 1; y++)
        for (int x = -1; x <= 1; x++)
          ao += texture2D(tAO, vUv + vec2(float(x), float(y)) * uPas).r;
      vec4 c = texture2D(tDiffuse, vUv);
      gl_FragColor = vec4(c.rgb * (ao / 9.0), c.a);
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
  const composeur = new EffectComposer(renderer);
  composeur.addPass(new RenderPass(scene, camera));
  const passeAO = new ShaderPass(OCCLUSION);
  passeAO.renderToScreen = false;
  const passeComposition = new ShaderPass(COMPOSITION);
  passeComposition.uniforms.tAO.value = cibleAO.texture;
  composeur.addPass(passeComposition);
  composeur.addPass(new OutputPass());
  passeAO.uniforms.tGeo.value = cibleGeo.texture;

  function redimensionner(l, h) {
    const p = renderer.getPixelRatio();
    composeur.setSize(l, h);
    cibleGeo.setSize(Math.round(l * p * 0.5), Math.round(h * p * 0.5));
    cibleAO.setSize(cibleGeo.width, cibleGeo.height);
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

    passeAO.render(renderer, cibleAO, null, 0, false);
    renderer.setRenderTarget(null);
    composeur.render();
  }

  return { rendre, redimensionner };
}
