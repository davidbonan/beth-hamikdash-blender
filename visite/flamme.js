import * as THREE from "three";

// Une flamme d'huile d'olive sur mèche de lin : quatre centimètres, le pied bleu, le coeur
// blanc, le manteau orangé qui s'efface vers la pointe. Additive, sans profondeur écrite.
const PROFIL_FLAMME = [[0, -0.003], [0.0035, 0.0], [0.0068, 0.007], [0.0075, 0.013],
                       [0.0062, 0.022], [0.0034, 0.032], [0.0008, 0.04], [0, 0.043]]
  .map(([r, y]) => new THREE.Vector2(r, y));
const HAUTEUR_FLAMME = 0.043;
const FORME = new THREE.LatheGeometry(PROFIL_FLAMME, 16);
export const TEMPS_FLAMME = { value: 0 };

function materiauFlamme(phase) {
  return new THREE.ShaderMaterial({
    uniforms: { uTemps: TEMPS_FLAMME, uPhase: { value: phase } },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */`
      uniform float uTemps; uniform float uPhase;
      varying float vHauteur; varying vec3 vN; varying vec3 vVue;
      void main(){
        vec3 p = position;
        vHauteur = clamp(p.y / ${HAUTEUR_FLAMME}, 0.0, 1.0);
        float h2 = vHauteur * vHauteur;
        p.y *= 1.0 + 0.10 * sin(uTemps * 8.3 + uPhase) + 0.05 * sin(uTemps * 19.0 + uPhase * 2.1);
        p.x += (0.6 * sin(uTemps * 6.1 + uPhase) + 0.4 * sin(uTemps * 14.3 + uPhase * 1.7)) * 0.0022 * h2;
        p.z += (0.6 * cos(uTemps * 5.3 + uPhase * 0.7) + 0.4 * sin(uTemps * 11.9 + uPhase)) * 0.0018 * h2;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vN = normalMatrix * normal; vVue = -mv.xyz;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      varying float vHauteur; varying vec3 vN; varying vec3 vVue;
      void main(){
        float face = abs(dot(normalize(vN), normalize(vVue)));
        vec3 coeur = vec3(3.4, 2.7, 1.5), manteau = vec3(2.0, 0.75, 0.18), pied = vec3(0.12, 0.22, 0.85);
        vec3 c = mix(manteau, coeur, smoothstep(0.45, 0.95, face) * (1.0 - smoothstep(0.35, 0.85, vHauteur)));
        c = mix(pied, c, smoothstep(0.02, 0.22, vHauteur));
        float voile = smoothstep(0.05, 0.6, face) * (1.0 - 0.7 * smoothstep(0.6, 1.0, vHauteur));
        gl_FragColor = vec4(c * voile, 1.0);
      }`,
  });
}

// `hauteur` en mètres : le vacillement se lit dans le repère de la flamme, il grandit avec elle.
export function flamme(phase, hauteur = HAUTEUR_FLAMME) {
  const mesh = new THREE.Mesh(FORME, materiauFlamme(phase));
  mesh.scale.setScalar(hauteur / HAUTEUR_FLAMME);
  return mesh;
}
