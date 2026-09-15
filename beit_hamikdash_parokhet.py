"""Tisse le motif des deux Parokhot : une carte de relief que la matière lit, pas des volumes.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_parokhet.py

« מַעֲשֵׂה חֹשֵׁב יַעֲשֶׂה אֹתָהּ כְּרֻבִים » (Ex. 26:31) : créatures ailées et lions en alternance,
tissés dans les mêmes quatre laines — jamais d'or (le verset n'en liste que quatre),
jamais brodés, et sans un visage (§9 de la fiche). Une figure TISSÉE n'est pas un
volume : elle bombe l'étoffe de quelques centimètres et s'en distingue au ton, par
l'autre face du maassé 'hoshev (Rashi, ibid.). Des découpes posées sur le rideau se
lisaient en carton ; ce qui se lit ici, c'est le rideau lui-même, qui porte le motif.

Écrit `visite/matieres/parokhet_2048.webp`, une carte de 20 amot sur 40 — le rideau
entier, lu par la position de monde (y, z) : RGB porte la HAUTEUR du bombé en gris,
alpha porte le MASQUE de la figure. Le WebP est sans perte (`beit_hamikdash_carte.py`).

Le blockout la lit dans `parokhet()` (bump + ton), `visite/matieres.js` dans la
famille étoffe (pente + ton). La rasterisation est celle de `beit_hamikdash_carte.py` ;
demande `cwebp` sur le PATH. À relancer après toute
modification de ce script ou de `beit_hamikdash_contours.py`, puis reconstruire.
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from beit_hamikdash_carte import ecrire, flouter, remplir  # noqa: E402
from beit_hamikdash_contours import (CORPS_DRESSE, aile, corolle, ellipse, lisser,  # noqa: E402
                                     poser, poser_lame)

LARGEUR_PX = 2048
NOM = f"parokhet_{LARGEUR_PX}"

# « אָרְכָּהּ אַרְבָּעִים אַמָּה וְרָחְבָּהּ עֶשְׂרִים אַמָּה » (Shekalim 8:5) : la carte est le rideau.
LARGEUR, HAUTEUR = 20.0, 40.0
CHAMP = (2.0, 38.0)       # bas et haut du champ figuré, en amot depuis le bas du rideau
RANGS, COLONNES = 6, 4
PART_FIGURE = 0.65        # hauteur d'une figure, en part du rang
LISIERE = 0.9             # largeur de la lisière qui borde le champ
# Le bombé se fond sur 4 cm : c'est un fil qui passe par-dessus, pas une arête.
FONDU = 0.04
SURECHANTILLON = 2


# --- Les deux motifs. Chaque partie : (contour en amot, hauteur relative du bombé). ---

def creature_ailee(u, z0, h):
    """Créature ailée de face : corps dressé, tête sans traits, deux ailes levées.
    « כְּרֻבִים » de Ex. 26:31 vaut « צִיּוּרִין שֶׁל בְּרִיּוֹת » (Rashi)."""
    parties = [(lisser(poser(CORPS_DRESSE, u, z0, h)), 0.75),
               (ellipse(u, z0 + 0.905 * h, 0.065 * h, 0.085 * h), 1.0)]
    for sens in (-1, 1):
        u_aile, z_aile = u + sens * 0.12 * h, z0 + 0.76 * h
        parties.append((poser_lame(aile(), u_aile, z_aile, 56, 0.44 * h, sens), 0.85))
        parties.append((poser_lame(aile(5), u_aile, z_aile, 50, 0.22 * h, sens), 1.0))
    return parties


# Le lion marchant des frises d'Orient : corps long, dos presque droit, poitrail
# profond, ventre relevé, queue ramenée en boucle au-dessus de la croupe.
LION_CORPS = ((0.36, 0.30), (0.40, 0.42), (0.40, 0.52), (0.30, 0.62), (0.16, 0.66),
              (0.00, 0.64), (-0.18, 0.62), (-0.34, 0.60), (-0.46, 0.56), (-0.53, 0.46),
              (-0.50, 0.34), (-0.36, 0.30), (-0.20, 0.27), (0.00, 0.26), (0.18, 0.28),
              (0.30, 0.30))
LION_TETE = ((0.36, 0.48), (0.50, 0.48), (0.60, 0.54), (0.63, 0.62), (0.58, 0.69),
             (0.49, 0.73), (0.45, 0.81), (0.39, 0.78), (0.34, 0.70), (0.31, 0.58))
LION_QUEUE = ((-0.38, 0.52), (-0.45, 0.58), (-0.52, 0.66), (-0.56, 0.78), (-0.53, 0.90),
              (-0.46, 0.94), (-0.39, 0.90), (-0.40, 0.86), (-0.46, 0.88), (-0.50, 0.82),
              (-0.49, 0.72), (-0.44, 0.60), (-0.40, 0.56))
# Une patte : cuisse, genou, canon, et la patte qui s'élargit au sol, (u de l'axe, z).
LION_PATTE = ((-0.055, 0.36), (0.055, 0.36), (0.040, 0.20), (0.030, 0.08), (0.075, 0.0),
              (-0.065, 0.0), (-0.035, 0.08), (-0.055, 0.20))
# (axe, foulée, hauteur relative) : les deux pattes du côté du regard sont en pleine
# marche, les deux autres passent derrière, un peu plus bas dans l'étoffe.
LION_PATTES = ((0.34, 0.08, 0.75), (-0.42, -0.08, 0.75), (0.22, -0.05, 0.60), (-0.30, 0.05, 0.60))


def lion(u, z0, h):
    """Le lion de la frise — « וּפְנֵי כְפִיר » (Ye'hezkel 41:19), et le lion du revers d'un
    maassé 'hoshev (Rashi sur Yoma 72b). De profil, marchant vers les u croissants."""
    parties = [(lisser(poser(LION_CORPS, u, z0, h), passes=2), 0.75),
               (corolle(u + 0.27 * h, z0 + 0.62 * h, 0.20 * h, 14), 0.90),
               (corolle(u + 0.33 * h, z0 + 0.47 * h, 0.13 * h, 10), 0.90),
               (lisser(poser(LION_TETE, u, z0, h), passes=2), 1.0),
               (lisser(poser(LION_QUEUE, u, z0, h), passes=2), 0.70)]
    for axe, foulee, hauteur in LION_PATTES:
        patte = [(axe + du + foulee * (1.0 - dz / 0.36), dz) for du, dz in LION_PATTE]
        parties.append((lisser(poser(patte, u, z0, h), passes=2), hauteur))
    return parties


def frise():
    """Le champ entier : créatures et lions en alternance stricte, et la lisière autour."""
    z0, z1 = CHAMP
    L, g, d = LISIERE, -LARGEUR / 2, LARGEUR / 2
    # Les colonnes se partagent le champ ENTRE les lisières : réparties sur toute la
    # largeur, celles des bords mordaient sur la bordure.
    rang, pas = (z1 - z0) / RANGS, (LARGEUR - 2 * L) / COLONNES
    parties = []
    for r in range(RANGS):
        for i in range(COLONNES):
            motif = creature_ailee if (i + r) % 2 == 0 else lion
            h = rang * PART_FIGURE
            parties += motif(g + L + pas * (i + 0.5), z0 + rang * r + (rang - h) / 2, h)
    for contour in ([(g, z0 - L), (d, z0 - L), (d, z0), (g, z0)],
                    [(g, z1), (d, z1), (d, z1 + L), (g, z1 + L)],
                    [(g, z0 - L), (g + L, z0 - L), (g + L, z1 + L), (g, z1 + L)],
                    [(d - L, z0 - L), (d, z0 - L), (d, z1 + L), (d - L, z1 + L)]):
        parties.append((contour, 0.6))
    return parties


# --- Le tissage : rasteriser, fondre, écrire. ---

def tisser():
    """(hauteur, masque), deux cartes de LARGEUR_PX sur le double, ligne 0 en bas."""
    largeur, hauteur = LARGEUR_PX * SURECHANTILLON, LARGEUR_PX * SURECHANTILLON * 2
    echelle = largeur / LARGEUR
    relief = np.zeros((hauteur, largeur), dtype=np.float32)
    for contour, bombe in frise():
        decale = [(u + LARGEUR / 2, z) for u, z in contour]
        lignes, colonnes, dedans = remplir(decale, echelle, hauteur, largeur)
        boite = relief[lignes, colonnes]
        boite[dedans] = np.maximum(boite[dedans], bombe)
    masque = (relief > 0).astype(np.float32)
    s = SURECHANTILLON
    relief = relief.reshape(hauteur // s, s, largeur // s, s).mean(axis=(1, 3))
    masque = masque.reshape(hauteur // s, s, largeur // s, s).mean(axis=(1, 3))
    return flouter(relief, max(1, round(FONDU * LARGEUR_PX / LARGEUR))), masque


ecrire(NOM, *tisser())
