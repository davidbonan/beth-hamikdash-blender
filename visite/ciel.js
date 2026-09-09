/**
 * Le ciel : d'où vient la lumière, ce que la scène réfléchit, et ce qui l'éloigne.
 *
 * Deux dômes, pas un. Celui qu'on VOIT porte le disque solaire à sa taille vraie —
 * un demi-degré — sur le dégradé d'un matin de Jérusalem : un ciel d'où vient une
 * ombre franche sans qu'on voie d'où elle vient se lit en éclairage de studio.
 *
 * Celui qui ÉCLAIRE, filtré en PMREM, n'a pas les mêmes couleurs. Il n'y a pas de
 * rebond dans cette scène : sous un portique la seule lumière serait celle du bleu du
 * zénith, et le dallage à l'ombre y virait au bleu franc. Le ciel de l'éclairage est
 * donc désaturé vers le haut, et sa moitié basse porte le calcaire ensoleillé de
 * l'esplanade, qui est le vrai rebond de tout ce qui est à l'ombre ici.
 *
 * Son soleil, lui, est ÉLARGI, et son horizon RESSERRÉ. Un disque d'un demi-degré ne
 * survit pas au filtrage : il ne couvre pas un texel de la cube-map. Sans lui l'or ne
 * réfléchit qu'un dégradé lisse — un métal qui n'a pas d'image dans son reflet se lit
 * en plastique jaune, et c'est ce qu'on voyait. Étalé sur trois degrés il traverse le
 * filtrage, et la ligne d'horizon lui donne la seconde chose qu'un métal doit
 * réfléchir pour en être un : une arête.
 */
import * as THREE from "three";

// Vingt degrés au-dessus de l'horizon, à l'est : l'axe de l'avoda, et l'heure du
// tamid du matin. L'angle n'est pas un détail d'ambiance — c'est lui qui décide si la
// lumière RASE la pierre ou l'écrase. À 38°, l'assise, le joint, le chanfrein et le
// grain des nappes recevaient tous la même clarté et le relief disparaissait. Plus bas
// que vingt, en revanche, le dallage ne reçoit plus qu'un quart du soleil et l'ambiance
// reprend le dessus : la cour repasse en aplat pâle, l'inverse de ce qu'on cherche.
export const SOLEIL = new THREE.Vector3(150, 58, 55).normalize();

// Le brouillard porte la couleur du BAS du ciel, et pas une autre : accordé au dôme
// il éloigne, désaccordé il salit. Il commence à six mètres et pas à deux cents : sans
// lui, un mur à quarante mètres avait exactement le contraste d'une marche à deux, et
// la cour entière se lisait en maquette. Ce qui sépare les plans à cette distance-là,
// ce n'est pas le voile mais la perte de contraste qu'il apporte.
export const BRUME = new THREE.Fog(0xd8dcd4, 6, 700);

const VU = { haut: 0x4d7fb8, bas: 0xd8dcd4, sol: 0xa89c86, ambiance: 1.0,
             soleil: 2.2, etendue: 7e-5, horizon: 6.0 };
// Le dôme ÉCLAIRANT tient trois réglages que la scène ne sait pas calculer seule.
//
// `ambiance` pèse sur le dégradé et jamais sur le disque : c'est le rapport du soleil à
// ce qui n'en vient pas, et sur une face horizontale il était renversé. Une dalle au
// soleil ne devait qu'un cinquième de sa clarté au soleil et quatre cinquièmes au ciel
// — mesurée à 1,13 fois l'ombre voisine, quand une cour de Jérusalem en rend deux et
// demie. C'est ce rapport-là, et pas la teinte, qui donnait le chantier : une ombre
// qu'on ne voit pas est une scène sans soleil, donc sans heure et sans relief.
//
// `haut` n'est pas le bleu du ciel. Sous un soleil de 20°, une face horizontale ne
// reçoit du soleil qu'un tiers de ce qu'en prend un parement : c'est le zénith qui
// décide de la couleur du dallage, et à 0x8fa5bd il en faisait du béton — un chroma
// mesuré à 1/255, du côté froid du gris, sur la moitié basse de chaque cadre. Il n'est
// pas neutre pour autant : une dalle à l'ombre, dans une cour dont les murs sont au
// soleil, reçoit d'eux un rebond chaud qu'aucune passe ne calcule ici, et sans lui elle
// retombe en béton une seconde fois. Le bleu, lui, reste au dôme qu'on VOIT.
//
// `sol` est le rebond du dallage, et rien d'autre : il suit le dallage quand il change.
// Il a porté 0xc9b795 quand la cour était ocre, puis 0xc4bcae le temps qu'elle soit
// grise ; le rovad est revenu dans le meleke des murs (MAT_SOL), son rebond avec.
const ECLAIRANT = { haut: 0xb2aa9c, bas: 0xe0d9c9, sol: 0xcdc0a8, ambiance: 0.45,
                    soleil: 3.5, etendue: 1.6e-3, horizon: 26.0 };

function dome(rayon, teintes) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(rayon, 64, 32),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { hautCiel: { value: new THREE.Color(teintes.haut) },
                  basCiel: { value: new THREE.Color(teintes.bas) },
                  solCiel: { value: new THREE.Color(teintes.sol) },
                  dirSoleil: { value: SOLEIL },
                  ambiance: { value: teintes.ambiance },
                  soleil: { value: teintes.soleil },
                  etendue: { value: teintes.etendue },
                  horizon: { value: teintes.horizon } },
      vertexShader: /* glsl */`
        varying vec3 vD;
        void main(){ vD = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: /* glsl */`
        uniform vec3 hautCiel, basCiel, solCiel, dirSoleil;
        uniform float ambiance, soleil, etendue, horizon;
        varying vec3 vD;
        void main(){
          vec3 d = normalize(vD); float h = d.y;
          vec3 c = ambiance * (h > 0.0 ? mix(basCiel, hautCiel, pow(h, 0.55))
                                      : mix(basCiel, solCiel, min(-h * horizon, 1.0)));
          float s = max(dot(d, dirSoleil), 0.0);
          // Trois portées : la moitié du ciel se réchauffe vers le soleil, le halo se
          // resserre autour, le disque tient dans son étendue.
          c += vec3(1.00, 0.84, 0.58) * (0.10 * pow(s, 4.0) + 0.45 * pow(s, 160.0));
          c += vec3(1.00, 0.95, 0.86) * soleil
             * smoothstep(1.0 - etendue, 1.0 - 0.3 * etendue, s);
          gl_FragColor = vec4(c, 1.0);
        }`,
    }));
}

export function domeVu(rayon) {
  const m = dome(rayon, VU);
  m.frustumCulled = false;
  return m;
}

export function environnement(renderer) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const cible = pmrem.fromScene(new THREE.Scene().add(dome(20, ECLAIRANT)), 0.04, 0.1, 200);
  pmrem.dispose();
  return cible.texture;
}
