// Le feu de l'autel : les flammes de chaque ma'arakha et la colonne de fumée de la grande, parcourues en volume.
import * as THREE from "three";
import { PROFIL } from "./qualite.js";

const FOYERS_MAX = 4;
// « וְלֹא נָצְחָה הָרוּחַ אֶת עַמּוּד הֶעָשָׁן » (Avot 5:5) : la colonne monte droit, et ne s'évase que de sa propre chaleur.
const COLONNE = { hauteur: 75, evasement: 0.08, col: 0.7, ondulation: 0.45 };
// Ce que le bruit et l'ondulation débordent du rayon de la colonne.
const MARGE_COLONNE = 1.25 + COLONNE.ondulation;
// Ce que le feu fait de son lit, en parts du demi-côté : la hauteur des flammes, et d'où part la fumée.
const FLAMMES = { hauteur: 1.0, socle: 0.5, debord: 1.1, depart: 0.6 };

const hauteurDesFlammes = (demi) => FLAMMES.hauteur * demi + FLAMMES.socle;
const demiCote = (lit) => (lit.max.x - lit.min.x + lit.max.z - lit.min.z) / 4;
const rayonDeLaColonne = (demi, montee) => COLONNE.col * demi + COLONNE.evasement * montee;

/** Un Vector4 par lit de braises (Box3, mètres) : son centre, et son demi-côté en `w`. */
export function foyersDuFeu(lits) {
  return Array.from({ length: FOYERS_MAX }, (_, i) => {
    const lit = lits[i];
    return lit ? new THREE.Vector4(...lit.getCenter(new THREE.Vector3()).toArray(), demiCote(lit)) : new THREE.Vector4();
  });
}

/** Ce que flammes et fumée occupent, pour savoir si l'œil les voit et jusqu'où la géométrie doit les couper. */
export function empriseDuFeu(lits) {
  const emprise = new THREE.Box3();
  for (const lit of lits.slice(0, FOYERS_MAX)) {
    const centre = lit.getCenter(new THREE.Vector3()), demi = demiCote(lit);
    const large = FLAMMES.debord * demi;
    emprise.expandByPoint(new THREE.Vector3(centre.x - large, centre.y, centre.z - large));
    emprise.expandByPoint(new THREE.Vector3(centre.x + large, centre.y + hauteurDesFlammes(demi), centre.z + large));
  }
  if (!lits.length) return emprise;
  const centre = lits[0].getCenter(new THREE.Vector3()), demi = demiCote(lits[0]);
  const rayon = MARGE_COLONNE * rayonDeLaColonne(demi, COLONNE.hauteur);
  const base = centre.y + FLAMMES.depart * hauteurDesFlammes(demi);
  emprise.expandByPoint(new THREE.Vector3(centre.x - rayon, base, centre.z - rayon));
  emprise.expandByPoint(new THREE.Vector3(centre.x + rayon, base + COLONNE.hauteur, centre.z + rayon));
  return emprise;
}

const nombre = (valeur) => valeur.toFixed(4);

export const FEU_DE_L_AUTEL = PROFIL.feuDeLAutel && {
  uniforms: { tGeo: { value: null },
              uTanFov: { value: 0 }, uAspect: { value: 1 }, uMonde: { value: new THREE.Matrix4() }, uTemps: { value: 0 },
              uFoyers: { value: foyersDuFeu([]) },
              uVersLAstre: { value: new THREE.Vector3(0, 1, 0) }, uAstre: { value: new THREE.Color() }, uPartDuCiel: { value: 1 } },
  defines: { PAS_FLAMMES: PROFIL.feuDeLAutel.flammes, PAS_FUMEE: PROFIL.feuDeLAutel.fumee, OCTAVES: PROFIL.feuDeLAutel.octaves },
  fragmentShader: /* glsl */`
    uniform sampler2D tGeo;
    uniform float uTanFov, uAspect, uTemps, uPartDuCiel;
    uniform mat4 uMonde;
    uniform vec4 uFoyers[${FOYERS_MAX}];
    uniform vec3 uVersLAstre, uAstre;
    varying vec2 vUv;

    const float HAUTEUR_COLONNE = ${nombre(COLONNE.hauteur)};
    // Par mètre traversé : la fumée au col de la colonne, la flamme à son plus vif, et ce que la flamme arrête.
    const float DENSITE_FUMEE = 1.1, ECLAT_FLAMME = 1.7, OPACITE_FLAMME = 2.2;
    const vec3 ALBEDO_FUMEE = vec3(0.80, 0.79, 0.78), ALBEDO_SUIE = vec3(0.34, 0.31, 0.29);
    const vec3 CIEL_SUR_LA_FUMEE = vec3(0.16, 0.19, 0.25), LUEUR_DU_FEU = vec3(0.30, 0.12, 0.03);

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

    float hauteurDesFlammes(float demi){ return ${nombre(FLAMMES.hauteur)} * demi + ${nombre(FLAMMES.socle)}; }

    // Des langues, pas une nappe : un bruit qui monte, que la hauteur seuille de plus en plus haut, sur un lit dont les points chauds se déplacent.
    float flamme(vec3 p, vec4 foyer, out float h){
      vec3 l = p - foyer.xyz;
      h = l.y / hauteurDesFlammes(foyer.w);
      float r = max(abs(l.x), abs(l.z)) / foyer.w;
      float bord = 1.0 - smoothstep(0.70 - 0.40 * h, 1.05 - 0.50 * h, r);
      if (h < 0.0 || h > 1.0 || bord <= 0.0) return 0.0;
      float maille = 0.20 + 0.08 * foyer.w;
      vec3 q = vec3(l.x, l.y * 0.34, l.z) / maille;
      q.y -= uTemps * 2.3;
      q.xz += (vec2(bruit(q * 0.5 + vec3(0.0, 0.0, uTemps * 0.6)), bruit(q * 0.5 + vec3(7.1, 3.3, -uTemps * 0.6))) - 0.5) * 2.0 * h;
      float pointChaud = bruit(vec3(l.xz / (maille * 3.2), uTemps * 0.3) + foyer.xzy);
      // Le bruit replié autour de son milieu donne des lames ; seul il fait un rideau de fils, mêlé au bruit plein il découpe des langues.
      float plein = fbm(q);
      float vive = mix(plein, 1.0 - abs(plein * 2.0 - 1.0), 0.7) * 0.90 + pointChaud * 0.65 - 0.66 - h * 0.60;
      return clamp(vive * 4.5, 0.0, 1.0) * bord * smoothstep(0.0, 0.06, h);
    }

    // Le cœur d'une flamme de bois est jaune pâle, son manteau orange, sa pointe rouge et presque éteinte.
    vec3 couleurDeFlamme(float vive, float h){
      float chaleur = vive * (1.0 - 0.45 * h);
      vec3 c = mix(vec3(1.0, 0.16, 0.02), vec3(1.0, 0.52, 0.10), smoothstep(0.0, 0.45, chaleur));
      c = mix(c, vec3(1.0, 0.80, 0.40), smoothstep(0.50, 1.0, chaleur));
      return c * (0.45 + 1.9 * chaleur * chaleur);
    }

    float monteeDeLaFumee(vec3 p){
      vec4 f = uFoyers[0];
      return p.y - f.y - ${nombre(FLAMMES.depart)} * hauteurDesFlammes(f.w);
    }
    float rayonDeLaColonne(float montee){ return ${nombre(COLONNE.col)} * uFoyers[0].w + ${nombre(COLONNE.evasement)} * montee; }

    // Un cœur plein que le bruit ronge par le bord : des volutes, qui grossissent avec la colonne et montent plus vite qu'elle ne s'évase.
    float fumee(vec3 p){
      float montee = monteeDeLaFumee(p);
      if (montee < 0.0 || montee > HAUTEUR_COLONNE) return 0.0;
      float R = rayonDeLaColonne(montee);
      float lent = montee * 0.07 - uTemps * 0.05;
      vec2 ondulation = (vec2(bruit(vec3(lent, 1.3, 0.0)), bruit(vec3(4.7, lent, 2.1))) - 0.5)
                      * ${nombre(2 * COLONNE.ondulation)} * R * smoothstep(0.0, 12.0, montee);
      vec2 d = (p.xz - uFoyers[0].xz - ondulation) / R;
      float rr = length(d);
      if (rr > 1.25) return 0.0;
      vec3 q = vec3(d.x * 2.2, 3.0 * pow(montee + 0.4, 0.6) - uTemps * 0.6, d.y * 2.2);
      float volutes = fbm(q + (bruit(q * 0.5 + 3.0) - 0.5) * 1.6);
      float corps = 1.0 - smoothstep(0.15, 1.15, rr);
      float pleine = smoothstep(0.0, 0.35, corps * 1.25 - (1.0 - volutes) * 1.45 + 0.12);
      float dilution = pow(rayonDeLaColonne(0.0) / R, 1.1);
      return DENSITE_FUMEE * pleine * dilution * smoothstep(0.0, 1.8, montee) * (1.0 - smoothstep(0.55, 1.0, montee / HAUTEUR_COLONNE));
    }

    // La fumée est grise : elle rend l'astre sur sa face tournée vers lui, le ciel sur l'autre, et le feu à son pied.
    vec3 lumiereDeLaFumee(vec3 p, vec3 d){
      float montee = monteeDeLaFumee(p), R = rayonDeLaColonne(montee);
      float ombre = mix(exp(-fumee(p + uVersLAstre * 0.5 * R) * R * 3.0), 1.0, 0.12);
      const float g = 0.55;
      float versLAvant = (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * dot(d, uVersLAstre), 1.5);
      vec3 albedo = mix(ALBEDO_SUIE, ALBEDO_FUMEE, smoothstep(0.0, 9.0, montee));
      return albedo * (uAstre * ombre * mix(1.0, versLAvant, 0.4) + CIEL_SUR_LA_FUMEE * uPartDuCiel)
           + LUEUR_DU_FEU * exp(-montee / 2.2);
    }

    vec2 traversee(vec3 o, vec3 inv, vec3 bas, vec3 haut, float portee){
      vec3 a = (bas - o) * inv, b = (haut - o) * inv;
      vec3 tmin = min(a, b), tmax = max(a, b);
      return vec2(max(max(tmin.x, tmin.y), max(tmin.z, 0.0)), min(min(tmax.x, tmax.y), min(tmax.z, portee)));
    }

    // La colonne est un cône : hors de lui les pas tomberaient dans le vide, et ceux qui restent seraient trop longs pour ses volutes.
    vec2 traverseeDuCone(vec3 o, vec3 d, float base, vec2 t){
      const float PENTE = ${nombre(MARGE_COLONNE * COLONNE.evasement)};
      vec2 e = o.xz - uFoyers[0].xz;
      float rayon = ${nombre(MARGE_COLONNE)} * rayonDeLaColonne(0.0) + PENTE * (o.y - base);
      float a = dot(d.xz, d.xz) - PENTE * PENTE * d.y * d.y;
      if (a < 1e-3) return t;
      float b = dot(e, d.xz) - PENTE * d.y * rayon;
      float discriminant = b * b - a * (dot(e, e) - rayon * rayon);
      if (discriminant <= 0.0) return vec2(1.0, 0.0);
      float racine = sqrt(discriminant);
      return vec2(max(t.x, (-b - racine) / a), min(t.y, (-b + racine) / a));
    }

    // Lumière reprise, et en alpha ce qui traverse : ce que la passe écrit.
    vec4 poser(vec4 devant, vec4 derriere){ return vec4(devant.rgb + devant.a * derriere.rgb, devant.a * derriere.a); }

    vec4 flammes(vec3 o, vec3 d, vec3 inv, float portee, float hasard, out float entree){
      vec4 rendu = vec4(0.0, 0.0, 0.0, 1.0);
      entree = 1e9;
      for (int k = 0; k < ${FOYERS_MAX}; k++) {
        vec4 foyer = uFoyers[k];
        if (foyer.w <= 0.0) continue;
        vec3 large = vec3(${nombre(FLAMMES.debord)} * foyer.w, 0.0, ${nombre(FLAMMES.debord)} * foyer.w);
        vec2 t = traversee(o, inv, foyer.xyz - large, foyer.xyz + large + vec3(0.0, hauteurDesFlammes(foyer.w), 0.0), portee);
        if (t.y <= t.x) continue;
        entree = min(entree, t.x);
        float pas = (t.y - t.x) / float(PAS_FLAMMES);
        for (int i = 0; i < PAS_FLAMMES; i++) {
          float h;
          float vive = flamme(o + d * (t.x + (float(i) + hasard) * pas), foyer, h);
          if (vive <= 0.0) continue;
          rendu.rgb += rendu.a * couleurDeFlamme(vive, h) * (vive * ECLAT_FLAMME * pas);
          rendu.a *= exp(-vive * OPACITE_FLAMME * pas);
        }
      }
      return rendu;
    }

    vec4 colonne(vec3 o, vec3 d, vec3 inv, float portee, float hasard, out float entree){
      vec4 rendu = vec4(0.0, 0.0, 0.0, 1.0);
      entree = 1e9;
      vec4 f = uFoyers[0];
      if (f.w <= 0.0) return rendu;
      float base = f.y + ${nombre(FLAMMES.depart)} * hauteurDesFlammes(f.w);
      float rayon = ${nombre(MARGE_COLONNE)} * rayonDeLaColonne(HAUTEUR_COLONNE);
      vec2 t = traversee(o, inv, vec3(f.x - rayon, base, f.z - rayon), vec3(f.x + rayon, base + HAUTEUR_COLONNE, f.z + rayon), portee);
      t = traverseeDuCone(o, d, base, t);
      if (t.y <= t.x) return rendu;
      entree = t.x;
      float pas = (t.y - t.x) / float(PAS_FUMEE);
      for (int i = 0; i < PAS_FUMEE; i++) {
        vec3 p = o + d * (t.x + (float(i) + hasard) * pas);
        float densite = fumee(p);
        if (densite <= 0.0) continue;
        float alpha = 1.0 - exp(-densite * pas);
        rendu.rgb += rendu.a * alpha * lumiereDeLaFumee(p, d);
        rendu.a *= 1.0 - alpha;
        if (rendu.a < 0.02) break;
      }
      return rendu;
    }

    void main(){
      float z = texture2D(tGeo, vUv).a;
      vec3 dirVue = normalize(vec3((vUv * 2.0 - 1.0) * uTanFov * vec2(uAspect, 1.0), -1.0));
      vec3 o = uMonde[3].xyz;
      vec3 d = normalize(mat3(uMonde) * dirVue);
      float portee = z > 0.0 ? z / max(-dirVue.z, 1e-3) : 1e4;
      vec3 inv = 1.0 / d;
      // Un départ tiré au hasard par pixel, sinon les pas se liraient en strates.
      float hasard = fract(sin(dot(vUv * 977.0 + fract(uTemps), vec2(12.9898, 78.233))) * 43758.5453);
      float entreeDesFlammes, entreeDeLaColonne;
      vec4 feu = flammes(o, d, inv, portee, hasard, entreeDesFlammes);
      vec4 panache = colonne(o, d, inv, portee, hasard, entreeDeLaColonne);
      gl_FragColor = entreeDesFlammes < entreeDeLaColonne ? poser(feu, panache) : poser(panache, feu);
    }`,
};
