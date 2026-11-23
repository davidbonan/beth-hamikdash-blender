/**
 * La chaîne d'image : ce qui est fait de la scène après qu'elle est rendue.
 *
 * Quatre choses, dans cet ordre. L'OCCLUSION ambiante, qui pose les volumes. Le HALO,
 * qui fait déborder les hautes lumières. Les RAYONS, la lumière de l'astre dans l'air.
 * L'ADOUCISSEMENT des arêtes, qui vient en dernier parce qu'il travaille sur l'image finie.
 *
 * L'anti-crénelage est ici et pas sur le moteur. `antialias: true` sur le
 * WebGLRenderer ne vaut que pour le tampon d'écran, dans lequel cette chaîne n'écrit
 * jamais : la scène va dans une cible hors écran. C'est donc cette cible qui est
 * multi-échantillonnée, quatre prises par pixel pour les arêtes, les cordes et les
 * échelons — sauf au profil sobre, qui s'en passe. Le FXAA final reprend ce que le MSAA ne voit pas : la passe d'occlusion,
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
 * Il lit la profondeur que la scène vient d'écrire, résolue dans une texture : la distance
 * s'en déduit en mètres, la normale de ses voisins, et le décor n'est pas tracé une seconde fois.
 */
import * as THREE from "three";
import { FEU_DE_L_AUTEL, empriseDuFeu, foyersDuFeu } from "./feu_de_l_autel.js";
import { parTranches } from "./fil.js";
import { COURBE_DE_L_ECRAN, EXPOSITION, EXPOSITION_DEHORS, TEINTE_CUITE } from "./matieres.js";
import { OMBRE_LOINTAINE, profondeurLointaine } from "./ombres.js";
import { DISTANCE_LUE, PROFONDEUR_DE_LA_SCENE } from "./profondeur_de_la_scene.js";
import { PROFIL } from "./qualite.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { Pass, FullScreenQuad } from "three/addons/postprocessing/Pass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";

// Douze directions par pixel, en demi-résolution : c'est la passe la plus chère de
// la visite après la géométrie. Le profil léger en garde la moitié — le flou de la
// passe suivante, qui moyenne déjà neuf voisins, en avale la différence.
const ECHANTILLONS = PROFIL.occlusion?.prises ?? 0;
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
// Il s'éteint bien plus tôt que l'autre : la passe est en demi-résolution, et 8 cm y
// valent moins d'un pixel passé quinze mètres.
const PORTEE_FIN = [12.0, 26.0];
// L'occlusion pose les volumes proches : elle s'éteint entre ces deux distances.
const PORTEE = [45.0, 120.0];

const OCCLUSION = {
  uniforms: {
    uTanFov: { value: 0 }, uAspect: { value: 1 },
    uRayon: { value: RAYON }, uForce: { value: FORCE },
    uRayonFin: { value: RAYON_FIN }, uForceFin: { value: FORCE_FIN },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */`
    ${DISTANCE_LUE}
    uniform float uTanFov, uAspect, uRayon, uForce, uRayonFin, uForceFin;
    varying vec2 vUv;

    // La position de vue se déduit de la distance par le rayon qui traverse le pixel.
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
      float zS = distanceLue(uvS);
      if (zS <= 0.0) return 0.0;
      float devant = -S.z - zS;
      return step(biais, devant) * clamp(portee / max(devant, 1e-4), 0.0, 1.0);
    }

    // De chaque côté, le voisin le plus proche en distance : celui d'au-delà d'une arête fausserait la face.
    vec3 normaleVue(vec2 uv, vec3 P, vec2 texel){
      vec2 dx = vec2(texel.x, 0.0), dy = vec2(0.0, texel.y);
      vec3 est = positionVue(uv + dx, distanceLue(uv + dx)) - P, ouest = P - positionVue(uv - dx, distanceLue(uv - dx));
      vec3 nord = positionVue(uv + dy, distanceLue(uv + dy)) - P, sud = P - positionVue(uv - dy, distanceLue(uv - dy));
      return normalize(cross(abs(est.z) < abs(ouest.z) ? est : ouest, abs(nord.z) < abs(sud.z) ? nord : sud));
    }

    void main(){
      // En demi-définition, le centre d'un pixel tombe à la jointure de quatre texels de profondeur : on en lit un, en son centre.
      vec2 texel = 1.0 / vec2(textureSize(tProfondeur, 0));
      vec2 uv = (floor(vUv / texel) + 0.5) * texel;
      float z = distanceLue(uv);
      if (z <= 0.0) { gl_FragColor = vec4(1.0); return; }   // le ciel n'occlut rien
      vec3 P = positionVue(uv, z);
      vec3 N = normaleVue(uv, P, texel);
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
      ao = mix(ao, 1.0, smoothstep(${PORTEE[0].toFixed(1)}, ${PORTEE[1].toFixed(1)}, z));
      aoFin = mix(aoFin, 1.0, smoothstep(${PORTEE_FIN[0].toFixed(1)}, ${PORTEE_FIN[1].toFixed(1)}, z));
      gl_FragColor = vec4(ao, aoFin, 0.0, 1.0);
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
// la boîte de la pièce et par la géométrie qu'il rencontre (la profondeur de la
// scène), puis parcouru pas à pas : à chaque pas une densité — une nappe qui
// s'amasse sous le plafond, et la colonne qui monte des braises en ondulant — et la
// lumière que ce point reçoit de l'Arche et des braises, en 1/d². C'est cette lumière-là,
// reprise par la fumée, qui fait lire l'obscurité : sans elle la pièce n'est qu'un écran noir.
//
// Elle passe AVANT le halo, pour la même raison que le halo passe avant la sortie : la
// lueur de l'Arche dans la fumée est une haute lumière, et c'est elle qui doit déborder.
//
// Le parcours se fait en demi-définition : au quart les volutes perdent leur détail. Il écrit la lumière reprise et, en alpha, ce qui
// traverse ; `VOILE` pose ça sur l'image.
// En mètres. De plus loin la pièce est close — ses murs, sa parokhet extérieure à 1,3 m — et la fumée coupée partout : dans le champ, elle coûtait pourtant sa passe.
const RECUL_FUMEE = 2;
// En mètres. La colonne de l'autel se voit de tout le Har HaBayit.
const RECUL_FEU = 300;
const FUMEE = {
  uniforms: { uTanFov: { value: 0 }, uAspect: { value: 1 }, uMonde: { value: new THREE.Matrix4() },
              uBoiteMin: { value: new THREE.Vector3() }, uBoiteMax: { value: new THREE.Vector3() },
              uBraise: { value: new THREE.Vector3() }, uArche: { value: new THREE.Vector3() },
              uTemps: { value: 0 },
              uVoile: { value: 0.03 }, uVolutes: { value: 1.4 },
              uLueur: { value: 0.11 }, uLueurArche: { value: 0.22 }, uLampe: { value: 0.06 } },
  defines: { PAS: PROFIL.fumee.pas, OCTAVES: PROFIL.fumee.octaves },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    ${DISTANCE_LUE}
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
      float z = distanceLue(vUv);
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

// Les RAYONS : la lumière de l'astre que l'air diffuse vers l'œil, là où la carte d'ombre lointaine dit que l'astre l'atteint.
// Chaque pixel marche de l'œil à ce qu'il voit ; ce que le Temple met à l'ombre reste sombre dans l'air, et les faisceaux sont ce qui passe entre.
// Au-delà, l'air éclairé de toute l'esplanade noyait l'ombre d'une colonne : les faisceaux se jouent près de l'œil.
const PORTEE_RAYONS = 50;
const PLAFOND_RAYONS = 0.45;
const ECLAT_HORS_CHAMP = 0.12;
// La poussière des cours tient au sol : entière jusqu'au dallage de l'Azara, elle a perdu les deux tiers de sa densité dix mètres plus haut.
const SOL_DE_L_AIR = 0, EPAISSEUR_DE_L_AIR = 10;
const BIAIS_RAYONS = 0.4 / 700;
const RAYONS = PROFIL.rayons && {
  uniforms: { uCarteLointaine: { value: null }, uOmbreLointaine: { value: new THREE.Matrix4() },
              uMonde: { value: new THREE.Matrix4() }, uVersLAstre: { value: new THREE.Vector3() },
              uTanFov: { value: 0 }, uAspect: { value: 1 }, uDensite: { value: 0 } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    #include <packing>
    ${DISTANCE_LUE}
    uniform sampler2D uCarteLointaine;
    uniform mat4 uOmbreLointaine, uMonde;
    uniform vec3 uVersLAstre;
    uniform float uTanFov, uAspect, uDensite;
    varying vec2 vUv;

    // Hors de la carte, rien ne porte d'ombre : l'air y est au soleil.
    float auSoleil(vec3 p){
      vec3 coord = (uOmbreLointaine * vec4(p, 1.0)).xyz;
      if (any(lessThan(coord, vec3(0.0))) || any(greaterThan(coord, vec3(1.0)))) return 1.0;
      return step(coord.z - ${BIAIS_RAYONS.toFixed(6)}, unpackRGBAToDepth(texture2D(uCarteLointaine, coord.xy)));
    }

    void main(){
      float z = distanceLue(vUv);
      vec3 dirVue = normalize(vec3((vUv * 2.0 - 1.0) * uTanFov * vec2(uAspect, 1.0), -1.0));
      vec3 o = uMonde[3].xyz;
      vec3 d = normalize(mat3(uMonde) * dirVue);
      float portee = min(z > 0.0 ? z / max(-dirVue.z, 1e-3) : ${PORTEE_RAYONS}.0, ${PORTEE_RAYONS}.0);
      float pas = portee / ${PROFIL.rayons.prises}.0;
      // Le départ décalé d'un pixel à l'autre : sans lui les pas se lisent en strates.
      float depart = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715))));
      float eclaire = 0.0;
      for (int i = 0; i < ${PROFIL.rayons.prises}; i++) {
        vec3 p = o + d * pas * (float(i) + depart);
        eclaire += auSoleil(p) * exp(-max(p.y - ${SOL_DE_L_AIR.toFixed(1)}, 0.0) / ${EPAISSEUR_DE_L_AIR}.0);
      }
      // L'air diffuse vers l'avant : à contre-jour un faisceau brille, dos à l'astre il s'éteint.
      const float g = 0.5;
      float phase = (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * dot(d, uVersLAstre), 1.5);
      // L'éblouissement : hors du cadre, l'astre voile encore l'œil de son côté.
      float eblouit = ${ECLAT_HORS_CHAMP} * pow(0.5 + 0.5 * dot(d, uVersLAstre), 8.0) * uDensite / ${PROFIL.rayons.densite};
      // L'air qui diffuse s'épaissit sans jamais dépasser ce plafond : face à l'astre, l'esplanade virait au blanc.
      gl_FragColor = vec4(vec3(${PLAFOND_RAYONS} * (1.0 - exp(-uDensite * phase * eclaire * pas / ${PLAFOND_RAYONS})) + eblouit), 1.0);
    }`,
};

// Agrandis deux fois, les départs décalés des rayons se liraient en trame : neuf prises les fondent.
const AIR_ECLAIRE = {
  uniforms: { tDiffuse: { value: null }, tRayons: { value: null }, uPas: { value: new THREE.Vector2() }, uTeinte: { value: new THREE.Color() },
              uRetenue: { value: 1 } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse, tRayons;
    uniform vec2 uPas;
    uniform vec3 uTeinte;
    uniform float uRetenue;
    varying vec2 vUv;
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      float rayons = 0.0;
      for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) rayons += texture2D(tRayons, vUv + uPas * 1.5 * vec2(i, j)).r;
      gl_FragColor = vec4(c.rgb + uTeinte * uRetenue * rayons / 9.0, c.a);
    }`,
};

// La SORTIE : le linéaire de la scène passé par la courbe de l'écran, puis en sRGB. Elle tient la place de
// l'OutputPass de three, qui ne connaît pas encore cette courbe ; l'exposition est celle que l'œil adapté tient à jour.
const SORTIE = new THREE.ShaderMaterial({
  uniforms: { tDiffuse: { value: null }, uExposition: EXPOSITION },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform float uExposition;
    varying vec2 vUv;
    ${COURBE_DE_L_ECRAN}
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      gl_FragColor = sRGBTransferOETF(vec4(courbeDeLEcran(c.rgb * uExposition), c.a));
    }`,
});

// Le FLOU DE BOUGÉ de la caméra : le pixel rendu est retrouvé là où l'image d'avant le voyait, et la pose étale l'écart.
const BOUGE = PROFIL.bouge;
// Un écart plus grand que ce quart d'écran est un saut, pas un geste ; la traînée reste sous ce quarantième.
const SAUT = 0.25, TRAINEE_MAX = 0.025;
const FLOU_DE_BOUGE = BOUGE && {
  uniforms: { tDiffuse: { value: null }, uFacteur: { value: 0 },
              uVersAvant: { value: new THREE.Matrix4() }, uProjectionInverse: { value: new THREE.Matrix4() } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    ${DISTANCE_LUE}
    uniform sampler2D tDiffuse;
    uniform mat4 uVersAvant, uProjectionInverse;
    uniform float uFacteur;
    varying vec2 vUv;
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      float z = distanceLue(vUv);
      vec4 r = uProjectionInverse * vec4(vUv * 2.0 - 1.0, 1.0, 1.0);
      vec3 rayon = r.xyz / r.w;
      // Le ciel est à l'infini : seule la rotation le déplace.
      vec4 avant = z > 0.0 ? uVersAvant * vec4(rayon * (z / -rayon.z), 1.0) : uVersAvant * vec4(rayon, 0.0);
      if (avant.w <= 0.0) { gl_FragColor = c; return; }
      vec2 ecart = vUv - (avant.xy / avant.w * 0.5 + 0.5);
      if (length(ecart) > ${SAUT}) { gl_FragColor = c; return; }
      vec2 trainee = ecart * uFacteur;
      trainee *= min(1.0, ${TRAINEE_MAX} / max(length(trainee), 1e-6));
      if (length(trainee * vec2(textureSize(tDiffuse, 0))) < 0.5) { gl_FragColor = c; return; }
      // Le départ de chaque pixel est décalé : les paliers des prises se fondent en bruit, que le grain recouvre.
      float decale = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715))));
      vec3 somme = vec3(0.0);
      for (int i = 0; i < ${BOUGE?.prises ?? 0}; i++)
        somme += texture2D(tDiffuse, vUv + trainee * ((float(i) + decale) / ${BOUGE?.prises ?? 0}.0 - 0.5)).rgb;
      gl_FragColor = vec4(somme / ${BOUGE?.prises ?? 0}.0, c.a);
    }`,
};

// L'ÉTALONNAGE, en toute fin : netteté, ombres relevées, bascule de teinte, vignettage, grain.
//
// La NETTETÉ est celle d'un téléphone, qui accentue toute photographie : adaptative (CAS
// d'AMD), elle creuse les arêtes que le FXAA a fondues sans faire déborder ce qui a déjà
// du contraste. Les OMBRES sont relevées comme il les relève, en gardant leur teinte :
// une photo de cour au soleil montre la pierre à l'ombre, pas un aplat bleu-gris.
//
// Il travaille sur l'image AFFICHÉE, pas sur le linéaire : c'est le geste d'un
// laboratoire, pas d'un moteur, et une bascule chaud/froid appliquée avant le
// tonemapping serait mangée par la courbe de l'écran.
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
              uChaud: { value: new THREE.Color(1.01, 1.00, 0.96) },
              uContraste: { value: 0.25 }, uNettete: { value: 0.5 }, uReleve: { value: 0.45 },
              uPas: { value: new THREE.Vector2() },
              uVignette: { value: 0.12 }, uGrain: { value: 0.010 } },
  vertexShader: OCCLUSION.vertexShader,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform vec3 uFroid, uChaud;
    uniform float uTemps, uContraste, uNettete, uReleve, uVignette, uGrain;
    uniform vec2 uPas;
    varying vec2 vUv;
    void main(){
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      vec3 n = texture2D(tDiffuse, vUv + vec2(0.0, uPas.y)).rgb, s = texture2D(tDiffuse, vUv - vec2(0.0, uPas.y)).rgb;
      vec3 e = texture2D(tDiffuse, vUv + vec2(uPas.x, 0.0)).rgb, o = texture2D(tDiffuse, vUv - vec2(uPas.x, 0.0)).rgb;
      vec3 bas = min(c, min(min(n, s), min(e, o))), haut = max(c, max(max(n, s), max(e, o)));
      vec3 marge = sqrt(clamp(min(bas, 1.0 - haut) / max(haut, 1e-4), 0.0, 1.0));
      vec3 poids = marge * (-1.0 / mix(8.0, 5.0, uNettete));
      c = clamp((c + (n + s + e + o) * poids) / (1.0 + 4.0 * poids), 0.0, 1.0);
      float clair = dot(c, vec3(0.2126, 0.7152, 0.0722));
      c *= 1.0 + uReleve * (1.0 - smoothstep(0.04, 0.45, clair)) * smoothstep(0.0, 0.04, clair);
      clair = dot(c, vec3(0.2126, 0.7152, 0.0722));
      // La courbe creuse le jour, pas le noir des salles, qu'elle assombrissait d'un tiers.
      c = mix(c, c * c * (3.0 - 2.0 * c), uContraste * smoothstep(0.15, 0.45, clair));
      clair = dot(c, vec3(0.2126, 0.7152, 0.0722));
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
const RELUE_TOUTES = 20;
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

  oublierTampons() {
    this.tampon = null;
    this.lecture = null;
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

// Sous Metal, ce qu'un mur cache passait par tout son nuanceur : la profondeur d'abord, un cheveu en retrait, et seul ce qui se voit s'ombre.
class PrePasseDeProfondeur {
  constructor(scene, camera) {
    this.scene = scene;
    this.camera = camera;
    this.materiau = new THREE.MeshBasicMaterial({ colorWrite: false, polygonOffset: true,
                                                  polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
    this.voiles = [];
  }

  // Ce qui n'écrit pas sa profondeur — le dôme, les flammes, ce qu'on voit au travers — ne cache rien.
  rendre(renderer) {
    this.scene.traverseVisible((o) => {
      if (o.material && (o.material.transparent || !o.material.depthWrite)) this.voiles.push(o);
    });
    for (const o of this.voiles) o.visible = false;
    const ombresSuivies = renderer.shadowMap.autoUpdate;
    // Un voile caché porte encore son ombre : les cartes attendent la passe de la scène.
    renderer.shadowMap.autoUpdate = false;
    this.scene.overrideMaterial = this.materiau;
    try {
      renderer.render(this.scene, this.camera);
    } finally {
      this.scene.overrideMaterial = null;
      renderer.shadowMap.autoUpdate = ombresSuivies;
      for (const o of this.voiles) o.visible = true;
      this.voiles.length = 0;
    }
  }
}

// La cible de la scène n'est jamais celle où le composeur écrit : sa profondeur se relit jusqu'à la dernière passe.
class Composeur extends EffectComposer {
  constructor(renderer, cibleScene) {
    super(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false }));
    this.cibleScene = cibleScene;
  }

  swapBuffers() {
    this.readBuffer = this.writeBuffer;
    this.writeBuffer = this.readBuffer === this.renderTarget1 ? this.renderTarget2 : this.renderTarget1;
  }

  render() {
    this.readBuffer = this.cibleScene;
    this.writeBuffer = this.renderTarget1;
    super.render();
  }
}

// La matière que three prête à un maillage pour la carte d'ombre du soleil ou d'une lampe (WebGLShadowMap.getDepthMaterial) : face retournée, cartes recopiées.
const FACE_OMBRE = { [THREE.FrontSide]: THREE.BackSide, [THREE.BackSide]: THREE.FrontSide, [THREE.DoubleSide]: THREE.DoubleSide };
const RECOPIEES = ["map", "alphaMap", "alphaTest", "displacementMap", "displacementScale", "displacementBias"];
const OMBRE_DU_SOLEIL = () => new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking });
const OMBRE_D_UNE_LAMPE = () => new THREE.MeshDistanceMaterial();
const ombrePortee = (creer) => ({ castShadow, material }) => {
  if (!castShadow) return null;
  const ombre = Object.assign(creer(), { side: material.shadowSide ?? FACE_OMBRE[material.side] });
  for (const cle of RECOPIEES) ombre[cle] = material[cle] ?? ombre[cle];
  return ombre;
};
// La carte lointaine se trace d'un œil dont le calque ne voit aucune lampe.
const SANS_LAMPES = null;

const PLEIN_ECRAN = new THREE.BufferGeometry()
  .setAttribute("position", new THREE.Float32BufferAttribute([-1, 3, 0, -1, -1, 0, 3, -1, 0], 3))
  .setAttribute("uv", new THREE.Float32BufferAttribute([0, 2, 0, 0, 2, 0], 2));
// Un seul relevé pour tous les programmes : compileAsync interroge chacun toutes les 10 ms, un demi-million d'allers-retours avec le GPU sur iPhone.
const RELEVE_MS = 50;
const compterLesLies = (programmes) => programmes.filter((programme) => programme.isReady()).length;
const liaison = (renderer, suivre) => new Promise((lies) => {
  // Les programmes déjà liés ne comptent pas : au passage à la nuit, ceux du jour mettaient la jauge à mi-course d'entrée.
  const acquis = compterLesLies(renderer.info.programs);
  const releve = setInterval(() => {
    const programmes = renderer.info.programs;
    const prets = compterLesLies(programmes);
    if (prets < programmes.length) return suivre(Math.max(0, prets - acquis) / (programmes.length - acquis));
    suivre(1);
    clearInterval(releve);
    lies();
  }, RELEVE_MS);
});
// Three n'interroge un programme qu'à son premier usage, dans l'image qui le trace : interrogés avant elle, par tranches.
const interrogerAvantUsage = (programme) => programme.getUniforms();

export function chaine(renderer, scene, camera) {
  const cibleScene = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: PROFIL.antiCrenelage });
  cibleScene.depthTexture = new THREE.DepthTexture(1, 1);
  PROFONDEUR_DE_LA_SCENE.tProfondeur.value = cibleScene.depthTexture;
  const cibleFumee = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false });
  const cibleRayons = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false });

  const composeur = new Composeur(renderer, cibleScene);
  const prePasse = PROFIL.preProfondeur && new PrePasseDeProfondeur(scene, camera);
  const cibleAO = PROFIL.occlusion && new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false });
  const passeAO = PROFIL.occlusion && new ShaderPass(OCCLUSION);
  const composition = passeAO && new ShaderPass(COMPOSITION);
  if (passeAO) {
    composition.uniforms.tAO.value = cibleAO.texture;
    composeur.addPass(composition);
  }
  const fumee = new ShaderPass(FUMEE);
  const voile = new ShaderPass(VOILE);
  voile.uniforms.tFumee.value = cibleFumee.texture;
  voile.enabled = false;
  composeur.addPass(voile);
  const cibleFeu = FEU_DE_L_AUTEL && new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false });
  const feu = FEU_DE_L_AUTEL && new ShaderPass({ ...FEU_DE_L_AUTEL, vertexShader: OCCLUSION.vertexShader });
  const voileDuFeu = feu && new ShaderPass(VOILE);
  if (feu) {
    voileDuFeu.uniforms.tFumee.value = cibleFeu.texture;
    voileDuFeu.enabled = false;
    composeur.addPass(voileDuFeu);
  }
  // Avant le halo : une haute lumière traînée déborde en traînée, comme sur la pellicule.
  const bouge = FLOU_DE_BOUGE && new ShaderPass(FLOU_DE_BOUGE);
  if (bouge) composeur.addPass(bouge);
  // Avant le halo : c'est la lumière de la scène qu'on mesure, pas son débordement.
  const photometre = new Photometre();
  composeur.addPass(photometre);
  renderer.domElement.addEventListener("webglcontextrestored", () => photometre.oublierTampons());

  // Le halo passe AVANT la sortie, donc avant le tonemapping : la cible du composeur
  // est en demi-flottant et garde le linéaire, et c'est là seulement que le soleil sur
  // l'or vaut cinq et le calcaire à l'ombre un dixième. Après la courbe tout est ramené
  // sous 1 et il n'y a plus de haute lumière à faire déborder.
  // Le seuil se lit dans ce linéaire-là : à 0,80 d'exposition, 1,6 sort à 0,92 de l'écran —
  // le seuil ne prend donc que ce qui brûle vraiment.
  const halo = PROFIL.halo && new UnrealBloomPass(
    new THREE.Vector2(1, 1), PROFIL.halo.force, PROFIL.halo.rayon, PROFIL.halo.seuil);
  if (halo) composeur.addPass(halo);
  // Après le halo : les faisceaux sont déjà de la lumière diffusée, il les étalerait une seconde fois.
  const rayons = RAYONS && new ShaderPass(RAYONS);
  const airEclaire = rayons && new ShaderPass(AIR_ECLAIRE);
  if (rayons) {
    rayons.uniforms.uCarteLointaine.value = OMBRE_LOINTAINE.uCarteLointaine.value;
    airEclaire.uniforms.tRayons.value = cibleRayons.texture;
    airEclaire.enabled = false;
    composeur.addPass(airEclaire);
  }
  composeur.addPass(new ShaderPass(SORTIE));

  // Après la sortie, et pas avant : le FXAA cherche ses arêtes sur la luminance
  // perçue, celle de l'image affichée. Sur du linéaire non borné il prendrait chaque
  // reflet pour une arête et laisserait passer tout le reste.
  const arretes = new ShaderPass(FXAAShader);
  composeur.addPass(arretes);
  // Après le FXAA et pas avant : le grain posé plus tôt lui donnerait des arêtes à
  // chercher partout, et il l'effacerait en même temps.
  const etalonnage = new ShaderPass(ETALONNAGE);
  if (PROFIL.etalonnage) etalonnage.uniforms.uReleve.value = PROFIL.etalonnage.releve;
  composeur.addPass(etalonnage);
  for (const passe of [passeAO, fumee, feu, rayons, bouge]) if (passe) Object.assign(passe.uniforms, PROFONDEUR_DE_LA_SCENE);

  // Un composeur construit sur sa propre cible fige sa définition à 1 : la scène était rendue en CSS, puis agrandie.
  function redimensionner(l, h, definition) {
    const p = renderer.getPixelRatio();
    composeur.setPixelRatio(definition);
    composeur.setSize(l, h);
    cibleScene.setSize(composeur.renderTarget1.width, composeur.renderTarget1.height);
    const demi = { l: Math.round(l * p * 0.5), h: Math.round(h * p * 0.5) };
    cibleFumee.setSize(demi.l, demi.h);
    voile.uniforms.uPas.value.set(1 / cibleFumee.width, 1 / cibleFumee.height);
    halo?.setSize(composeur.renderTarget1.width, composeur.renderTarget1.height);
    arretes.material.uniforms.resolution.value.set(1 / composeur.renderTarget1.width, 1 / composeur.renderTarget1.height);
    etalonnage.uniforms.uPas.value.set(1 / composeur.renderTarget1.width, 1 / composeur.renderTarget1.height);
    const tanFov = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    if (passeAO) {
      cibleAO.setSize(Math.round(l * p * PROFIL.occlusion.definition), Math.round(h * p * PROFIL.occlusion.definition));
      composition.uniforms.uPas.value.set(1 / cibleAO.width, 1 / cibleAO.height);
      passeAO.uniforms.uTanFov.value = tanFov;
      passeAO.uniforms.uAspect.value = camera.aspect;
    }
    fumee.uniforms.uTanFov.value = tanFov;
    fumee.uniforms.uAspect.value = camera.aspect;
    if (feu) {
      cibleFeu.setSize(demi.l, demi.h);
      voileDuFeu.uniforms.uPas.value.set(1 / cibleFeu.width, 1 / cibleFeu.height);
      feu.uniforms.uTanFov.value = tanFov;
      feu.uniforms.uAspect.value = camera.aspect;
    }
    if (!rayons) return;
    cibleRayons.setSize(demi.l, demi.h);
    airEclaire.uniforms.uPas.value.set(1 / cibleRayons.width, 1 / cibleRayons.height);
    rayons.uniforms.uTanFov.value = tanFov;
    rayons.uniforms.uAspect.value = camera.aspect;
  }

  // L'éclat des faisceaux au moment, et `partDeLAir` celle que le lieu en garde : sous un centième, la passe ne se fait plus.
  let eclatDeLAir = 0, partDeLAir = 1;
  const allumerLAir = () => { airEclaire.enabled = eclatDeLAir > 0 && partDeLAir > 0.01; };
  function eclairerLAir(versLAstre, teinte, eclat) {
    if (!rayons) return;
    eclatDeLAir = eclat;
    allumerLAir();
    airEclaire.uniforms.uTeinte.value.set(teinte);
    rayons.uniforms.uVersLAstre.value.copy(versLAstre);
    rayons.uniforms.uDensite.value = PROFIL.rayons.densite * eclat;
  }

  function ouvrirLAir(part) {
    if (!rayons) return;
    partDeLAir = part;
    allumerLAir();
  }

  // Sous un toit l'œil ouvre : sans retenue, l'air du dehors y brûlait jusqu'au blanc.
  function rendreLesRayons() {
    airEclaire.uniforms.uRetenue.value = partDeLAir * EXPOSITION_DEHORS / renderer.toneMappingExposure;
    rayons.uniforms.uMonde.value.copy(camera.matrixWorld);
    rayons.uniforms.uOmbreLointaine.value.copy(OMBRE_LOINTAINE.uOmbreLointaine.value);
    rayons.render(renderer, cibleRayons, null, 0, false);
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

  /** Les lits de braises de l'autel (Box3, en mètres), le plus étendu d'abord : c'est lui qui porte la colonne de fumée. */
  let empriseDuFeuDeLAutel = null;
  function embraser(lits) {
    if (!feu || !lits.length) return;
    feu.uniforms.uFoyers.value = foyersDuFeu(lits);
    empriseDuFeuDeLAutel = empriseDuFeu(lits);
  }

  function teinterLaLumiereCuite(chaleurCuite = [1, 1, 1]) {
    if (PROFIL.etalonnage) TEINTE_CUITE.value.setRGB(...chaleurCuite);
  }

  /** `astre` : sa couleur et son intensité ; `partDuCiel` : ce que le moment garde du ciel de jour. */
  function eclairerLeFeu(versLAstre, astre, partDuCiel) {
    if (!feu) return;
    feu.uniforms.uVersLAstre.value.copy(versLAstre);
    feu.uniforms.uAstre.value.set(astre.couleur).multiplyScalar(astre.intensite / Math.PI);
    feu.uniforms.uPartDuCiel.value = partDuCiel;
  }

  const dansLeChamp = (boite) => champ.setFromProjectionMatrix(
    vueProjetee.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse)).intersectsBox(boite);
  const pieceEnfumeeVue = () => pieceEnfumee !== null && pieceEnfumee.distanceToPoint(camera.position) < RECUL_FUMEE && dansLeChamp(pieceEnfumee);
  const feuDeLAutelVu = () => empriseDuFeuDeLAutel !== null && empriseDuFeuDeLAutel.distanceToPoint(camera.position) < RECUL_FEU
    && dansLeChamp(empriseDuFeuDeLAutel);

  function rendreLaScene() {
    const autoClear = renderer.autoClear;
    renderer.autoClear = false;
    try {
      renderer.setRenderTarget(cibleScene);
      renderer.clear();
      if (prePasse) prePasse.rendre(renderer);
      renderer.render(scene, camera);
    } finally {
      renderer.autoClear = autoClear;
    }
  }

  // Une image de pas nul est un saut demandé (vue, capture) : elle n'a pas de mouvement à étaler.
  const vueAvant = new THREE.Matrix4(), vueCourante = new THREE.Matrix4();
  function poserLeBouge(dt) {
    if (!bouge) return;
    vueCourante.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    bouge.enabled = dt > 0 && !vueCourante.equals(vueAvant);
    if (bouge.enabled) {
      bouge.uniforms.uFacteur.value = BOUGE.pose / dt;
      bouge.uniforms.uVersAvant.value.multiplyMatrices(vueAvant, camera.matrixWorld);
      bouge.uniforms.uProjectionInverse.value.copy(camera.projectionMatrixInverse);
    }
    vueAvant.copy(vueCourante);
  }

  function rendre(dt) {
    voile.enabled = pieceEnfumeeVue();
    if (feu) voileDuFeu.enabled = feuDeLAutelVu();
    const eclaire = rayons && airEclaire.enabled;
    poserLeBouge(dt);
    PROFONDEUR_DE_LA_SCENE.uProche.value = camera.near;
    PROFONDEUR_DE_LA_SCENE.uLoin.value = camera.far;
    etalonnage.uniforms.uTemps.value = performance.now() * 0.001;
    fumee.uniforms.uTemps.value = etalonnage.uniforms.uTemps.value;
    fumee.uniforms.uMonde.value.copy(camera.matrixWorld);

    // Les matrices se font une fois : sans ça three recalcule celles de toute la scène à chaque passe.
    scene.updateMatrixWorld();
    scene.matrixWorldAutoUpdate = false;
    try {
      rendreLaScene();
      if (passeAO) passeAO.render(renderer, cibleAO, null, 0, false);
      if (voile.enabled) fumee.render(renderer, cibleFumee, null, 0, false);
      if (voileDuFeu?.enabled) {
        feu.uniforms.uTemps.value = etalonnage.uniforms.uTemps.value;
        feu.uniforms.uMonde.value.copy(camera.matrixWorld);
        feu.render(renderer, cibleFeu, null, 0, false);
      }
      if (eclaire) rendreLesRayons();
      renderer.setRenderTarget(null);
      composeur.render();
    } finally {
      scene.matrixWorldAutoUpdate = true;
    }
  }

  // Compilés hors cible, les nuanceurs prendraient le tonemapping de l'écran : la scène se rend dans le composeur, sans lui.
  // compile ne voit que la matière de chaque objet : celle de la pré-passe de profondeur se compilait à sa première image, figée.
  async function compiler(objets = scene, suivre = () => {}) {
    renderer.setRenderTarget(cibleScene);
    renderer.compile(objets, camera, scene);
    compilerPleinEcran(passesEnTampon());
    if (prePasse) compilerSous(objets, () => prePasse.materiau);
    compilerOmbres(objets);
    compilerSous(objets, profondeurLointaine, SANS_LAMPES);
    renderer.setRenderTarget(null);
    compilerPleinEcran([etalonnage.material]);
    await liaison(renderer, suivre);
    await parTranches([...renderer.info.programs], interrogerAvantUsage);
  }

  // Une passe plein écran se trace hors scène, sans lampes ni brume dans la clé de son nuanceur : compilée à la première image, elle la figeait.
  function compilerPleinEcran(materiaux) {
    renderer.compile(new THREE.Group().add(...materiaux.map((materiau) => new THREE.Mesh(PLEIN_ECRAN, materiau))), camera);
  }

  function passesEnTampon() {
    const halos = halo ? [halo.materialHighPassFilter, ...halo.separableBlurMaterials, halo.compositeMaterial, halo.blendMaterial] : [];
    return [passeAO, composition, bouge, fumee, voile, feu, voileDuFeu, rayons, airEclaire, arretes].filter(Boolean).map((passe) => passe.material).concat(PHOTOMETRIE, halos);
  }

  // Des doubles vêtus de la matière de la passe : three déduit du maillage ses variantes, squelette compris, et une tuile ne se laisse pas rhabiller.
  function compilerSous(objets, habit, lampes = scene) {
    const doubles = new THREE.Group();
    objets.traverse((o) => {
      const materiau = o.isMesh && habit(o);
      if (materiau) doubles.add(Object.assign(o.clone(false), { material: materiau }));
    });
    renderer.compile(doubles, camera, lampes);
  }

  // La carte d'ombre se trace sans scène, donc sans brume, et three compte la brume dans la clé de chaque nuanceur.
  function compilerOmbres(objets) {
    const brume = scene.fog;
    scene.fog = null;
    try {
      for (const ombre of [OMBRE_DU_SOLEIL, OMBRE_D_UNE_LAMPE]) compilerSous(objets, ombrePortee(ombre));
    } finally {
      scene.fog = brume;
    }
  }

  return { rendre, redimensionner, enfumer, embraser, eclairerLeFeu, eclairerLAir, ouvrirLAir, teinterLaLumiereCuite, compiler, get luminance() { return photometre.luminance; } };
}
