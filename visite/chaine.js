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
 * Il ne lit PAS le tampon de profondeur, multi-échantillonné et encodé par le moteur.
 * Une passe séparée écrit donc la normale et la distance en clair, en mètres, dans une
 * cible flottante : ce qu'on y lit ne dépend d'aucun réglage du moteur.
 */
import * as THREE from "three";
import { PROFIL } from "./qualite.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { Pass, FullScreenQuad } from "three/addons/postprocessing/Pass.js";
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

// LA FUMÉE de la ketoret, dans le seul volume qui en a : le Kodesh HaKodashim. Une
// passe d'écran, pas un objet — la scène n'a ni volumes ni particules, et un nuage de
// cartes alpha se trahit dès qu'on le traverse. Le rayon de chaque pixel est coupé par
// la boîte de la pièce et par la géométrie qu'il rencontre (la distance de la passe
// d'occlusion), puis parcouru pas à pas : à chaque pas une densité — une nappe qui
// s'amasse sous le plafond, et la colonne qui monte des braises en ondulant — et la
// lumière que ce point reçoit de l'Arche et des braises, en 1/d². C'est cette lumière-là,
// reprise par la fumée, qui fait lire l'obscurité : sans elle la pièce n'est qu'un écran noir.
//
// Elle passe AVANT le halo, pour la même raison que le halo passe avant la sortie : la
// lueur de l'Arche dans la fumée est une haute lumière, et c'est elle qui doit déborder.
//
// Le parcours se fait en demi-définition, sur la grille de la passe de géométrie qu'il lit :
// au quart les volutes perdent leur détail. Il écrit la lumière reprise et, en alpha, ce qui
// traverse ; `VOILE` pose ça sur l'image.
const FUMEE = {
  uniforms: { tGeo: { value: null },
              uTanFov: { value: 0 }, uAspect: { value: 1 }, uMonde: { value: new THREE.Matrix4() },
              uBoiteMin: { value: new THREE.Vector3() }, uBoiteMax: { value: new THREE.Vector3() },
              uBraise: { value: new THREE.Vector3() }, uArche: { value: new THREE.Vector3() },
              uTemps: { value: 0 },
              uVoile: { value: 0.03 }, uVolutes: { value: 1.4 },
              uLueur: { value: 0.11 }, uLueurArche: { value: 0.22 }, uLampe: { value: 0.06 } },
  defines: { PAS: PROFIL.fumee.pas, OCTAVES: PROFIL.fumee.octaves },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tGeo;
    uniform float uTanFov, uAspect, uTemps, uVoile, uVolutes, uLueur, uLueurArche, uLampe;
    uniform mat4 uMonde;
    uniform vec3 uBoiteMin, uBoiteMax, uBraise, uArche;
    varying vec2 vUv;

    float hachage(vec3 p){
      p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3)); p *= 17.0;
      return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
    }
    float bruit(vec3 x){
      vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(mix(hachage(i), hachage(i + vec3(1, 0, 0)), f.x),
                     mix(hachage(i + vec3(0, 1, 0)), hachage(i + vec3(1, 1, 0)), f.x), f.y),
                 mix(mix(hachage(i + vec3(0, 0, 1)), hachage(i + vec3(1, 0, 1)), f.x),
                     mix(hachage(i + vec3(0, 1, 1)), hachage(i + vec3(1, 1, 1)), f.x), f.y), f.z);
    }

    float fbm(vec3 x){
      float s = 0.0, a = 0.5, somme = 0.0;
      for (int i = 0; i < OCTAVES; i++) {
        s += a * bruit(x); somme += a;
        x = x * 2.03 + vec3(1.7, 9.2, 3.1); a *= 0.5;
      }
      return s / somme;
    }

    // La ketoret a empli la maison (Yoma 5:1) : un voile diffus partout, et des volutes
    // nettes dans le seul panache qui monte des braises en s'élargissant. Une volute est
    // la crête d'un bruit déformé par un autre bruit : fine, enroulée.
    float densite(vec3 p){
      float h = clamp((p.y - uBoiteMin.y) / (uBoiteMax.y - uBoiteMin.y), 0.0, 1.0);
      float voile = 0.6 + 0.4 * h + 0.5 * (bruit(p * 0.15 + vec3(uTemps * 0.01, 0.0, -uTemps * 0.008)) - 0.5);
      // Le déplacement du panache ne l'écarte jamais de plus de 0,45·dy : au-delà, ses
      // volutes pèsent moins qu'un millième et ses quatre bruits ne changent rien.
      vec2 r = p.xz - uBraise.xz;
      float dy = p.y - uBraise.y;
      float montee = max(dy, 0.0);
      float ecartMin = max(length(r) - 0.45 * montee, 0.0);
      float rayon = 0.35 + 0.3 * montee;
      float large = max(rayon * rayon, 0.04 + 0.12 * montee);
      if (dy < -0.05 || uVolutes * exp(-ecartMin * ecartMin / large) < 1e-3) return uVoile * voile;

      float angle = uTemps * 0.04 + h * 1.5;
      float c = cos(angle), s = sin(angle);
      vec3 q = vec3(c * r.x - s * r.y, p.y - uTemps * 0.35, s * r.x + c * r.y) * 0.32;
      vec3 w = vec3(bruit(q * 0.7 + vec3(0.0, uTemps * 0.03, 5.2)),
                    bruit(q * 0.7 + vec3(3.1, 0.0, uTemps * 0.03)),
                    bruit(q * 0.7 + vec3(7.4, uTemps * 0.02, 1.3))) - 0.5;
      float crete = 1.0 - abs(fbm(q * 2.0 + w * 3.0) * 2.0 - 1.0);
      float volute = smoothstep(0.90, 0.995, crete);
      vec2 d = r + w.xz * 0.6 * montee;
      float colonne = exp(-dot(d, d) / (0.04 + 0.12 * montee)) * smoothstep(-0.05, 0.3, dy);
      float panache = exp(-dot(d, d) / (rayon * rayon)) * smoothstep(-0.05, 0.3, dy);
      return uVoile * voile + uVolutes * (volute * panache + 0.4 * colonne);
    }

    // Un point source vu à travers la fumée : en 1/d², diffusé vers l'avant — à contre-jour
    // elle brille. Même diffusion pour les deux sources, c'est la même fumée.
    vec3 source(vec3 p, vec3 d, vec3 point, vec3 teinte, float force){
      vec3 v = p - point;
      float d2 = max(dot(v, v), 0.06);
      const float g = 0.5;
      float cosT = dot(v * inversesqrt(d2), d);
      float phase = (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * cosT, 1.5);
      return teinte * (force * phase / d2);
    }

    // La fumée est blanche : elle prend la couleur de ce qui l'éclaire. L'Arche, les braises,
    // la lampe de tête qui la fait voir autour de soi, et un fond presque noir.
    vec3 lumiere(vec3 p, vec3 o, vec3 d){
      float dc = max(distance(p, o), 0.6);
      return source(p, d, uArche, vec3(1.0, 0.93, 0.82), uLueurArche)
           + source(p, d, uBraise, vec3(1.0, 0.62, 0.36), uLueur)
           + vec3(1.0, 0.95, 0.88) * (uLampe / pow(dc, 1.7))
           + vec3(0.010, 0.009, 0.008);
    }

    void main(){
      float z = texture2D(tGeo, vUv).a;
      vec3 dirVue = normalize(vec3((vUv * 2.0 - 1.0) * uTanFov * vec2(uAspect, 1.0), -1.0));
      vec3 o = uMonde[3].xyz;
      vec3 d = normalize(mat3(uMonde) * dirVue);
      float portee = z > 0.0 ? z / max(-dirVue.z, 1e-3) : 1e4;
      vec3 inv = 1.0 / d;
      vec3 a = (uBoiteMin - o) * inv, b = (uBoiteMax - o) * inv;
      vec3 tmin = min(a, b), tmax = max(a, b);
      float t0 = max(max(tmin.x, tmin.y), max(tmin.z, 0.0));
      float t1 = min(min(tmax.x, tmax.y), min(tmax.z, portee));
      if (t1 <= t0) { gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
      // Pas en progression quadratique : fins près de l'œil, où une volute se voit en
      // détail, longs au loin, où elle ne couvre que quelques pixels. Un départ tiré au
      // hasard par pixel, sinon les pas se liraient en strates.
      float etendue = t1 - t0;
      float hasard = fract(sin(dot(vUv * 977.0 + fract(uTemps), vec2(12.9898, 78.233))) * 43758.5453);
      float T = 1.0;
      vec3 L = vec3(0.0);
      for (int i = 0; i < PAS; i++) {
        float u0 = (float(i) + hasard) / float(PAS);
        if (u0 >= 1.0) break;
        float u1 = min((float(i) + 1.0 + hasard) / float(PAS), 1.0);
        float pas = etendue * (u1 * u1 - u0 * u0);
        vec3 p = o + d * (t0 + etendue * 0.5 * (u0 * u0 + u1 * u1));
        float alpha = 1.0 - exp(-densite(p) * pas);
        L += T * alpha * lumiere(p, o, d);
        T *= 1.0 - alpha;
        if (T < 0.02) break;
      }
      gl_FragColor = vec4(L, T);
    }`,
};

// Le départ tiré au hasard de chaque texel, agrandi deux fois, marbrerait la fumée : quatre
// prises bilinéaires décalées d'un texel le fondent.
const VOILE = {
  uniforms: { tDiffuse: { value: null }, tFumee: { value: null }, uPas: { value: new THREE.Vector2() } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse, tFumee;
    uniform vec2 uPas;
    varying vec2 vUv;
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      vec4 f = 0.25 * (texture2D(tFumee, vUv + uPas * vec2(-1.0, -1.0)) + texture2D(tFumee, vUv + uPas * vec2(1.0, -1.0))
                     + texture2D(tFumee, vUv + uPas * vec2(-1.0, 1.0)) + texture2D(tFumee, vUv + uPas * vec2(1.0, 1.0)));
      gl_FragColor = vec4(c.rgb * f.a + f.rgb, c.a);
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

// La PHOTOMÉTRIE : ce que l'œil reçoit vraiment, lu dans le linéaire avant toute
// exposition. Moyenne géométrique, comme un posemètre : une porte au soleil dans le
// champ tire l'œil vers le bas sans que ses quelques pixels ne décident de tout.
// Chaque case de la grille en moyenne 8 × 8 ; la grille est relue toutes les
// quelques images, l'adaptation mettant de toute façon plus d'une seconde à suivre.
const GRILLE = 16;
const RELUE_TOUTES = 6;
const PHOTOMETRIE = new THREE.ShaderMaterial({
  uniforms: { tDiffuse: { value: null } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    varying vec2 vUv;
    void main(){
      vec2 coin = vUv - 0.5 / ${GRILLE}.0;
      float somme = 0.0;
      for (int i = 0; i < 8; i++) for (int j = 0; j < 8; j++) {
        vec3 c = texture2D(tDiffuse, coin + (vec2(i, j) + 0.5) / (8.0 * ${GRILLE}.0)).rgb;
        somme += log(max(dot(c, vec3(0.2126, 0.7152, 0.0722)), 1e-4));
      }
      gl_FragColor = vec4(somme / 64.0, 0.0, 0.0, 1.0);
    }`,
});

// La grille se relit quand le GPU l'a finie, pas sur-le-champ : une lecture immédiate l'attendait
// toutes les six images, et sur iPhone cette attente se voyait en à-coups.
class Photometre extends Pass {
  constructor() {
    super();
    this.needsSwap = false;
    this.cible = new THREE.WebGLRenderTarget(GRILLE, GRILLE, { type: THREE.FloatType, depthBuffer: false });
    this.cases = new Float32Array(GRILLE * GRILLE * 4);
    this.quad = new FullScreenQuad(PHOTOMETRIE);
    this.images = 0;
    this.luminance = null;
    this.tampon = null;
    this.lecture = null;
  }

  render(renderer, writeBuffer, readBuffer) {
    const gl = renderer.getContext();
    if (this.lecture) this.relever(gl);
    if (this.images++ % RELUE_TOUTES || this.lecture) return;
    PHOTOMETRIE.uniforms.tDiffuse.value = readBuffer.texture;
    renderer.setRenderTarget(this.cible);
    this.quad.render(renderer);
    if (!this.tampon) {
      this.tampon = gl.createBuffer();
      gl.bindBuffer(gl.PIXEL_PACK_BUFFER, this.tampon);
      gl.bufferData(gl.PIXEL_PACK_BUFFER, this.cases.byteLength, gl.STREAM_READ);
    }
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, this.tampon);
    gl.readPixels(0, 0, GRILLE, GRILLE, gl.RGBA, gl.FLOAT, 0);
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);
    this.lecture = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
  }

  relever(gl) {
    if (gl.clientWaitSync(this.lecture, 0, 0) === gl.TIMEOUT_EXPIRED) return;
    gl.deleteSync(this.lecture);
    this.lecture = null;
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, this.tampon);
    gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, this.cases);
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);
    let somme = 0;
    for (let i = 0; i < this.cases.length; i += 4) somme += this.cases[i];
    this.luminance = Math.exp(somme / (GRILLE * GRILLE));
  }
}

/**
 * `horsGeo` : ce qui ne doit pas entrer dans la passe de géométrie. Le dôme de ciel
 * en fait partie — il enveloppe la scène, et il occluerait tout.
 */
export function chaine(renderer, scene, camera, horsGeo = []) {
  const cibleGeo = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: true });
  const cibleAO = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false });
  const cibleFumee = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false });

  const teinteFond = new THREE.Color();
  const composeur = new EffectComposer(renderer,
    new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }));
  composeur.addPass(new RenderPass(scene, camera));
  const passeAO = new ShaderPass(OCCLUSION);
  passeAO.renderToScreen = false;
  const passeComposition = new ShaderPass(COMPOSITION);
  passeComposition.uniforms.tAO.value = cibleAO.texture;
  composeur.addPass(passeComposition);
  const fumee = new ShaderPass(FUMEE);
  fumee.uniforms.tGeo.value = cibleGeo.texture;
  const voile = new ShaderPass(VOILE);
  voile.uniforms.tFumee.value = cibleFumee.texture;
  voile.enabled = false;
  composeur.addPass(voile);
  // Avant le halo : c'est la lumière de la scène qu'on mesure, pas son débordement.
  const photometre = new Photometre();
  composeur.addPass(photometre);

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
    cibleFumee.setSize(cibleGeo.width, cibleGeo.height);
    voile.uniforms.uPas.value.set(1 / cibleFumee.width, 1 / cibleFumee.height);
    halo?.setSize(l * p, h * p);
    arretes.material.uniforms.resolution.value.set(1 / (l * p), 1 / (h * p));
    passeComposition.uniforms.uPas.value.set(1 / cibleAO.width, 1 / cibleAO.height);
    passeAO.uniforms.uTanFov.value = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    passeAO.uniforms.uAspect.value = camera.aspect;
    fumee.uniforms.uTanFov.value = passeAO.uniforms.uTanFov.value;
    fumee.uniforms.uAspect.value = camera.aspect;
  }

  /** La pièce enfumée (Box3, en mètres), le point d'où monte la fumée et celui qui l'éclaire
   *  avec lui. Le rayon d'un pixel qui n'entre pas dans la boîte — ou que la géométrie arrête
   *  avant — n'y coûte qu'un test, et une pièce hors du champ ne coûte aucune passe. */
  let pieceEnfumee = null;
  const champ = new THREE.Frustum();
  const vueProjetee = new THREE.Matrix4();
  function enfumer(boite, braise, arche) {
    pieceEnfumee = boite.clone();
    fumee.uniforms.uBoiteMin.value.copy(boite.min);
    fumee.uniforms.uBoiteMax.value.copy(boite.max);
    fumee.uniforms.uBraise.value.copy(braise);
    fumee.uniforms.uArche.value.copy(arche);
  }

  const pieceEnfumeeVue = () => pieceEnfumee !== null && champ.setFromProjectionMatrix(
    vueProjetee.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse)).intersectsBox(pieceEnfumee);

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
    fumee.uniforms.uTemps.value = etalonnage.uniforms.uTemps.value;
    fumee.uniforms.uMonde.value.copy(camera.matrixWorld);
    passeAO.render(renderer, cibleAO, null, 0, false);
    voile.enabled = pieceEnfumeeVue();
    if (voile.enabled) fumee.render(renderer, cibleFumee, null, 0, false);
    renderer.setRenderTarget(null);
    composeur.render();
  }

  // Compilés hors cible, les nuanceurs prendraient le tonemapping de l'écran : la scène se rend dans le composeur, sans lui.
  function compiler(objets = scene) {
    renderer.setRenderTarget(composeur.readBuffer);
    const prets = renderer.compileAsync(objets, camera, scene);
    renderer.setRenderTarget(null);
    return prets;
  }

  return { rendre, redimensionner, enfumer, compiler, get luminance() { return photometre.luminance; } };
}
