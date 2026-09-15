"""Grave les trois figures des parois du Bayit : une carte de relief et leurs silhouettes.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py                       # l'atlas
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py -- --guides           # les guides
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py -- --tailler timora   # une tuile

« כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » (Melakhim I 6:29), « וְצִפָּה זָהָב מְיֻשָּׁר עַל־הַמְּחֻקֶּה »
(6:35) : la figure est CREUSÉE, et l'or épouse le creusé. Un bas-relief se lit à son
modelé — les volumes qui bombent, les plans qui s'étagent, les sillons qui séparent une
penne de la suivante — et non à sa découpe : une plaque plate au contour parfait reste
un emporte-pièce. Le blockout ne pose donc plus qu'UNE plaque par figure, à sa
silhouette ; tout le modelé est ici, dans une carte que la plaque lit par ses UV.

Le modelé lui-même n'est plus dessiné ici. Des contours lissés et des dômes, si juste
soit le motif, sortent en clip-art : chaque partie bombe de la même parabole, chaque
bord est parfait, rien n'est taillé. Ce script DESSINE donc des guides — la composition,
l'iconographie, le cadrage, en dômes et sillons — et les fait tailler par gpt-image-2
(fal.ai, ~0,08 $ la tuile) dans la manière de l'ornement judéen du Second Temple —
ossuaires, portes de 'Houlda, frises hérodiennes — ; les tuiles taillées, dans
`gravures/`, sont la SOURCE : versionnées, parce qu'un modèle ne rend jamais deux fois
la même image. `--guides` redessine les guides dans `gravures/guides/`, `--tailler`
en fait tailler un, et sans argument l'atlas se compose des tuiles.

Une tuile taillée est un rendu ombré, pas une hauteur : la luminance en donne les
creux et les arêtes (les sillons sont sombres, les crêtes claires), et c'est la
distance au bord qui donne le volume d'ensemble — le bombé de la silhouette.

Écrit `visite/matieres/gravures_2048.webp` — un atlas de trois tuiles de 1024 : gris =
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
from beit_hamikdash_contours import (TETE_DOUBLE, aile, corolle, ellipse, lisser,  # noqa: E402
                                     poser, poser_lame, symetrique)

TUILE_PX = 1024
ATLAS_PX = 2 * TUILE_PX
NOM = f"gravures_{ATLAS_PX}"
TUILES = RACINE / "gravures"
GUIDES = TUILES / "guides"
# Le relief d'une tuile taillée : la silhouette bombe sur RONDEUR (en part de la hauteur)
# depuis son bord, et la luminance, floutée de GRAIN pour ôter le grain du modèle, y
# ajoute le modelé pour PART_MODELE du tout. Un fond plus noir que SEUIL_FOND est le mur.
RONDEUR, GRAIN, PART_MODELE, SEUIL_FOND = 0.05, 0.004, 0.5, 0.02
# Le cadre d'une figure debout : un peu plus large qu'elle, du dessous du pied au
# dessus de la tête, pour que le fondu du bord n'atteigne jamais la tuile voisine.
CADRE_DEBOUT = (-0.6, -0.1, 0.6, 1.1)
FONDU = 0.005            # en part de la hauteur : 2 cm sur un keruv de paroi
# Simplification de la silhouette, en part de la hauteur : 1,5 cm sur un keruv de paroi,
# 1 cm sur la timora d'un jambage. Le fleuron fait 22 cm et court par centaines : le
# chanfrein et l'export dédoublent chaque sommet, et c'est là que le glb se gagne.
TOLERANCE = {"keruv": 0.005, "timora": 0.005, "fleuron": 0.02}


# --- Les rubans : bras, palmes. ------------------------------------------------------

def bezier(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (k / (n - 1) for k in range(n))]


def normales(axe):
    """La normale unitaire en chaque point d'une ligne brisée, moyenne des deux segments."""
    n = []
    for k, (u, z) in enumerate(axe):
        (u0, z0), (u1, z1) = axe[max(0, k - 1)], axe[min(len(axe) - 1, k + 1)]
        du, dz = u1 - u0, z1 - z0
        l = math.hypot(du, dz) or 1.0
        n.append((-dz / l, du / l))
    return n


def ruban(axe, largeurs):
    """Le contour d'un ruban le long de `axe`, de demi-largeur `largeurs[k]` au point k."""
    n = normales(axe)
    gauche = [(u + nu * w, z + nz * w) for (u, z), (nu, nz), w in zip(axe, n, largeurs)]
    droite = [(u - nu * w, z - nz * w) for (u, z), (nu, nz), w in zip(axe, n, largeurs)]
    return gauche + droite[::-1]


# --- Le keruv : debout, de face, deux ailes levées, un crâne à deux profils. ------------

# Le corps vêtu, sans les bras : cou, épaules, poitrine, taille, hanches, robe évasée
# jusqu'à l'ourlet. Moitié droite, du haut du cou à l'axe de l'ourlet. Le
# CORPS_DRESSE du rideau était sans épaules ni cou : une figure de trois mètres se
# lisait en mannequin de couturière. Le cou monte DANS le crâne, qui le recouvre :
# arrêté dessous, le lissage le rognait et la tête flottait.
# Les proportions sont celles d'un ENFANT — « כְּרוּב : כְּרַבְיָא » (Soucca 5b, Rashi Ex. 25:18) :
# la tête fait un cinquième de la hauteur, les épaules tombent à 0,74, non 0,80.
CORPS_KERUV = symetrique([
    (0.000, 0.860), (0.050, 0.860), (0.055, 0.750), (0.165, 0.730), (0.185, 0.680),
    (0.165, 0.600), (0.140, 0.540), (0.155, 0.470), (0.180, 0.400), (0.210, 0.250),
    (0.230, 0.100), (0.235, 0.030), (0.000, 0.030)])
# Le bras droit, le long du corps et un peu fléchi : épaule, coude, poignet.
BRAS = ((0.150, 0.710), (0.200, 0.580), (0.165, 0.440))
LARGEURS_BRAS = (0.052, 0.046, 0.036)
# Les plis de la robe partent de la ceinture et s'écartent vers l'ourlet.
PLIS = (-1.0, -0.5, 0.0, 0.5, 1.0)

# Les niveaux, en unités libres : ce qui est devant est plus haut. L'atlas les ramène
# tous ensemble à [0, 1], et la visite les lit à la même échelle sur les trois motifs.
NIVEAU_AILE, NIVEAU_CORPS, NIVEAU_BRAS, NIVEAU_TETE = 0.0, 0.35, 0.65, 0.65
# Les ailes s'ouvrent à 40° : serrées contre le corps elles se cachaient derrière la tête
# et se lisaient en bois de cerf. Leur pointe reste sous le haut de la tuile.
ANGLE_AILE, TAILLE_AILE = 40, 0.40


def keruv(planche):
    for sens in (-1, 1):
        u_aile, z_aile = sens * 0.12, 0.66
        contour = poser_lame(aile(), u_aile, z_aile, ANGLE_AILE, TAILLE_AILE, sens)
        planche.bomber(contour, NIVEAU_AILE, 1.0, 0.05)
        # Les rémiges : un sillon de chaque entaille du bord de fuite jusqu'au poignet,
        # et l'arc des couvertures qui les recouvre à la racine.
        for k in range(6):
            a = 1.0 - (k + 0.5) / 6
            longueur = 0.18 + 0.26 * a
            entaille = (a + 0.05 + 0.55 * longueur * 0.4, -longueur * 0.42)
            sillon = poser_lame([entaille, (0.14, -0.02)], u_aile, z_aile, ANGLE_AILE, TAILLE_AILE, sens)
            planche.graver(sillon, 0.012, 0.45)
        couvertures = poser_lame([(0.10, -0.12), (0.40, -0.14), (0.70, -0.12), (0.96, -0.05)],
                                 u_aile, z_aile, ANGLE_AILE, TAILLE_AILE, sens)
        planche.graver(couvertures, 0.010, 0.35)
    for sens in (-1, 1):
        planche.bomber(ellipse(sens * 0.075, 0.02, 0.05, 0.03), NIVEAU_CORPS, 0.8, 0.02)
    planche.bomber(lisser(CORPS_KERUV), NIVEAU_CORPS, 1.0, 0.10)
    planche.graver([(-0.14, 0.50), (0.0, 0.49), (0.14, 0.50)], 0.014, 0.5)
    for s in PLIS:
        planche.graver([(0.09 * s, 0.47), (0.15 * s, 0.25), (0.20 * s, 0.04)], 0.012, 0.45)
    for sens in (-1, 1):
        axe = [(sens * u, z) for u, z in BRAS]
        planche.bomber(lisser(ruban(axe, LARGEURS_BRAS), passes=2), NIVEAU_BRAS, 0.9, 0.04)
        planche.bomber(ellipse(sens * 0.150, 0.415, 0.038, 0.048), NIVEAU_BRAS, 0.9, 0.03)
    # Le crâne à deux profils, un peu resserré, et lissé UNE fois : trois passes en
    # faisaient une miche, et c'est le nez et le menton de chaque profil qui le font lire.
    t = 0.148
    tete = [(0.85 * u, z) for u, z in TETE_DOUBLE]
    planche.bomber(lisser(poser(tete, 0.0, 0.868, t), passes=1), NIVEAU_TETE, 1.2, 0.05)
    planche.graver([(-0.10, 0.92), (0.0, 0.932), (0.10, 0.92)], 0.010, 0.4)


# --- La timora : le dattier, tel que la tradition le lit et le frappe. -----------------

# « וְתִמֹרֹת » (Melakhim I 6:29) : Rashi et Radak lisent דקלים, des palmiers-dattiers, et
# la fiche (§8c-bis) en fixe sept palmes. Son image juive est celle des monnaies de
# Bar Kokhba : un fût droit à écailles, sept palmes — celle du milieu dressée, les
# paires suivantes qui ploient en arc —, et deux régimes de dattes qui pendent de la
# couronne, de part et d'autre du fût. Ni volutes ni collier : c'était la palmette
# assyrienne, étrangère à cette tradition. La silhouette des palmes reste LISSE, les
# folioles ne sont que des sillons qui s'arrêtent avant le bord.
FUT = 0.56
TRONC = symetrique([(0.0, FUT), (0.045, FUT), (0.052, 0.10), (0.065, 0.035), (0.09, 0.0), (0.0, 0.0)])
ECAILLE = 0.045                          # pas des losanges du fût
COURONNE = (0.0, FUT - 0.01)
# (inclinaison sur la verticale, longueur, retombée) : la palme du milieu se dresse, les
# paires suivantes ploient de plus en plus, la dernière retombe sous l'horizontale.
PALMES = ((0, 0.42, 0.0), (28, 0.42, 0.18), (60, 0.40, 0.42), (95, 0.34, 0.55))
REGIME = ((0.0, 0.0, 0.026), (-0.028, -0.030, 0.023), (0.028, -0.030, 0.023),
          (-0.040, -0.065, 0.020), (0.0, -0.060, 0.021), (0.040, -0.065, 0.020),
          (-0.018, -0.095, 0.017), (0.018, -0.095, 0.017), (0.0, -0.122, 0.014))
ATTACHE_REGIME = (0.085, FUT - 0.05)
NIVEAU_FUT, NIVEAU_PALME, NIVEAU_REGIME = 0.4, 0.25, 0.55


def palme(inclinaison, longueur, retombee):
    a = math.radians(inclinaison)
    p0 = COURONNE
    p1 = (p0[0] + 0.5 * longueur * math.sin(a), p0[1] + 0.5 * longueur * math.cos(a))
    p2 = (p0[0] + longueur * math.sin(a), p0[1] + longueur * (math.cos(a) - retombee))
    axe = bezier(p0, p1, p2, 32)
    n = len(axe) - 1
    largeurs = [0.005 + 0.062 * (1.0 - k / n) ** 0.55 * min(1.0, 0.45 + 4.0 * k / n)
                for k in range(len(axe))]
    return axe, largeurs


def nervures(planche, axe, largeurs):
    """La nervure médiane, et les folioles en arête de poisson, qui s'arrêtent bien avant
    le bord de la palme : c'est le bord dentelé qui faisait la scie."""
    planche.graver(axe[2:-2], 0.006, 0.3)
    n = normales(axe)
    for k in range(4, len(axe) - 3, 2):
        (u, z), (nu, nz), w = axe[k], n[k], largeurs[k]
        (u1, z1) = axe[k + 1]
        tu, tz = u1 - u, z1 - z
        l = math.hypot(tu, tz) or 1.0
        for cote in (-1, 1):
            planche.graver([(u, z), (u + cote * nu * w * 0.6 + tu / l * 0.7 * w,
                                     z + cote * nz * w * 0.6 + tz / l * 0.7 * w)], 0.005, 0.3)


def timora(planche):
    planche.bomber(TRONC, NIVEAU_FUT, 1.0, 0.05)
    for k in range(-3, 14):
        z = ECAILLE * k
        for sens in (-1, 1):
            planche.graver([(sens * -0.08, z), (sens * 0.08, z + 0.16)], 0.006, 0.35)
    for inclinaison, longueur, retombee in PALMES[::-1]:
        for sens in ((1,) if inclinaison == 0 else (-1, 1)):
            axe, largeurs = palme(sens * inclinaison, longueur, retombee)
            planche.bomber(lisser(ruban(axe, largeurs), passes=2), NIVEAU_PALME, 1.0, 0.035)
            nervures(planche, axe, largeurs)
    for sens in (-1, 1):
        # La tige du régime part de la couronne ; les dattes pendent le long du fût.
        planche.bomber(ruban([(sens * 0.03, FUT + 0.01), (sens * ATTACHE_REGIME[0], ATTACHE_REGIME[1] + 0.02)],
                             [0.012, 0.010]), NIVEAU_REGIME, 0.7, 0.01)
        for du, dz, r in REGIME:
            planche.bomber(ellipse(sens * ATTACHE_REGIME[0] + du, ATTACHE_REGIME[1] + dz, r * 0.9, r * 1.3),
                           NIVEAU_REGIME, 0.7, 0.015)


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
MOTIFS = {
    "keruv": (keruv, CADRE_DEBOUT, (0, 1), "winged child figure",
              "a standing child seen from the front, child-like proportions with a large "
              "round head, a plain long tunic with simple vertical folds down to the feet, "
              "a belt, arms along the body with hands visible, two large wings raised on "
              "either side with clearly separated layered feathers, and ONE single head "
              "carrying TWO faces in profile, one looking left and one looking right "
              "(Janus-like), with a plain headband, no beard, no crown. IMPORTANT: the "
              "faces are left perfectly smooth and blank, with no eyes, no nose, no mouth."),
    "timora": (timora, CADRE_DEBOUT, (1, 1), "date palm tree, as on the Bar Kokhba coins",
               "a straight trunk with scale pattern, flared foot, a crown of exactly seven "
               "fronds — the middle one upright, the others bending down in smooth arcs —, "
               "and two clusters of dates hanging from the crown on either side of the trunk."),
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
    corps = {"prompt": TAILLE.format(sujet=sujet, iconographie=iconographie),
             "image_urls": [fal_commun.televerse(str(GUIDES / f"{nom}.png"), cle)],
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
