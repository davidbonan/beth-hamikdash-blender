// Les figurants, en troupes : celle de la visite libre et celle de chaque parcours, chacune à l'heure de son service.
import * as THREE from "three";
import { enBoite } from "./cadrage.js";
import { laisserPeindre } from "./fil.js";
import { flamme } from "./flamme.js";
import { ETOFFES } from "./matieres.js";
import { PROFIL, plafonner } from "./qualite.js";

// Une troupe pour la visite libre, une par parcours : chacune descend la première fois qu'on la demande.
// Chemins écrits en entier : empreintes.py ne signe que ceux qu'il lit.
export const TROUPES = {
  figures: { glb: "./figures.glb", json: "./figures.json" },
  figures_tamid: { glb: "./figures_tamid.glb", json: "./figures_tamid.json" },
  figures_kippour: { glb: "./figures_kippour.glb", json: "./figures_kippour.json" },
  figures_shoeva: { glb: "./figures_shoeva.glb", json: "./figures_shoeva.json" },
  figures_pessah: { glb: "./figures_pessah.glb", json: "./figures_pessah.json" },
  figures_bikkourim: { glb: "./figures_bikkourim.glb", json: "./figures_bikkourim.json" },
  figures_souccot: { glb: "./figures_souccot.glb", json: "./figures_souccot.json" },
  figures_hakhel: { glb: "./figures_hakhel.glb", json: "./figures_hakhel.json" },
  figures_nazir: { glb: "./figures_nazir.glb", json: "./figures_nazir.json" },
};
export const TROUPE_LIBRE = "figures";

const MARGE_GESTE = 0.35;
const HAUTEUR_FLAMME_TORCHE = 0.3;

export function troupesDeFigurants({ scene, camera, renderer, chargeur, rendu, detail, alleger, obstacles, horsGeometrie,
  distributions, conceptDe, lampesPosees }) {
  const troupes = {};
  const chargements = {};
  const EMPRISES_FIGURANTS = Object.fromEntries(Object.entries(distributions).map(([nom, { emprises }]) =>
    [nom, Object.values(emprises).map(enBoite)]));
  // La voulue change à la demande, la présente sous le voile du fondu qui suit.
  let troupeVoulue = TROUPE_LIBRE, troupePresente = TROUPE_LIBRE;
  // Les figurants que l'étape d'un parcours appelle, par nom ou par concept ; null : toute la troupe.
  let appeles = null;
  const PRISE = new THREE.MeshBasicMaterial();

  // Le clic vise une boîte portée par le figurant : un rayon sur un corps animé transforme chaque sommet en JavaScript.
  function prendreEnMain(figurant) {
    const emprise = new THREE.Box3();
    figurant.traverse((o) => {
      if (!o.isMesh) return;
      o.material.side = ETOFFES.has(o.material.name) ? THREE.DoubleSide : THREE.FrontSide;
      o.castShadow = PROFIL.figurants.ombre;
      o.receiveShadow = true;
      if (!o.isSkinnedMesh) return;
      o.computeBoundingSphere();
      o.boundingSphere.radius += MARGE_GESTE;
      o.computeBoundingBox();
      emprise.union(o.boundingBox.clone().applyMatrix4(o.matrix));
    });
    const prise = new THREE.Mesh(new THREE.BoxGeometry(...emprise.getSize(new THREE.Vector3()).toArray()), PRISE);
    emprise.getCenter(prise.position);
    prise.visible = false;
    prise.userData.concept = conceptDe(figurant);
    figurant.add(prise);
    return prise;
  }

  // Où le figurant peut paraître : sa prise, et tout le trajet de son concept s'il marche ou danse.
  function etendueDe(figurant, prise, emprises, animations) {
    const etendue = new THREE.Box3().setFromObject(prise);
    const bouge = animations.some((clip) => clip.tracks.some((piste) => piste.name === `${figurant.name}.position`));
    const trajet = bouge && emprises[conceptDe(figurant)];
    return trajet ? etendue.union(enBoite(trajet)) : etendue;
  }

  // La tête d'étoupe est au bout du manche, sur l'axe y du maillage : la flamme s'y pose, droite, quoi que fasse la torche.
  function allumerTorches(figurant, rang) {
    const torches = [];
    figurant.traverse((o) => { if (o.isMesh && /_avouka(_\d+)?$/.test(o.name)) torches.push(o); });
    return torches.map((torche, i) => {
      torche.geometry.computeBoundingBox();
      const meche = flamme((rang + i) * 1.93, HAUTEUR_FLAMME_TORCHE);
      scene.add(meche);
      horsGeometrie.push(meche);
      return { torche, meche, bout: new THREE.Vector3(0, torche.geometry.boundingBox.max.y - 0.06, 0) };
    });
  }

  function suivreTorches(troupe) {
    if (!troupe.torches.length) return;
    troupe.scene.updateMatrixWorld();
    for (const { torche, meche, bout } of troupe.torches) meche.position.copy(bout).applyMatrix4(torche.matrixWorld);
  }

  const estAppele = (figurant) => appeles === null || appeles.has(figurant.name) || appeles.has(conceptDe(figurant));

  // Caché, un figurant sort de ce que le doigt vise, et ses torches s'éteignent.
  function montrerFigurant({ figurant, prise, torches }, visible) {
    figurant.visible = visible;
    for (const { meche } of torches) meche.visible = visible;
    const rang = obstacles.indexOf(prise);
    if (visible && rang < 0) obstacles.push(prise);
    if (!visible && rang >= 0) obstacles.splice(rang, 1);
  }

  // Les autres troupes se cachent ; de la présente, les figurants que l'étape appelle.
  function montrerTroupes() {
    for (const [nom, troupe] of Object.entries(troupes)) {
      const presente = nom === troupePresente;
      troupe.scene.visible = presente;
      for (const membre of troupe.membres) montrerFigurant(membre, presente && estAppele(membre.figurant));
    }
  }

  // En marche, un figurant ne paraît ni ne disparaît sous les yeux : il attend d'être hors du cadre.
  const cadre = new THREE.Frustum(), projection = new THREE.Matrix4();
  function relayerHorsDuCadre() {
    const troupe = troupes[troupePresente];
    if (!troupe) return;
    cadre.setFromProjectionMatrix(projection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    for (const membre of troupe.membres) {
      const voulu = estAppele(membre.figurant);
      if (membre.figurant.visible !== voulu && !cadre.intersectsBox(membre.etendue)) montrerFigurant(membre, voulu);
    }
  }

  function texturesDe(racine) {
    const textures = new Set();
    racine.traverse((o) => {
      if (o.isMesh) for (const valeur of Object.values(o.material)) if (valeur?.isTexture) textures.add(valeur);
    });
    return [...textures];
  }

  // Envoyées d'un bloc à la première image de la troupe, ses textures figeaient la marche : une par image, avant qu'elle n'entre.
  async function envoyerTextures(textures) {
    for (const texture of textures) {
      renderer.initTexture(texture);
      await laisserPeindre();
    }
  }

  function rendreLaMemoire(maillages) {
    const materiaux = new Set(maillages.map((m) => m.material));
    for (const maillage of maillages) {
      maillage.geometry.dispose();
      maillage.skeleton?.dispose();
    }
    for (const materiau of materiaux) {
      for (const valeur of Object.values(materiau)) if (valeur?.isTexture) valeur.dispose();
      materiau.dispose();
    }
  }

  // Compilés avant d'entrer en scène : sinon la première image qui les voit fige la marche le temps de leurs nuanceurs.
  async function poserFigurants({ scene: troupe, animations }, emprises) {
    const textures = texturesDe(troupe);
    // Un figurant se lit sur quelques centaines de pixels au plus : le profil léger ramène ses textures à cette mesure.
    await Promise.all(textures.map((t) => plafonner(t, PROFIL.textures.figurants)));
    const melangeur = new THREE.AnimationMixer(troupe);
    for (const clip of animations) melangeur.clipAction(clip).play();
    melangeur.update(0);
    troupe.updateMatrixWorld(true);
    let rang = 0;
    const membres = troupe.children.map((figurant) => {
      const prise = prendreEnMain(figurant);
      prise.updateMatrixWorld();
      const torches = allumerTorches(figurant, rang);
      rang += torches.length;
      return { figurant, prise, torches, etendue: etendueDe(figurant, prise, emprises, animations) };
    });
    await envoyerTextures(textures);
    await compilerSousLesLampes(troupe);
    return { scene: troupe, melangeur, membres, torches: membres.flatMap((m) => m.torches) };
  }

  // Une lampe posée pendant la compilation change la clé de chaque nuanceur : on recompile jusqu'à ce que l'éclairage n'ait plus bougé.
  async function compilerSousLesLampes(objet) {
    let lampes;
    do {
      lampes = lampesPosees();
      await rendu.compiler(objet);
    } while (lampes !== lampesPosees());
  }

  // Une troupe renvoyée pendant sa descente est libérée à l'arrivée, sans entrer en scène.
  function chargerTroupe(nom) {
    if (chargements[nom]) return chargements[nom];
    const chargement = chargeur.loadAsync(TROUPES[nom].glb).then((glb) => poserFigurants(glb, distributions[nom].emprises)).then((troupe) => {
      if (chargements[nom] !== chargement) return libererTroupe(troupe);
      scene.add(troupe.scene);
      troupe.scene.updateMatrixWorld(true);
      troupes[nom] = troupe;
      alleger(troupe.scene);
      suivreTorches(troupe);
      montrerTroupes();
    });
    chargements[nom] = chargement;
    return chargement;
  }
  // Chaque troupe de parcours pèse des dizaines de textures : gardées toutes, les trois parcours menaient la mémoire GPU de 0,7 à 1,2 Go.
  function libererTroupe({ scene: troupe, melangeur, membres, torches }) {
    scene.remove(troupe);
    for (const { meche } of torches) {
      scene.remove(meche);
      horsGeometrie.splice(horsGeometrie.indexOf(meche), 1);
      meche.material.dispose();
    }
    for (const { prise } of membres) {
      const rang = obstacles.indexOf(prise);
      if (rang >= 0) obstacles.splice(rang, 1);
      prise.geometry.dispose();
    }
    melangeur.stopAllAction();
    melangeur.uncacheRoot(troupe);
    const maillages = [];
    troupe.traverse((o) => { if (o.isMesh && o.material !== PRISE) maillages.push(o); });
    detail.oublier(maillages);
    rendreLaMemoire(maillages);
  }

  function renvoyerTroupe(nom) {
    const troupe = troupes[nom];
    delete chargements[nom];
    delete troupes[nom];
    if (troupe) libererTroupe(troupe);
  }

  function presenterTroupe(voulue) {
    troupePresente = voulue;
    montrerTroupes();
    for (const nom of Object.keys(chargements)) if (nom !== voulue && nom !== TROUPE_LIBRE) renvoyerTroupe(nom);
  }

  // Une carte d'ombre figée garderait l'ombre des figurants à leur pose de départ.
  const ombresPres = (point) => PROFIL.figurants.ombre && troupePresente in troupes
    && EMPRISES_FIGURANTS[troupePresente].some((b) => b.distanceToPoint(point) < PROFIL.ombres.portee);

  function animer(dt) {
    const troupe = troupes[troupePresente];
    if (!troupe) return;
    troupe.melangeur.update(dt);
    suivreTorches(troupe);
  }

  // La voulue descend aussitôt ; elle n'entre en scène qu'à `presenter`, sous le voile.
  function demander(voulue) {
    if (voulue === troupeVoulue) return false;
    troupeVoulue = voulue;
    chargerTroupe(voulue);
    return true;
  }

  return {
    charger: chargerTroupe, demander, presenter: presenterTroupe, montrer: montrerTroupes, relayerHorsDuCadre, animer, ombresPres,
    appeler(noms) { appeles = noms ? new Set(noms) : null; },
    chargements: () => Promise.all(Object.values(chargements)),
    figurantsVus: () => troupes[troupePresente]?.membres.filter((m) => m.figurant.visible).map((m) => m.figurant.name) ?? [],
    reglerLeTemps(t) { troupes[troupePresente]?.melangeur.setTime(t); },
  };
}
