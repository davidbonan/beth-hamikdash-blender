"""Tisse le motif des deux Parokhot : une carte que la matière lit, pas des volumes.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_parokhet.py                     # la carte
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_parokhet.py -- --guides         # les guides
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_parokhet.py -- --tisser lion    # une figure

« מַעֲשֵׂה חֹשֵׁב יַעֲשֶׂה אֹתָהּ כְּרֻבִים » (Ex. 26:31) : créatures ailées et lions en alternance,
tissés dans les mêmes quatre laines — jamais d'or (le verset n'en liste que quatre),
jamais brodés, et sans un visage humain (§9 de la fiche). Une figure TISSÉE n'est pas
un volume : elle bombe l'étoffe de quelques centimètres et s'en distingue par la FACE
du tissage qui la montre — « אֲרִיגָה שֶׁל שְׁתֵּי קִירוֹת » (Rashi, ibid.), deux parois de
fils dont l'une passe devant l'autre là où le dessin le veut. Chaque cordon porte les
quatre laines (Shekalim 8:5) ; ce qui change d'une face à l'autre, c'est celle qui
affleure : le fond montre ses tekhelet et argaman, la figure ses lin et tola'at shani.
Le lion de la Porte d'Ishtar, blanc et fauve sur l'émail bleu, en est le contemporain.

Les figures ne sont plus dessinées ici. Des contours lissés en aplats, si juste soit
le motif, sortaient en autocollants : chaque partie d'une seule couleur, chaque bord
parfait, rien de tissé. Ce script DESSINE donc des guides — la composition, la pose,
les couleurs, le cadrage — et les fait tisser par gpt-image-2 (fal.ai, ~0,08 $ la
figure) dans la manière des tapisseries de l'Orient ancien ; les figures tissées,
dans `tissages/`, sont la SOURCE : versionnées, parce qu'un modèle ne rend jamais
deux fois la même image. `--guides` redessine les guides dans `tissages/guides/`,
`--tisser` en fait tisser un, et sans argument la carte se compose des figures.

Une figure tissée est une image en couleur sur fond vert : sa couleur, en chaque
point, se ramène à la face du tissage la plus proche — le point du carré (clarté,
rougeur) dont la laine dosée lui ressemble le plus —, et sa luminance donne le
modelé, la distance au bord le bombé d'ensemble, comme pour une gravure.

Écrit `visite/matieres/parokhet_2048.webp`, une carte de 20 amot sur 40 — le rideau
entier, lu par la position de monde (y, z) : R porte la HAUTEUR du bombé, G la CLARTÉ
de la face (0 les laines sombres, 1 le lin), B sa ROUGEUR (0 tekhelet, 1 tola'at
shani), alpha le MASQUE de la figure. Deux axes de dosage plutôt qu'un index de face :
un index ne survit pas au filtrage — entre un lion clair et le fond, la moyenne des
deux textures voisines tombait sur une troisième couleur ; un dosage moyenné reste
un dosage. Et `visite/matieres/parokhet.json` : les quatre laines, les dosages des
faces et la palette qui en sort, que le blockout lit (`parokhet()`) ; la visite
(`visite/matieres.js`) porte la même palette en constantes. Le WebP est sans perte
(`beit_hamikdash_carte.py`). Demande `cwebp` sur le PATH, et FAL_AI_KEY (`.env`) pour
tisser. À relancer après toute modification d'une figure, puis reconstruire.
"""
import json
import pathlib
import sys

import bpy
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from beit_hamikdash_carte import (RACINE, SORTIE, bombe, cadrer, distance, ecrire, figure,  # noqa: E402
                                  flouter, lire_rgb, reechantillonner, remplir)
from beit_hamikdash_contours import (BRAS, CORPS_KERUV, LARGEURS_BRAS, PLIS, TETE_DOUBLE,  # noqa: E402
                                     aile, corolle, courbe, ellipse, lisser, poser, poser_lame,
                                     ruban)

LARGEUR_PX = 2048
NOM = f"parokhet_{LARGEUR_PX}"
TUILE_PX = 1024
TISSAGES = RACINE / "tissages"
GUIDES = TISSAGES / "guides"

# « אָרְכָּהּ אַרְבָּעִים אַמָּה וְרָחְבָּהּ עֶשְׂרִים אַמָּה » (Shekalim 8:5) : la carte est le rideau.
LARGEUR, HAUTEUR = 20.0, 40.0
CHAMP = (2.0, 38.0)       # bas et haut du champ figuré, en amot depuis le bas du rideau
RANGS, COLONNES = 6, 4
PART_FIGURE = 0.78        # hauteur d'une figure, au plus, en part du rang
PART_COLONNE = 0.92       # largeur d'une figure, au plus, en part de sa colonne
LISIERE = 0.9             # largeur de la lisière qui borde le champ
LISTEL = 0.10             # les deux filets clairs qui bordent la lisière
# Le bombé se fond sur 4 cm : c'est un fil qui passe par-dessus, pas une arête.
FONDU = 0.04
SURECHANTILLON = 2
# Le relief d'une figure tissée : la silhouette bombe sur RONDEUR (en part de la
# hauteur) depuis son bord, et la luminance, floutée de GRAIN pour ôter le grain du
# modèle, y ajoute le modelé pour PART_MODELE du tout — moins que sur une gravure :
# un fil couché ne creuse pas comme un ciseau.
RONDEUR, GRAIN, PART_MODELE = 0.06, 0.004, 0.35
# Le fond vert du modèle : ce qui n'est pas la figure. Il le rend texturé et parfois
# sombre ; c'est donc la DOMINANCE du vert qui le reconnaît, d'au moins VERT sur le
# rouge et sur le bleu (valeurs du fichier) — aucune laine n'est verte.
VERT = 0.12

# Les quatre laines (Shekalim 8:5 ; Rashi Ex. 26:31), en linéaire : tekhelet, argaman,
# tola'at shani, lin — et les FACES du tissage, en dosage de ces quatre laines, aux
# coins d'un carré (clarté, rougeur) que la carte parcourt : le fond bleu-violet, le
# chaud cramoisi, le clair de lin, et le coin lin-cramoisi qu'un fondu atteint. Aucun
# dosage n'est pur : un rouge de tola'at seule et un lin blanc sur le violet faisaient
# un drapeau, pas une tapisserie — les teintes d'un lainage se tiennent de près.
LAINES = (("tekhelet", (0.10, 0.17, 0.48)), ("argaman", (0.40, 0.08, 0.30)),
          ("shani", (0.55, 0.08, 0.08)), ("lin", (0.86, 0.84, 0.78)))
DOSAGES = {"fond": (0.50, 0.42, 0.08, 0.00), "chaud": (0.10, 0.35, 0.50, 0.05),
           "clair": (0.05, 0.05, 0.20, 0.70), "clair_chaud": (0.00, 0.10, 0.45, 0.45)}
JOUR = 0.75   # la laine teinte absorbe : le jour d'une étoffe lourde, sur les quatre faces
PALETTE = {face: tuple(JOUR * sum(p * rgb[k] for p, (_, rgb) in zip(parts, LAINES)) for k in range(3))
           for face, parts in DOSAGES.items()}
FOND, POURPRE, CHAUD, CLAIR = (0.0, 0.0), (0.0, 0.5), (0.0, 1.0), (1.0, 0.0)
# Un trait intérieur — ceinture, épaule, hanche — est un fil du fond qui repasse sur la
# figure : plus bas qu'elle, et de sa couleur à elle, le fond.
TRAIT, BOMBE_TRAIT = 0.03, 0.45


def couleur_face(clarte, rougeur):
    """La couleur linéaire d'un point du carré des faces : bilinéaire entre les coins."""
    coins = np.array([[PALETTE["fond"], PALETTE["chaud"]], [PALETTE["clair"], PALETTE["clair_chaud"]]])
    c, r = np.asarray(clarte)[..., None], np.asarray(rougeur)[..., None]
    return (1 - c) * ((1 - r) * coins[0, 0] + r * coins[0, 1]) + c * ((1 - r) * coins[1, 0] + r * coins[1, 1])


# --- Les guides des deux motifs. Chaque partie : (contour, hauteur du bombé, face). Les
# parties se posent dans l'ordre, chacune couvrant les précédentes. Dans le repère de la
# figure : hauteur 1, axe en u = 0, pied en z = 0. ---

def creature_ailee():
    """Créature ailée de face — la figure même du keruv des parois (beit_hamikdash_gravures.py) :
    corps d'enfant, bras le long du corps, robe à plis, tête double sans traits, deux
    ailes levées. « כְּרֻבִים » de Ex. 26:31 vaut « צִיּוּרִין שֶׁל בְּרִיּוֹת » (Rashi) ; la tête —
    « וּשְׁנַיִם פָּנִים לַכְּרוּב » (Ye'hezkel 41:18) —, un profil de chaque côté. Robe cramoisie,
    ailes de lin aux couvertures pourpres, bras et tête de lin, ceinture et plis du fond."""
    parties = []
    for sens in (-1, 1):
        u_aile, z_aile = sens * 0.12, 0.66
        parties.append((poser_lame(aile(), u_aile, z_aile, 40, 0.40, sens), 0.85, CLAIR))
        parties.append((poser_lame(aile(5), u_aile, z_aile, 36, 0.20, sens), 1.0, POURPRE))
    for sens in (-1, 1):
        parties.append((ellipse(sens * 0.075, 0.02, 0.05, 0.03), 0.8, CLAIR))
    parties.append((lisser(CORPS_KERUV), 0.75, CHAUD))
    parties.append((ruban([(-0.14, 0.50), (0.0, 0.49), (0.14, 0.50)], TRAIT), BOMBE_TRAIT, FOND))
    for s in PLIS:
        parties.append((ruban([(0.09 * s, 0.47), (0.15 * s, 0.25), (0.20 * s, 0.04)], TRAIT * 0.6),
                        BOMBE_TRAIT, FOND))
    for sens in (-1, 1):
        parties.append((lisser(ruban([(sens * u, z) for u, z in BRAS], sum(LARGEURS_BRAS) / 1.5), passes=2),
                        0.9, CLAIR))
        parties.append((ellipse(sens * 0.150, 0.415, 0.038, 0.048), 0.9, CLAIR))
    # Le crâne à deux profils, un peu resserré, lissé UNE fois : c'est le nez et le menton
    # de chaque profil qui le font lire.
    parties.append((lisser(poser([(0.85 * u, z) for u, z in TETE_DOUBLE], 0.0, 0.868, 0.148), passes=1),
                    1.0, CLAIR))
    return parties


# Le lion marchant des frises d'Orient : corps long, dos presque droit, poitrail
# profond, ventre relevé, queue en S ramenée au-dessus de la croupe. Il regarde vers
# les u croissants.
LION_CORPS = ((0.40, 0.58), (0.44, 0.66), (0.36, 0.72), (0.22, 0.75), (0.02, 0.74),
              (-0.18, 0.72), (-0.36, 0.71), (-0.50, 0.66), (-0.56, 0.56), (-0.54, 0.44),
              (-0.46, 0.36), (-0.30, 0.33), (-0.10, 0.32), (0.10, 0.33), (0.28, 0.36),
              (0.40, 0.44))
# Front, oreille, mufle, et l'entaille de la gueule entrouverte sous le nez.
LION_TETE = ((0.36, 0.56), (0.40, 0.70), (0.48, 0.80), (0.55, 0.87), (0.61, 0.84),
             (0.65, 0.78), (0.75, 0.77), (0.84, 0.72), (0.88, 0.64), (0.84, 0.58),
             (0.74, 0.57), (0.80, 0.52), (0.72, 0.47), (0.60, 0.47), (0.48, 0.50))
LION_QUEUE = ((-0.48, 0.64), (-0.58, 0.70), (-0.65, 0.80), (-0.63, 0.90), (-0.55, 0.95))
# Une patte : cuisse, genou, canon, et la patte qui s'élargit au sol, (u de l'axe, z).
LION_PATTE = ((-0.055, 0.38), (0.055, 0.38), (0.040, 0.20), (0.030, 0.08), (0.075, 0.0),
              (-0.065, 0.0), (-0.035, 0.08), (-0.055, 0.20))
# (axe, foulée, hauteur du bombé) : les deux pattes du côté du regard sont en pleine
# marche, les deux autres passent derrière, un peu plus bas dans l'étoffe.
LION_PATTES = ((0.22, -0.05, 0.60), (-0.30, 0.05, 0.60), (0.34, 0.08, 0.75), (-0.42, -0.08, 0.75))
# Les traits du fond qui dessinent l'épaule et la hanche sur le corps clair.
LION_TRAITS = (((0.14, 0.38), (0.21, 0.48), (0.17, 0.60), (0.06, 0.67)),
               ((-0.26, 0.36), (-0.22, 0.46), (-0.29, 0.58), (-0.42, 0.65)))


def lion():
    """Le lion de la frise — « וּפְנֵי כְפִיר » (Ye'hezkel 41:19), et le lion du revers d'un
    maassé 'hoshev (Rashi sur Yoma 72b). De profil, marchant : corps de lin, crinière
    et houppe cramoisies."""
    parties = []
    for axe, foulee, hauteur in LION_PATTES:
        patte = [(axe + du + foulee * (1.0 - dz / 0.38), dz) for du, dz in LION_PATTE]
        parties.append((lisser(patte, passes=2), hauteur, CLAIR))
    parties += [(lisser(LION_CORPS, passes=2), 0.75, CLAIR),
                (ellipse(-0.40, 0.45, 0.13, 0.11), 0.75, CLAIR),
                (ruban(courbe(LION_QUEUE), 0.045), 0.70, CLAIR),
                (ellipse(-0.53, 0.96, 0.07, 0.055), 0.80, CHAUD),
                (corolle(0.40, 0.66, 0.27, 16), 0.90, CHAUD),
                (corolle(0.34, 0.50, 0.17, 12), 0.90, CHAUD),
                (lisser(LION_TETE, passes=1), 1.0, CLAIR)]
    for trait in LION_TRAITS:
        parties.append((ruban(courbe(trait), TRAIT), BOMBE_TRAIT, FOND))
    return parties


# Ce que l'on demande au modèle pour chaque motif : l'iconographie mot à mot, parce que
# c'est elle que le guide ne porte qu'à moitié. La manière est celle des tapisseries de
# l'Orient ancien — laines plates, contours en fil, dessin intérieur en fils contrastés.
TISSAGE = "Re-weave this {sujet} as a genuine ancient Near-Eastern woven wool tapestry " \
          "figure of the Iron Age (in the spirit of the Ishtar Gate lions, Pazyryk textiles, " \
          "Phoenician and Syrian tapestry): flat woven wool with a visible fine weft, bold " \
          "simplified outlines in a darker thread, decorative interior patterning in " \
          "contrasting threads, stylised and geometric, no shading, no gold, no yellow, no " \
          "green, no black. Use ONLY these wool colours: deep blue-violet, purple, crimson, " \
          "and ivory linen. Keep exactly this composition, pose, proportions and framing: " \
          "{iconographie} Flat pure bright green (#00FF00) background all around the figure, " \
          "orthographic front view, no text, no border, no frame."
# (guide, cadre carré autour de la figure, largeur en part de la hauteur, sujet, iconographie)
MOTIFS = {
    "creature": (creature_ailee, (-0.6, -0.1, 0.6, 1.1), 1.10, "winged child figure",
                 "a standing child seen from the front, child-like proportions with a large "
                 "head, a long plain crimson tunic with a patterned belt and simple vertical "
                 "folds down to the feet, arms along the body with ivory hands visible, two "
                 "large wings of ivory linen raised on either side with clearly separated rows "
                 "of feathers and purple covert feathers at the root, and ONE single ivory head "
                 "carrying TWO faces in profile, one looking left and one looking right "
                 "(Janus-like), with a plain headband, no hair, no beard. IMPORTANT: the faces "
                 "are perfectly smooth and blank, with no eyes, no nose, no mouth."),
    "lion": (lion, (-0.80, -0.25, 0.90, 1.45), 1.52, "striding lion",
             "a lion in profile walking to the right, body of ivory linen, a full crimson "
             "mane in stylised locks around the head and chest, a half-open muzzle, a small "
             "ear, four legs in stride with the paws on the ground, a long tail curving up "
             "in an S over the rump ending in a crimson tuft, shoulder and haunch drawn as "
             "lines in the violet ground thread."),
}


# --- La lisière et la frise : ce qui reste dessiné ici. ---

def rosace(u, z):
    """Une rosace de la lisière : le ציץ des parois (I Rois 6:29) repris en bordure — un
    CHOIX ; corolle de lin, cœur cramoisi."""
    return [(corolle(u, z, 0.26, 8), 0.80, CLAIR), (ellipse(u, z, 0.08, 0.08), 0.65, CHAUD)]


def lisiere():
    """La bordure : un champ pourpre entre deux filets de lin, semé de rosaces."""
    z0, z1 = CHAMP
    L, F, g, d = LISIERE, LISTEL, -LARGEUR / 2, LARGEUR / 2
    bas, haut = z0 - L, z1 + L
    parties = []
    for contour in ([(g, bas), (d, bas), (d, z0), (g, z0)], [(g, z1), (d, z1), (d, haut), (g, haut)],
                    [(g, bas), (g + L, bas), (g + L, haut), (g, haut)],
                    [(d - L, bas), (d, bas), (d, haut), (d - L, haut)]):
        parties.append((contour, 0.50, POURPRE))
    for (u0, z_0, u1, z_1) in ((g, bas, d, bas + F), (g, haut - F, d, haut), (g, bas, g + F, haut),
                               (d - F, bas, d, haut), (g + L - F, z0 - F, d - L + F, z0),
                               (g + L - F, z1, d - L + F, z1 + F), (g + L - F, z0 - F, g + L, z1 + F),
                               (d - L, z0 - F, d - L + F, z1 + F)):
        parties.append(([(u0, z_0), (u1, z_0), (u1, z_1), (u0, z_1)], 0.60, CLAIR))
    # Les rosaces se suivent à une ama, une aux quatre coins ; les rangs verticaux
    # partent du coin sans le redoubler.
    axe_bas, axe_haut, axe_g, axe_d = bas + L / 2, haut - L / 2, g + L / 2, d - L / 2
    for u in np.linspace(axe_g, axe_d, round(axe_d - axe_g) + 1):
        parties += rosace(u, axe_bas) + rosace(u, axe_haut)
    for z in np.linspace(axe_bas, axe_haut, round(axe_haut - axe_bas) + 1)[1:-1]:
        parties += rosace(axe_g, z) + rosace(axe_d, z)
    return parties


def frise():
    """Les places des figures : (motif, u de l'axe, z du pied, hauteur, sens) — créatures
    et lions en alternance stricte, les lions d'un rang marchant vers ceux du rang
    voisin, comme deux cortèges qui se croisent."""
    z0, z1 = CHAMP
    g = -LARGEUR / 2
    # Les colonnes se partagent le champ ENTRE les lisières : réparties sur toute la
    # largeur, celles des bords mordaient sur la bordure.
    rang, pas = (z1 - z0) / RANGS, (LARGEUR - 2 * LISIERE) / COLONNES
    places = []
    for r in range(RANGS):
        for i in range(COLONNES):
            nom = "creature" if (i + r) % 2 == 0 else "lion"
            h = min(rang * PART_FIGURE, pas * PART_COLONNE / MOTIFS[nom][2])
            places.append((nom, g + LISIERE + pas * (i + 0.5), z0 + rang * r + (rang - h) / 2, h,
                           1 if r % 2 == 0 else -1))
    return places


# --- Les guides, le tissage, la carte. ---

def rasteriser(parties, cadre, largeur_px, echelle):
    """(relief, faces) des parties posées dans `cadre` à `largeur_px` de large."""
    u0, z0, u1, z1 = cadre
    hauteur_px = int(round((z1 - z0) * echelle))
    relief = np.zeros((hauteur_px, largeur_px), dtype=np.float32)
    faces = np.zeros((hauteur_px, largeur_px, 2), dtype=np.float32)
    for contour, hauteur, face in parties:
        lignes, colonnes, dedans = remplir([(u - u0, z - z0) for u, z in contour], echelle, hauteur_px, largeur_px)
        relief[lignes, colonnes][dedans] = hauteur
        faces[lignes, colonnes][dedans] = face
    return relief, faces


def ombrer(relief, faces, masque):
    """Le guide tel qu'on le montre au modèle : les faces en couleur, le relief éclairé de
    haut à gauche, sur le vert du fond — un rendu, que le modèle lit mieux qu'une carte."""
    dz, du = np.gradient(relief * 0.03 * relief.shape[1])
    ombre = np.clip(1.0 + 0.5 * (dz * 0.6 - du * 0.6) / (1.0 + np.abs(dz) + np.abs(du)), 0.5, 1.5)
    rgb = np.clip(couleur_face(faces[..., 0], faces[..., 1]) * ombre[..., None], 0, 1) ** (1 / 2.2)
    return np.where(masque[..., None], rgb, np.array([0.0, 1.0, 0.0]))


def sauver_png(chemin, rgb):
    image = bpy.data.images.new(chemin.stem, rgb.shape[1], rgb.shape[0], alpha=False)
    image.pixels.foreach_set(np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,))], -1)
                             .astype(np.float32).ravel())
    chemin.parent.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(chemin)
    image.file_format = "PNG"
    image.save()


def guider(nom):
    dessiner, cadre, _, _, _ = MOTIFS[nom]
    relief, faces = rasteriser(dessiner(), cadre, TUILE_PX, TUILE_PX / (cadre[2] - cadre[0]))
    sauver_png(GUIDES / f"{nom}.png", ombrer(relief, faces, relief > 0))
    print(f"  {nom:8s} guide : tissages/guides/{nom}.png")


def tisser_figure(nom):
    """Fait tisser le guide de `nom` par gpt-image-2 et pose la figure dans `tissages/`."""
    sys.path.insert(0, str(RACINE / ".claude" / "skills" / "fal-video"))
    import fal_commun  # noqa: E402
    _, _, _, sujet, iconographie = MOTIFS[nom]
    cle = fal_commun.cle_api()
    corps = {"prompt": TISSAGE.format(sujet=sujet, iconographie=iconographie),
             "image_urls": [fal_commun.televerse(str(GUIDES / f"{nom}.png"), cle)],
             "image_size": "square_hd", "quality": "high", "output_format": "png"}
    reponse = fal_commun.genere("openai/gpt-image-2/edit", corps, cle)
    fal_commun.telecharge(reponse["images"][0]["url"], str(TISSAGES / f"{nom}.png"))
    print(f"  {nom:8s} tissé : tissages/{nom}.png")


def faces_de(rgb, masque, pas=32):
    """La face du tissage la plus proche de chaque couleur : le point du carré (clarté,
    rougeur), au 1/`pas`, dont la laine dosée est la moins loin, en linéaire."""
    grille = (np.arange(pas + 1) / pas)
    clarte, rougeur = np.meshgrid(grille, grille, indexing="ij")
    candidats = couleur_face(clarte, rougeur).reshape(-1, 3)
    couleurs = rgb[masque]
    choix = np.empty(len(couleurs), dtype=np.int64)
    for debut in range(0, len(couleurs), 65536):
        tranche = couleurs[debut:debut + 65536]
        ecarts = ((tranche[:, None, :] - candidats[None, :, :]) ** 2).sum(axis=2)
        choix[debut:debut + 65536] = ecarts.argmin(axis=1)
    faces = np.zeros(masque.shape + (2,), dtype=np.float32)
    faces[masque] = np.stack([clarte.ravel()[choix], rougeur.ravel()[choix]], axis=1)
    return faces


def figure_tissee(nom):
    """(relief, faces, masque) d'une figure tissée, posée dans le cadre de son motif."""
    _, cadre, _, _, _ = MOTIFS[nom]
    rgb = lire_rgb(TISSAGES / f"{nom}.png")
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dedans = figure(~((g > r + VERT) & (g > b + VERT)))
    # Le bord de la figure emprunte au vert : deux pixels de moins, et rien n'y touche.
    dedans = distance(dedans, 2) >= 2
    echelle = TUILE_PX / (cadre[2] - cadre[0])
    canaux = [cadrer(rgb[..., k], dedans, cadre, TUILE_PX)[0] for k in range(3)]
    _, masque = cadrer(rgb[..., 0], dedans, cadre, TUILE_PX)
    lineaire = np.clip(np.stack(canaux, axis=-1), 0, 1) ** 2.2
    rayon = max(1, int(round(RONDEUR * echelle)))
    volume = bombe(distance(masque, rayon) / rayon)
    modele = flouter(lineaire.mean(axis=2), max(1, int(round(GRAIN * echelle))))
    bas, haut = modele[masque].min(), modele[masque].max()
    modele = np.clip((modele - bas) / (haut - bas), 0.0, 1.0)
    relief = np.where(masque, (1.0 - PART_MODELE) * volume + PART_MODELE * modele, 0.0)
    return relief.astype(np.float32), faces_de(lineaire, masque), masque


def tisser():
    """(hauteur, faces, masque) : trois cartes de LARGEUR_PX sur le double, ligne 0 en bas ;
    les faces portent (clarté, rougeur) sur leur dernier axe. La lisière se rasterise,
    les figures tissées se posent à leur place, chacune lue bilinéaire dans son cadre."""
    largeur, hauteur = LARGEUR_PX * SURECHANTILLON, LARGEUR_PX * SURECHANTILLON * 2
    echelle = largeur / LARGEUR
    relief, faces = rasteriser(lisiere(), (-LARGEUR / 2, 0.0, LARGEUR / 2, HAUTEUR), largeur, echelle)
    figures = {nom: figure_tissee(nom) for nom in MOTIFS}
    for nom, u, z0, h, sens in frise():
        _, (cu0, cz0, cu1, cz1), _, _, _ = MOTIFS[nom]
        relief_fig, faces_fig, masque_fig = figures[nom]
        echelle_fig = TUILE_PX / (cu1 - cu0)
        # Le bloc de la carte que le cadre couvre, et pour chacun de ses pixels le
        # point de la figure qu'il lit : u de figure = (u de carte - axe) / h, retourné
        # par `sens`.
        l0, l1 = int(np.ceil((z0 + cz0 * h) * echelle)), int(np.floor((z0 + cz1 * h) * echelle))
        c0, c1 = int(np.ceil((u + LARGEUR / 2 + min(sens * cu0, sens * cu1) * h) * echelle)), \
            int(np.floor((u + LARGEUR / 2 + max(sens * cu0, sens * cu1) * h) * echelle))
        z_fig = ((np.arange(l0, l1) + 0.5) / echelle - z0) / h
        u_fig = sens * ((np.arange(c0, c1) + 0.5) / echelle - LARGEUR / 2 - u) / h
        lignes = np.clip((z_fig - cz0) * echelle_fig - 0.5, 0, relief_fig.shape[0] - 1.001)
        colonnes = np.clip((u_fig - cu0) * echelle_fig - 0.5, 0, relief_fig.shape[1] - 1.001)
        dedans = reechantillonner(masque_fig, lignes, colonnes) > 0.5
        bloc_relief, bloc_faces = relief[l0:l1, c0:c1], faces[l0:l1, c0:c1]
        bloc_relief[dedans] = reechantillonner(relief_fig, lignes, colonnes)[dedans]
        bloc_faces[dedans] = reechantillonner(faces_fig, lignes, colonnes)[dedans]
    masque = (relief > 0).astype(np.float32)
    s = SURECHANTILLON
    relief = relief.reshape(hauteur // s, s, largeur // s, s).mean(axis=(1, 3))
    faces = faces.reshape(hauteur // s, s, largeur // s, s, 2).mean(axis=(1, 3))
    masque = masque.reshape(hauteur // s, s, largeur // s, s).mean(axis=(1, 3))
    rayon = max(1, round(FONDU * LARGEUR_PX / LARGEUR))
    faces = np.stack([flouter(faces[..., k], rayon) for k in range(2)], axis=-1)
    return flouter(relief, rayon), faces, masque


def ecrire_palette():
    fiche = {"laines": [[nom, list(rgb)] for nom, rgb in LAINES], "dosages": DOSAGES, "jour": JOUR,
             "palette": {face: [round(c, 4) for c in rgb] for face, rgb in PALETTE.items()}}
    (SORTIE / "parokhet.json").write_text(json.dumps(fiche, separators=(",", ":")), encoding="utf-8")
    for face, rgb in fiche["palette"].items():
        print(f"  {face:12s} {rgb}")


ARGUMENTS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if ARGUMENTS[:1] == ["--guides"]:
    for nom in ARGUMENTS[1:] or MOTIFS:
        guider(nom)
elif ARGUMENTS[:1] == ["--tisser"]:
    for nom in ARGUMENTS[1:] or MOTIFS:
        tisser_figure(nom)
elif __name__ == "__main__":
    relief, faces, masque = tisser()
    ecrire(NOM, relief, masque, faces)
    ecrire_palette()
