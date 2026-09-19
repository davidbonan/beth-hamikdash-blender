"""Grave les figures des parois du Bayit : une carte de relief et leurs silhouettes.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py                       # l'atlas
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py -- --guides           # les guides
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py -- --tailler timora   # une tuile

« כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » (Melakhim I 6:29), « וְצִפָּה זָהָב מְיֻשָּׁר עַל־הַמְּחֻקֶּה »
(6:35) : la figure est CREUSÉE, et l'or épouse le creusé. Un bas-relief se lit à son
modelé — les volumes qui bombent, les plans qui s'étagent, les sillons qui séparent une
penne de la suivante — et non à sa découpe : une plaque plate au contour parfait reste
un emporte-pièce. Le blockout ne taille donc qu'UN fond par figure, à sa
silhouette ; tout le modelé est ici, dans une carte que ce fond lit par ses UV.

Le modelé lui-même n'est plus dessiné ici. Des contours lissés et des dômes, si juste
soit le motif, sortent en clip-art : chaque partie bombe de la même parabole, chaque
bord est parfait, rien n'est taillé. Ce script DESSINE donc des guides — la composition,
l'iconographie, le cadrage, en dômes et sillons — et les fait tailler par gpt-image-2
(fal.ai, ~0,08 $ la tuile) dans la manière de l'ornement judéen du Second Temple —
ossuaires, portes de 'Houlda, frises hérodiennes — ; les tuiles taillées, dans
`gravures/`, sont la SOURCE : versionnées, parce qu'un modèle ne rend jamais deux fois
la même image. `--guides` redessine les guides dans `gravures/guides/`, `--tailler`
en fait tailler un — avec l'esquisse validée du motif, dans `gravures/esquisses/`, s'il
en a une —, et sans argument l'atlas se compose des tuiles.

Une tuile taillée est un rendu ombré, pas une hauteur : la luminance en donne les
creux et les arêtes (les sillons sont sombres, les crêtes claires), et c'est la
distance au bord qui donne le volume d'ensemble — le bombé de la silhouette.

Écrit `visite/matieres/gravures_2048.webp` — un atlas de quatre tuiles de 1024 : gris =
hauteur du modelé, alpha = masque — et `visite/matieres/gravures.json` : pour chaque
motif, le cadre réel que sa tuile couvre, sa place dans l'atlas, et sa silhouette,
tracée sur le masque même de la carte, pour que la plaque et le modelé coïncident au
pixel. Tout se donne dans le repère de la figure : hauteur 1, axe en u = 0, pied en z = 0.

Le blockout lit le JSON (`_relief_grave`), `visite/matieres.js` lit l'atlas (GRAVURE).
Demande `cwebp` sur le PATH, et FAL_AI_KEY (`.env`) pour tailler. À relancer après
toute modification d'une tuile, puis reconstruire la scène.
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from beit_hamikdash_carte import (RACINE, SORTIE, Planche, bombe, cadrer, distance, ecrire,  # noqa: E402
                                  figure, flouter, lire, silhouette)
from beit_hamikdash_contours import (AILES_DRESSEES, AILES_TENDUES, CROISURE, GAINE_KERUV,  # noqa: E402
                                     JAMBE, LARGEUR_JAMBE, MAINS, REDUCTION_DRESSE, SABOT, aile,
                                     bezier, corolle, ellipse, folioles, largeurs_palme, lisser,
                                     poser_lame, reduire, ruban, symetrique, tete_keruv)

TUILE_PX = 1024
ATLAS_PX = 2 * TUILE_PX
NOM = f"gravures_{ATLAS_PX}"
TUILES = RACINE / "gravures"
GUIDES = TUILES / "guides"
# L'esquisse validée d'un motif, quand il en a une : montrée au modèle avec le guide, elle
# donne la manière — le dessin des plumes, les proportions — que le guide ne porte pas.
ESQUISSES = TUILES / "esquisses"
ESQUISSE = "The second image is the approved design sketch: carve the figure in its manner " \
           "and proportions, but keep the composition and framing of the first image."
# Le relief d'une tuile taillée : la silhouette bombe sur RONDEUR (en part de la hauteur)
# depuis son bord, et la luminance, floutée de GRAIN pour ôter le grain du modèle, y
# ajoute le modelé pour PART_MODELE du tout. Un fond plus noir que SEUIL_FOND est le mur.
RONDEUR, GRAIN, PART_MODELE, SEUIL_FOND = 0.05, 0.004, 0.5, 0.02
# Le cadre d'une figure debout : un peu plus large qu'elle, du dessous du pied au
# dessus de la tête, pour que le fondu du bord n'atteigne jamais la tuile voisine.
CADRE_DEBOUT = (-0.6, -0.1, 0.6, 1.1)
FONDU = 0.005            # en part de la hauteur : 2 cm sur un keruv de paroi
# Simplification de la silhouette, en part de la hauteur : 1,5 cm sur un keruv de paroi,
# 2 cm sur la timora d'un jambage. Le fleuron fait 22 cm et court par centaines : le
# chanfrein et l'export dédoublent chaque sommet, et c'est là que le glb se gagne.
# Les palmes de la timora sont découpées en folioles, et sa silhouette a quintuplé : 0,010
# en ôte un tiers sans en perdre une. Au-delà, les dents s'effacent palme par palme — à
# 0,014 la moitié des palmes est ressortie en lame lisse.
TOLERANCE = {"keruv": 0.005, "keruv_dresse": 0.005, "timora": 0.010, "fleuron": 0.02}


# --- Le keruv : la 'haya de Ye'hezkel, quatre ailes, une jambe, une tête à deux faces. ---

# La gaine des ailes croisées, les mains, la jambe et la tête sont dans
# beit_hamikdash_contours.py : le guide du keruv tissé du rideau est bâti sur le même corps.

# Les niveaux, en unités libres : ce qui est devant est plus haut. L'atlas les ramène
# tous ensemble à [0, 1], et la visite les lit à la même échelle sur tous les motifs.
NIVEAU_AILE, NIVEAU_JAMBE, NIVEAU_GAINE, NIVEAU_MAINS, NIVEAU_TETE = 0.0, 0.30, 0.35, 0.65, 0.65


def ailes_hautes(planche, attache, angle, taille, k=1.0):
    (u, z) = attache
    for sens in (-1, 1):
        def poser_aile(contour):
            return reduire(poser_lame(contour, sens * u, z, angle, taille, sens), k)
        planche.bomber(poser_aile(aile()), NIVEAU_AILE, 1.0, 0.05 * k)
        # Les rémiges : un sillon de chaque entaille du bord de fuite jusqu'au poignet,
        # et l'arc des couvertures qui les recouvre à la racine.
        for n in range(6):
            a = 1.0 - (n + 0.5) / 6
            longueur = 0.18 + 0.26 * a
            entaille = (a + 0.05 + 0.55 * longueur * 0.4, -longueur * 0.42)
            planche.graver(poser_aile([entaille, (0.14, -0.02)]), 0.012 * k, 0.45)
        planche.graver(poser_aile([(0.10, -0.12), (0.40, -0.14), (0.70, -0.12), (0.96, -0.05)]),
                       0.010 * k, 0.35)


def corps_de_keruv(planche, k=1.0):
    planche.bomber(reduire(ellipse(*SABOT), k), NIVEAU_JAMBE + 0.1, 0.8, 0.02 * k)
    planche.bomber(reduire(ruban(JAMBE, LARGEUR_JAMBE), k), NIVEAU_JAMBE, 0.8, 0.02 * k)
    planche.bomber(reduire(lisser(GAINE_KERUV), k), NIVEAU_GAINE, 1.0, 0.08 * k)
    planche.graver(reduire(CROISURE, k), 0.014 * k, 0.5)
    # Les rangs de plumes de la gaine, en chevrons qui descendent vers la jambe.
    for z in (0.74, 0.64, 0.54, 0.44, 0.34, 0.26):
        planche.graver(reduire([(-0.12, z + 0.03), (0.0, z - 0.02), (0.12, z + 0.03)], k), 0.008 * k, 0.3)
    for main in MAINS:
        planche.bomber(reduire(ellipse(*main), k), NIVEAU_MAINS, 0.9, 0.02 * k)
    planche.bomber(reduire(tete_keruv(), k), NIVEAU_TETE, 1.2, 0.05 * k)


def keruv(planche):
    ailes_hautes(planche, *AILES_TENDUES)
    corps_de_keruv(planche)


def keruv_dresse(planche):
    ailes_hautes(planche, *AILES_DRESSEES, REDUCTION_DRESSE)
    corps_de_keruv(planche, REDUCTION_DRESSE)


# --- La timora : une palmette, sept palmes en éventail sur une base en cloche. ----------

# « כּוֹתֶרֶת, דּוֹמֶה לְדֶקֶל » (Rashi sur Ye'hezkel 40:16) et « דמות ענפי אילן וחריותיו »
# (Ralbag sur Melakhim I 6:29) : l'ornement peut n'être que les palmes, sans fût ni
# régimes. Le dattier entier, à 2,9 amot entre deux keruvim, se lisait en dessin d'arbre.
# Chaque palme part droite de la naissance puis s'ouvre en fontaine : (point de contrôle,
# pointe) de la demi-palmette droite, la palme du milieu d'abord. Des palmes en rayons
# droits se lisaient en feuille de chanvre. La dernière paire retombe vers le pied, sous
# les 0,36 de demi-largeur que le dattier tenait.
NAISSANCE = (0.0, 0.18)
BASE = symetrique([(0.0, NAISSANCE[1] + 0.02), (0.05, NAISSANCE[1] + 0.02), (0.035, 0.09),
                   (0.07, 0.0), (0.0, 0.0)])
PALMETTE = (((0.0, 0.60), (0.0, 0.97)), ((0.10, 0.98), (0.26, 0.78)),
            ((0.20, 0.82), (0.36, 0.48)), ((0.26, 0.56), (0.36, 0.20)))
NIVEAU_BASE, NIVEAU_PALME = 0.4, 0.25


def timora(planche):
    for (u1, z1), (u2, z2) in PALMETTE[::-1]:
        for sens in ((1,) if u2 == 0 else (-1, 1)):
            axe = bezier(NAISSANCE, (sens * u1, z1), (sens * u2, z2), 32)
            planche.bomber(folioles(axe, largeurs_palme(len(axe))), NIVEAU_PALME, 1.0, 0.035)
            # La nervure seule : les folioles ne sont plus des arêtes de poisson gravées
            # dans un bord lisse, c'est le contour lui-même qui les découpe.
            planche.graver(axe[3:-9], 0.005, 0.3)
    planche.bomber(BASE, NIVEAU_BASE, 1.0, 0.03)


# --- Le fleuron : la rosette à six pétales, celle des ossuaires de Jérusalem. -----------

# « פְּטוּרֵי צִצִּים » (Melakhim I 6:29), des fleurs qui s'ouvrent. La fleur de l'ornement
# judéen du Second Temple est la rosette tracée au compas — six pétales, sur les
# ossuaires et les linteaux des tombes de Jérusalem. Six, donc, et non huit.
LOBES = 6


def fleuron(planche):
    planche.bomber(corolle(0.0, 0.5, 0.5, LOBES), 0.0, 1.0, 0.12)
    for k in range(LOBES):
        a = math.pi * (2 * k + 1) / LOBES
        planche.graver([(0.10 * math.cos(a), 0.5 + 0.10 * math.sin(a)),
                        (0.40 * math.cos(a), 0.5 + 0.40 * math.sin(a))], 0.022, 0.5)
    planche.bomber(ellipse(0.0, 0.5, 0.13, 0.13), 0.6, 1.0, 0.10)


# --- Les guides, la taille, l'atlas. ------------------------------------------------------

# Ce que l'on demande au modèle pour chaque motif : l'iconographie, mot à mot, parce que
# c'est elle que le guide ne porte qu'à moitié — un crâne à deux profils sans traits
# ne se devine pas d'un dôme.
# La manière est celle de l'ornement judéen du Second Temple — ossuaires, linteaux et
# plafonds des portes de 'Houlda, frises hérodiennes — : plans plats, contours en sillon
# net, arrondi doux, ni muscles ni tiare ni barbe assyrienne.
TAILLE = "Re-sculpt this {sujet} as a genuine hand-carved stone bas-relief in the manner " \
         "of Judean ornament of the Second Temple period (Jerusalem ossuaries, the Huldah " \
         "Gates ceilings, Herodian friezes): flat carved planes, clean grooved outlines, " \
         "gentle rounding, restrained and geometric, no Assyrian, Egyptian or Greek " \
         "traits. Keep exactly this composition and framing: {iconographie} Fine tool " \
         "marks, slightly worn. Pure grayscale on a flat pure black background, " \
         "orthographic front view, no colour, no text."
KERUV = ("an awe-inspiring heavenly being of Ezekiel's vision, NOT a human in clothes and NOT "
         "a Christian angel: no tunic, no garment, no belt, no visible torso. The body is a "
         "tall sheath of feathers made by two lower wings wrapped down and crossed in front "
         "from the shoulders to the shins; two human hands emerge from under them, laid flat "
         "on the sheath. Below it ONE single straight rigid leg without knee, ending in ONE "
         "round calf's hoof, polished like burnished bronze. ONE head carrying TWO faces in "
         "profile, a man's profile looking left and a young lion's profile with a short mane "
         "looking right. IMPORTANT: both faces are perfectly smooth featureless silhouettes, "
         "no eyes, no nose detail, no mouth, no fangs. {ailes} Every wing in rows of small "
         "scale-like coverts, then long overlapping flight feathers. Majestic, hieratic, "
         "severe, in the manner of Israelite and Phoenician ivory carving; no halo, no crown, "
         "no beard, no palm trees, a single figure alone.")
MOTIFS = {
    "keruv": (keruv, CADRE_DEBOUT, (0, 1), "four-winged cherub",
              KERUV.format(ailes="Its two upper wings spread out almost horizontally from the "
                                 "shoulders, long and straight, the tips slightly lifted, the "
                                 "long flight feathers hanging below them in stacked bands.")),
    "keruv_dresse": (keruv_dresse, CADRE_DEBOUT, (1, 0), "four-winged cherub",
                     KERUV.format(ailes="Its two upper wings rise straight up from the "
                                        "shoulders, tall and narrow like two flames, their "
                                        "tips high above the head, the flight feathers long, "
                                        "straight and parallel.")),
    "timora": (timora, CADRE_DEBOUT, (1, 1), "palmette of palm fronds",
               "a fan of exactly seven palm fronds springing from a small bell-shaped base, "
               "with no trunk and no dates: the middle frond upright, the three pairs on "
               "either side curving outward and drooping more and more, the lowest pair "
               "falling back down to the level of the base. IMPORTANT: every frond is deeply "
               "CUT INTO SEPARATE POINTED LEAFLETS along both sides of a grooved midrib, like "
               "a feather or a comb, never a smooth leaf, never a flower petal and never a "
               "stiff Greek anthemion; the leaflets are narrow, straight and angled towards "
               "the tip."),
    "fleuron": (fleuron, (-0.6, -0.1, 0.6, 1.1), (0, 0), "six-petal rosette",
                "an open six-petal compass-drawn rosette filling the frame, as on Jerusalem "
                "ossuaries, a round raised heart in the centre, each petal a carved lobe "
                "with a central rib."),
}


def ombrer(relief, masque):
    """Le guide tel qu'on le montre au modèle : le relief éclairé de haut à gauche, en
    or sur un fond brun — un rendu, que le modèle lit mieux qu'une carte de gris."""
    hauteur = relief * 0.03 * relief.shape[1]
    gz, gu = np.gradient(hauteur)
    normale = np.stack([-gu, -gz, np.ones_like(hauteur)], -1)
    normale /= np.linalg.norm(normale, axis=-1, keepdims=True)
    lumiere = np.array([-0.5, 0.6, 0.62])
    ombre = np.clip(normale @ (lumiere / np.linalg.norm(lumiere)), 0, 1)
    rgb = (0.25 + 0.75 * ombre)[..., None] * np.array([1.0, 0.78, 0.38])
    return np.where(masque[..., None] > 0.5, rgb, np.array([0.40, 0.32, 0.18]))


def guider(nom):
    tailler, cadre, _, _, _ = MOTIFS[nom]
    planche = Planche(cadre, TUILE_PX)
    tailler(planche)
    relief, masque = planche.relief(FONDU)
    rgb = ombrer(relief / relief.max(), masque)
    image = bpy.data.images.new(nom, rgb.shape[1], rgb.shape[0], alpha=False)
    image.pixels.foreach_set(np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,))], -1)
                             .astype(np.float32).ravel())
    GUIDES.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(GUIDES / f"{nom}.png")
    image.file_format = "PNG"
    image.save()
    print(f"  {nom:8s} guide : {image.filepath_raw}")


def tailler(nom):
    """Fait tailler le guide de `nom` par gpt-image-2 et pose la tuile dans `gravures/`."""
    sys.path.insert(0, str(RACINE / ".claude" / "skills" / "fal-video"))
    import fal_commun  # noqa: E402
    _, _, _, sujet, iconographie = MOTIFS[nom]
    cle = fal_commun.cle_api()
    esquisse = ESQUISSES / f"{nom}.png"
    images = [GUIDES / f"{nom}.png"] + ([esquisse] if esquisse.exists() else [])
    prompt = TAILLE.format(sujet=sujet, iconographie=iconographie)
    corps = {"prompt": prompt + (" " + ESQUISSE if len(images) > 1 else ""),
             "image_urls": [fal_commun.televerse(str(image), cle) for image in images],
             "image_size": "square_hd", "quality": "high", "output_format": "png"}
    reponse = fal_commun.genere("openai/gpt-image-2/edit", corps, cle)
    fal_commun.telecharge(reponse["images"][0]["url"], str(TUILES / f"{nom}.png"))
    print(f"  {nom:8s} taillé : gravures/{nom}.png")


def relief_taille(nom):
    """(relief, masque) d'une tuile taillée, posés dans le cadre du motif."""
    _, cadre, _, _, _ = MOTIFS[nom]
    luminance = lire(TUILES / f"{nom}.png")
    luminance, masque = cadrer(luminance, figure(luminance > SEUIL_FOND), cadre, TUILE_PX)
    echelle = TUILE_PX / (cadre[2] - cadre[0])
    rayon = max(1, int(round(RONDEUR * echelle)))
    volume = bombe(distance(masque, rayon) / rayon)
    modele = flouter(luminance, max(1, int(round(GRAIN * echelle))))
    bas, haut = modele[masque].min(), modele[masque].max()
    modele = np.clip((modele - bas) / (haut - bas), 0.0, 1.0)
    relief = np.where(masque, (1.0 - PART_MODELE) * volume + PART_MODELE * modele, 0.0)
    return flouter(relief, max(1, int(round(FONDU * echelle)))).astype(np.float32), masque


def graver():
    atlas = np.zeros((ATLAS_PX, ATLAS_PX), dtype=np.float32)
    masque = np.zeros((ATLAS_PX, ATLAS_PX), dtype=np.float32)
    fiche = {"pixels": ATLAS_PX, "motifs": {}}
    for nom, (_, cadre, (colonne, ligne), _, _) in MOTIFS.items():
        relief, dedans = relief_taille(nom)
        l0, c0 = ligne * TUILE_PX, colonne * TUILE_PX
        atlas[l0:l0 + TUILE_PX, c0:c0 + TUILE_PX] = relief
        masque[l0:l0 + TUILE_PX, c0:c0 + TUILE_PX] = dedans
        contour = silhouette(dedans, cadre[:2], TUILE_PX / (cadre[2] - cadre[0]), TOLERANCE[nom])
        fiche["motifs"][nom] = {"cadre": cadre, "tuile": [colonne * 0.5, ligne * 0.5, 0.5],
                                "silhouette": [[round(u, 4), round(z, 4)] for u, z in contour]}
        print(f"  {nom:8s} silhouette : {len(contour)} sommets, modelé jusqu'à {relief.max():.2f}")
    atlas /= atlas.max()
    ecrire(NOM, atlas, masque)
    (SORTIE / "gravures.json").write_text(json.dumps(fiche, separators=(",", ":")), encoding="utf-8")


ARGUMENTS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if ARGUMENTS[:1] == ["--guides"]:
    for nom in ARGUMENTS[1:] or MOTIFS:
        guider(nom)
elif ARGUMENTS[:1] == ["--tailler"]:
    for nom in ARGUMENTS[1:] or MOTIFS:
        tailler(nom)
else:
    graver()
