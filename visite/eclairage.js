// L'éclairage : les lampes du Temple, l'astre qui suit le visiteur, et le moment du jour qu'un parcours demande.
import * as THREE from "three";
import { astreDu, environnement, lumieresDu, peindreDome, teinterAir } from "./ciel.js";
import { laisserPeindre } from "./fil.js";
import { TEMPS_FLAMME, flamme } from "./flamme.js";
import { assombrir, eclairerLaSalle } from "./matieres.js";
import { PROFIL } from "./qualite.js";

// Le soleil est posé loin devant la caméra, pas à sa hauteur : la fenêtre d'ombre le
// suit, et il faut que ce qui la surplombe — la façade fait cinquante mètres — tienne
// entre son `near` et son `far`.
const RECUL_SOLEIL = 200;
const PAS_OMBRE = PROFIL.ombres.portee / 10;

// L'Arche éclaire le Kodesh HaKodashim : « עד שלא ניטל הארון היה נכנס ויוצא לאורו של ארון »
// (Yerushalmi Yoma 5:3, fiche §8e) — une lumière posée entre les keruvim, qui ne vacille
// pas et dont la portée meurt avant les murs. Les braises de la ma'hta, elles, vacillent à
// la mesure d'un bassin de charbons — pas d'une flamme : deux sinus incommensurables et un
// peu de hasard, jamais une période. Elles ne sont plus que le point chaud de la pièce.
const ARCHE = { couleur: 0xffeed2, intensite: 9, portee: 6, carte: 512 };
// Remonter `intensite` rallume les stries d'auto-ombre sur la calotte des keruvim : les regarder avant de conclure.
const BRAISE = { couleur: 0xff7a2a, intensite: 6, portee: 8, carte: 512 };
// Le feu de l'autel, une lampe au-dessus des ma'arakhot : de nuit, la seule lumière de l'Azara (Tamid 1:4).
const FEU = { couleur: 0xff8a3a, intensite: 600, portee: 60, carte: 1024, hauteur: 3.0 };
// L'or est métallique, il ne diffuse rien : sous 150 cd l'environnement couvre l'ombre du Shoulkhan, à 600 le mur brûle.
const MENORA = { couleur: 0xffe1aa, intensite: 150, portee: 18, carte: 512 };
// Les lampes de terre de la Lishkat HaGazit, une lueur par mèche : sans elles, la salle n'avait que sa
// lumière cuite, qui n'a pas de direction, et la pierre comme les gradins y rendaient à plat.
const LUEUR_GAZIT = { couleur: 0xffd8a0, intensite: 4 };
// Les mâts d'or de l'Ezrat Nashim, qui ne brûlent que la nuit de Sim'hat Beit HaSho'éva (Soucca 5:2).
const SHOEVA = { couleur: 0xffc58a, intensite: 600, portee: 200, carte: 1024 };
const HAUTEUR_FLAMME_SHOEVA = 1.2;
// Les torches de la ronde, en une lueur sans ombre : une lampe par torche, c'est un nuanceur par torche.
const LUEUR = { couleur: 0xffa860, intensite: 40, portee: 16, hauteur: 1.5 };   // m : des mèches de caleçons et de ceintures de cohanim (Soucca 5:3)

// De proche en proche : deux points à moins de `pas` l'un de l'autre sont du même groupe.
function centresDesGroupes(points, pas) {
  let groupes = [];
  for (const p of points) {
    const voisins = groupes.filter((g) => g.some((q) => q.distanceTo(p) < pas));
    groupes = [...groupes.filter((g) => !voisins.includes(g)), [p, ...voisins.flat()]];
  }
  return groupes.map((g) => g.reduce((somme, p) => somme.add(p), new THREE.Vector3()).divideScalar(g.length));
}

// Le bord des coupes est le plus haut du mât : ses sommets, groupés, donnent le centre de chacune.
function coupesDeLaShoeva(candelabres) {
  const sommets = [];
  for (const o of candelabres) {
    const position = o.geometry.attributes.position;
    for (let i = 0; i < position.count; i++) {
      sommets.push(new THREE.Vector3().fromBufferAttribute(position, i).applyMatrix4(o.matrixWorld));
    }
  }
  const haut = sommets.reduce((max, p) => Math.max(max, p.y), -Infinity);
  return centresDesGroupes(sommets.filter((p) => p.y > haut - 0.02), 0.25);
}

export function eclairerLeTemple({ scene, renderer, rendu, astres: { soleil, appoint, cielAmbiant }, ciel, brume, temple, sousSonde,
  emprises, reperes, horsGeometrie, annoncerAttente }) {
  let braise = null;
  let vacillement = 0;
  let feuDeLAutel = null;
  let lampesPosees = 0;
  // L'or est métallique : sans environnement à réfléchir, il rend noir.
  const reflets = { jour: environnement(renderer) };
  scene.environment = reflets.jour.texture;

  // La scène ne bouge pas : la carte cubique se calcule une fois, au premier rendu.
  function poserLampe(reglage, position, ombrage) {
    const carte = Math.min(reglage.carte, ombrage.carte);
    const lumiere = new THREE.PointLight(reglage.couleur, reglage.intensite, reglage.portee, 2);
    lumiere.position.copy(position);
    lumiere.castShadow = ombrage.ombre;
    lumiere.shadow.autoUpdate = false;
    lumiere.shadow.needsUpdate = true;
    lumiere.shadow.mapSize.set(carte, carte);
    lumiere.shadow.camera.near = 0.05;
    lumiere.shadow.camera.far = reglage.portee;
    lumiere.shadow.bias = -0.002;
    // Pas de `normalBias` ici, contrairement au soleil : ces trois lampes éclairent des
    // objets plus fins que le décalage qu'il faudrait. Une penne d'aile fait 2,5 mm, et
    // 2 cm — l'ordre de grandeur qui vaut pour le soleil — la traversent : la lumière
    // passe sous les ailes, les keruvim perdent l'ombre propre de leur visage et les
    // marches du Heikhal voient la leur se décoller du sol.
    scene.add(lumiere);
    return lumiere;
  }

  function eclairerKodeshHakodashim(arche, braises) {
    if (!arche?.length || !braises?.length) return;
    const lumiereArche = poserLampe(ARCHE, new THREE.Vector3(...arche[0]), PROFIL.sanctuaire);
    braise = poserLampe(BRAISE, new THREE.Vector3(...braises[0]), PROFIL.sanctuaire);
    // La pièce n'a aucune ouverture, mais le ciel y entrait quand même — par l'ambiance, par
    // le rebond, par l'or qui le réfléchit. La pénombre est dans la pièce, pas dans le
    // temps : elle se lit sur la position de chaque point, et la fumée y prend la lumière
    // des deux sources.
    assombrir(emprises.get("kodesh_hakodashim"));
    rendu.enfumer(emprises.get("kodesh_hakodashim"), braise.position, lumiereArche.position);
  }

  function vaciller(dt) {
    vacillement += dt;
    const t = vacillement;
    TEMPS_FLAMME.value = t;
    const eclat = lumieresDu(moment).shoeva ? SHOEVA.intensite : 0;
    shoeva?.lampes.forEach((l, i) => {
      l.intensity = eclat * (0.93 + 0.04 * Math.sin(t * 7.3 + i) + 0.03 * Math.sin(t * 17.9 + i * 2.1));
    });
    if (shoeva?.lueur) shoeva.lueur.intensity = eclat ? LUEUR.intensite * (0.9 + 0.1 * Math.sin(t * 11.3)) : 0;
    lueursGazit.forEach((l, i) => {
      l.w = LUEUR_GAZIT.intensite * (0.94 + 0.04 * Math.sin(t * 8.3 + i * 1.7) + 0.02 * Math.sin(t * 19.1 + i));
    });
    if (lumiereMenora) {
      lumiereMenora.intensity = MENORA.intensite * (0.95 + 0.03 * Math.sin(t * 9.1) + 0.02 * Math.sin(t * 23.0 + 2.0));
    }
    if (feuDeLAutel) {
      feuDeLAutel.intensity = lumieresDu(moment).feu ? FEU.intensite * (0.9 + 0.06 * Math.sin(t * 2.3) + 0.04 * Math.sin(t * 6.1 + 1.3)) : 0;
    }
    if (!braise) return;
    const souffle = 0.86 + 0.09 * Math.sin(t * 1.7) + 0.05 * Math.sin(t * 4.3 + 1.0) + 0.04 * (Math.random() - 0.5);
    braise.intensity = BRAISE.intensite * souffle;
  }

  let lumiereMenora = null;

  function allumerMenora(flammes) {
    if (!flammes?.length) return;
    const centre = new THREE.Vector3();
    flammes.forEach((p, i) => {
      const meche = flamme(i * 2.39);
      meche.position.set(...p);
      scene.add(meche);
      horsGeometrie.push(meche);
      centre.add(meche.position);
    });
    // Au-dessus des mèches et non entre elles : à un doigt de la lampe du milieu, son or brûlait.
    const point = centre.divideScalar(flammes.length).add(new THREE.Vector3(0, 0.35, 0));
    lumiereMenora = poserLampe(MENORA, point, PROFIL.sanctuaire);
  }

  let lueursGazit = [];

  function allumerLesLueurs(lueurs) {
    if (!lueurs?.points.length) return;
    const salle = new THREE.Box3(new THREE.Vector3(...lueurs.salle.min), new THREE.Vector3(...lueurs.salle.max));
    lueursGazit = eclairerLaSalle(salle, lueurs.points, LUEUR_GAZIT.couleur);
  }

  let moment = "jour";
  let directionDeLAstre = astreDu(moment);
  let shoeva = null;
  let lumiereCuiteDuCiel = null;

  // Le Heikhal et le Kodesh HaKodashim ont leur lumière cuite à leurs propres lampes, que la nuit n'éteint pas.
  function eclaireParSesLampes(maillage) {
    if (sousSonde.has(maillage)) return true;
    const centre = maillage.geometry.boundingBox.getCenter(new THREE.Vector3()).applyMatrix4(maillage.matrixWorld);
    return emprises.get("kodesh_hakodashim").containsPoint(centre);
  }

  // Une lampe par mât, au milieu de ses quatre coupes : seize lampes à carte d'ombre, c'est seize cubes à rendre.
  function poserShoeva() {
    const candelabres = [];
    temple.traverse((o) => { if (o.isMesh && o.userData.concept === "candelabres_shoeva") candelabres.push(o); });
    const coupes = coupesDeLaShoeva(candelabres);
    const flammes = coupes.map((coupe, i) => {
      const meche = flamme(i * 2.39, HAUTEUR_FLAMME_SHOEVA);
      meche.position.copy(coupe).y -= 0.1;
      scene.add(meche);
      horsGeometrie.push(meche);
      return meche;
    });
    const lampes = centresDesGroupes(coupes, 2).map((mat) =>
      poserLampe(SHOEVA, mat.add(new THREE.Vector3(0, HAUTEUR_FLAMME_SHOEVA / 2, 0)), PROFIL.feux));
    return { candelabres, flammes, lampes, lueur: eclairerLaRonde(emprises.get("hassidim_veanshei_maase")) };
  }

  function eclairerLaRonde(ronde) {
    if (!ronde) return null;
    const lueur = new THREE.PointLight(LUEUR.couleur, 0, LUEUR.portee, 2);
    ronde.getCenter(lueur.position).y += LUEUR.hauteur;
    scene.add(lueur);
    return lueur;
  }

  // L'intensité de jour de chaque lumière cuite au ciel seul, celle que le moment module.
  function lumieresCuitesAuCiel() {
    const intensites = new Map();
    temple.traverse((o) => {
      if (o.isMesh && o.material.lightMap && !eclaireParSesLampes(o)) intensites.set(o.material, o.material.lightMapIntensity);
    });
    return intensites;
  }

  function allumerLeFeu() {
    const dessus = emprises.get("maarakhot");
    const foyer = dessus.getCenter(new THREE.Vector3()).setY(dessus.max.y + FEU.hauteur);
    return poserLampe(FEU, foyer, PROFIL.feux);
  }

  // Les mâts et le feu ne sont posés qu'à la première nuit : le visiteur de jour n'en paie ni les lampes ni les nuanceurs.
  // Posées avant que « préparation… » soit peint, la boucle compilerait leurs nuanceurs dans son image, figée, sans l'avoir montré.
  async function passerAu(voulu) {
    if (voulu === moment) return;
    const lumieres = lumieresDu(voulu);
    const lampesAPoser = (feuDeLAutel === null && lumieres.feu) || (shoeva === null && lumieres.shoeva);
    if (!lampesAPoser) return eclairerAu(voulu);
    await annoncerAttente(async () => {
      eclairerAu(voulu);
      await rendu.compiler();
      // La première image de nuit trace les cartes d'ombre des lampes : sous le voile, et non au premier pas.
      await laisserPeindre();
    });
  }

  function eclairerAu(voulu) {
    const quitte = moment;
    moment = voulu;
    const lumieres = lumieresDu(voulu);
    soleil.color.set(lumieres.astre.couleur);
    soleil.intensity = lumieres.astre.intensite;
    directionDeLAstre = astreDu(voulu);
    ANCRE_OMBRE.set(Infinity, Infinity, Infinity);
    appoint.intensity = lumieres.appoint;
    cielAmbiant.intensity = lumieres.ciel;
    peindreDome(ciel, voulu);
    teinterAir(brume, voulu);
    reflets[voulu] ??= environnement(renderer, voulu);
    scene.environment = reflets[voulu].texture;
    // Le ciel de jour revient à la fin de chaque parcours ; celui d'un autre moment se refait en un fondu s'il revient.
    if (quitte !== "jour") {
      reflets[quitte].dispose();
      delete reflets[quitte];
    }
    lumiereCuiteDuCiel ??= lumieresCuitesAuCiel();
    for (const [materiau, intensite] of lumiereCuiteDuCiel) materiau.lightMapIntensity = intensite * lumieres.cuite;
    if (feuDeLAutel === null && lumieres.feu) {
      feuDeLAutel = allumerLeFeu();
      lampesPosees++;
    }
    if (shoeva === null && lumieres.shoeva) {
      shoeva = poserShoeva();
      lampesPosees++;
    }
    if (shoeva !== null) {
      for (const f of shoeva.flammes) f.visible = lumieres.shoeva;
      // Les coupes sont sous la lampe de leur mât : leur ombre posait quatre disques noirs sur les murs.
      for (const o of shoeva.candelabres) o.castShadow = !lumieres.shoeva;
    }
  }

  // L'ombre portée est une fenêtre de 110 amot ; à l'échelle du Har HaBayit une seule
  // carte figée serait illisible. Elle suit donc le visiteur — mais par sauts, pas à
  // chaque image : la refaire coûte une passe de géométrie entière, la troisième de
  // l'image après la principale et celle de l'occlusion, et la fenêtre fait cinquante
  // mètres de large quand on n'avance que d'une douzaine de centimètres par image, en
  // courant. Tant qu'on ne la rafraîchit pas, three garde aussi la matrice qui va avec :
  // carte et matrice restent d'accord, et l'ombre reste juste — elle est simplement
  // calculée depuis un pas en arrière.
  const ANCRE_OMBRE = new THREE.Vector3(Infinity, Infinity, Infinity);

  function suivreSoleil(oeil, ombresMobilesPres) {
    if (ombresMobilesPres(ANCRE_OMBRE)) soleil.shadow.needsUpdate = true;
    if (oeil.distanceToSquared(ANCRE_OMBRE) < PAS_OMBRE * PAS_OMBRE) return;
    ANCRE_OMBRE.copy(oeil);
    soleil.target.position.copy(oeil);
    soleil.position.copy(oeil).addScaledVector(directionDeLAstre, RECUL_SOLEIL);
    soleil.target.updateMatrixWorld();
    soleil.shadow.needsUpdate = true;
  }

  // Three ne refait pas seul les environnements après une perte de contexte.
  function refaireLesReflets() {
    for (const m of Object.keys(reflets)) {
      reflets[m].dispose();
      reflets[m] = environnement(renderer, m);
    }
    scene.environment = reflets[moment].texture;
  }

  allumerMenora(reperes.flammes);
  allumerLesLueurs(reperes.lueurs);
  eclairerKodeshHakodashim(reperes.arche, reperes.braises);

  return {
    passerAu, vaciller, suivreSoleil, refaireLesReflets,
    get moment() { return moment; },
    get lampesPosees() { return lampesPosees; },
  };
}
