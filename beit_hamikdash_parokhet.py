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
Le lion du sceau de Shema, serviteur de Yarovam, en est le contemporain hébreu.

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
from beit_hamikdash_contours import (BRAS, CORPS_KERUV, DATTE, EPIS,  # noqa: E402
                                     LARGEURS_BRAS, LARGEURS_QUEUE, LION_COTES, LION_CORPS,
                                     LION_CRINIERE, LION_FLANC, LION_GUEULE, LION_HOUPPE,
                                     LION_MACHOIRE, LION_NASEAU, LION_OEIL, LION_OREILLE,
                                     LION_PATTES_CACHEES, LION_PATTES_VUES, LION_QUEUE, LION_RANGS,
                                     LION_SOURCIL, LION_TETE, LION_VOLUTE_EPAULE,
                                     LION_VOLUTE_HANCHE, PALMES, PLIS, TETE_DOUBLE, TRONC, aile,
                                     chevrons, corolle, courbe, criniere, ellipse, epi, folioles,
                                     lisser, palme, pied, poser, poser_lame, ruban, ruban_effile, volute)

LARGEUR_PX = 2048
NOM = f"parokhet_{LARGEUR_PX}"
TUILE_PX = 1024
TISSAGES = RACINE / "tissages"
GUIDES = TISSAGES / "guides"

# « אָרְכָּהּ אַרְבָּעִים אַמָּה וְרָחְבָּהּ עֶשְׂרִים אַמָּה » (Shekalim 8:5) : la carte est le rideau.
LARGEUR, HAUTEUR = 20.0, 40.0
LISIERE = 1.2             # largeur de la lisière qui borde le champ
LISTEL = 0.10             # les deux filets clairs qui bordent la lisière et les bandes
BANDE = 0.6               # hauteur d'une bande de guilloché entre deux registres
# Les registres, en amot depuis le bas du rideau : bas, centre, haut, et les deux bandes
# qui les séparent. Une tapisserie d'apparat n'est pas une grille : un centre qui
# domine, des registres qui l'encadrent, des bandes qui les tiennent.
REGISTRES = {"bas": (LISIERE, 9.0), "centre": (9.6, 30.4), "haut": (31.0, HAUTEUR - LISIERE)}
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
# Le fond est de tekhelet avant tout : « תְּכֵלֶת דּוֹמֶה לַיָּם וְיָם דּוֹמֶה לָרָקִיעַ וְרָקִיעַ
# דּוֹמֶה לְכִסֵּא הַכָּבוֹד » (Menachot 43b) — c'est la couleur du Trône que le rideau du Devir
# porte, l'argaman ne fait que l'assombrir.
DOSAGES = {"fond": (0.62, 0.30, 0.08, 0.00), "chaud": (0.10, 0.35, 0.50, 0.05),
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


def lion():
    """Le lion du sceau de Shema (beit_hamikdash_contours.py), tissé : corps de lin,
    crinière, toupet et fond de gueule cramoisis, dessin intérieur en fils du fond. Les
    parties se posent du plus lointain au plus proche — les pattes du côté caché, la
    queue, le corps, puis la tête et les pattes du côté vu."""
    parties = []
    for axe, largeurs in LION_PATTES_CACHEES:
        parties += [(ruban_effile(axe, largeurs), 0.58, CLAIR), (pied(axe), 0.58, CLAIR)]
    parties += [(ruban_effile(LION_QUEUE, LARGEURS_QUEUE), 0.68, CLAIR),
                (lisser(LION_CORPS, passes=2), 0.76, CLAIR),
                (criniere(*LION_HOUPPE, meches=9, creux=0.80), 0.82, CHAUD),
                (criniere(*LION_CRINIERE), 0.88, CHAUD),
                (lisser(LION_OREILLE, passes=2), 0.95, CLAIR),
                (lisser(LION_GUEULE, passes=1), 0.62, CHAUD),
                (lisser(LION_TETE, passes=1), 1.0, CLAIR),
                (lisser(LION_MACHOIRE, passes=1), 0.94, CLAIR)]
    for axe, largeurs in LION_PATTES_VUES:
        parties += [(ruban_effile(axe, largeurs), 0.80, CLAIR), (pied(axe), 0.80, CLAIR)]
    for fil in LION_RANGS + LION_COTES + (LION_FLANC, LION_SOURCIL, LION_NASEAU):
        parties.append((ruban(courbe(fil), TRAIT), BOMBE_TRAIT, FOND))
    for spirale, depart in ((LION_VOLUTE_EPAULE, 2.2), (LION_VOLUTE_HANCHE, -0.6)):
        parties.append((ruban(volute(*spirale, depart=depart), TRAIT), BOMBE_TRAIT, FOND))
    parties.append((ellipse(*LION_OEIL), BOMBE_TRAIT, FOND))
    return parties


def timora():
    """Le dattier — « וְתִמֹרֹת » (Melakhim I 6:29), et « תִמֹרָה בֵּין כְּרוּב לִכְרוּב » (Ye'hezkel
    41:18) : entre deux keruvim, une timora. Celle des parois (beit_hamikdash_contours.py),
    tissée : fût pourpre à chevrons du fond, palmes de lin découpées en folioles, régimes
    de dattes cramoisies pendus en épis."""
    parties = [(TRONC, 0.6, POURPRE)]
    for chevron in chevrons():
        parties.append((ruban(chevron, 0.008), BOMBE_TRAIT, FOND))
    for inclinaison, longueur, retombee in PALMES[::-1]:
        for sens in ((1,) if inclinaison == 0 else (-1, 1)):
            axe, largeurs = palme(sens * inclinaison, longueur, retombee)
            parties.append((folioles(axe, largeurs), 0.8, CLAIR))
            parties.append((ruban(axe[3:-9], 0.005), BOMBE_TRAIT, FOND))
    for sens in (-1, 1):
        for ecart, longueur in EPIS:
            fil, dattes = epi(ecart, longueur)
            parties.append((ruban([(sens * u, z) for u, z in fil], 0.011), 0.70, POURPRE))
            for u, z in dattes:
                parties.append((ellipse(sens * u, z, *DATTE), 0.74, CHAUD))
    return parties


# Ce que l'on demande au modèle pour chaque motif : l'iconographie mot à mot, parce que
# c'est elle que le guide ne porte qu'à moitié. La manière est celle des tapisseries de
# l'Orient ancien — laines plates, contours en fil, dessin intérieur en fils contrastés.
TISSAGE = "Re-weave this {sujet} as a genuine ancient Near-Eastern woven wool tapestry " \
          "figure of the Iron Age (in the spirit of Hebrew and Phoenician seals, Syrian " \
          "tapestry and Pazyryk textiles): flat woven wool with a visible fine weft, bold " \
          "simplified outlines in a darker thread, decorative interior patterning in " \
          "contrasting threads, stylised and geometric, no shading, no gold, no yellow, no " \
          "green, no black. Use ONLY these wool colours: deep blue-violet, purple, crimson, " \
          "and ivory linen. Keep exactly this composition, pose, proportions and framing: " \
          "{iconographie} Flat pure bright green (#00FF00) background all around the figure, " \
          "orthographic front view, no text, no border, no frame."
# (guide, cadre carré autour de la figure, sujet, iconographie). Le cadre suit la
# convention de `cadrer` : la figure y tient du pied en z = 0 au sommet en z = 1, centrée
# sur u = 0 — le guide montré au modèle cadre alors exactement comme le tissage sera relu.
MOTIFS = {
    "creature": (creature_ailee, (-0.6, -0.1, 0.6, 1.1), "winged child figure",
                 "a standing child seen from the front, child-like proportions with a large "
                 "head, a long plain crimson tunic with a patterned belt and simple vertical "
                 "folds down to the feet, arms along the body with ivory hands visible, two "
                 "large wings of ivory linen raised on either side with clearly separated rows "
                 "of feathers and purple covert feathers at the root, and ONE single ivory head "
                 "carrying TWO faces in profile, one looking left and one looking right "
                 "(Janus-like), with a plain headband, no hair, no beard. IMPORTANT: the faces "
                 "are perfectly smooth and blank, with no eyes, no nose, no mouth."),
    "timora": (timora, (-0.6, -0.1, 0.6, 1.1), "date palm tree, as on the Bar Kokhba coins",
               "a straight purple trunk marked with stacked chevron scars of cut frond bases "
               "and a flared foot, and a crown of exactly seven fronds of ivory linen — the "
               "middle one upright, the others bending down in arcs. IMPORTANT: every frond "
               "is deeply CUT INTO SEPARATE POINTED LEAFLETS along both sides of a fine violet "
               "midrib, like a feather or a comb, never a smooth leaf and never a flower "
               "petal; the leaflets are narrow, straight and angled towards the tip. Hanging "
               "from the crown on either side of the trunk, three slender purple strands per "
               "side drooping down along the trunk, each strung with small oval crimson dates "
               "— hanging spikes, not a round bunch of grapes."),
    "lion": (lion, (-0.80, -0.30, 0.80, 1.30), "roaring royal lion of Judah",
             "a lion in strict profile facing right, in the manner of the Hebrew seal of "
             "Shema servant of Jeroboam from Megiddo: massive and regal, ROARING with the "
             "jaws WIDE OPEN showing bared fangs and a crimson mouth, the head held at the "
             "height of the back, a heavy brow ridge over a small almond eye, a short rounded "
             "ear set back. Body of ivory linen: deep chest, hollow flank drawn up in front "
             "of a heavy haunch, long dipped back. A full crimson mane of POINTED LOCKS in "
             "tiered rows encircling the head and falling over the chest — rows of pointed "
             "tufts, never rounded petals and never a flower. Four legs each at its own "
             "angle, the foreleg advanced and the hind leg thrusting with a bent hock, broad "
             "paws flat on the ground. Long tail raised in an S above the back, ending in a "
             "crimson tuft that touches the tail. Interior drawing in the violet ground "
             "thread: a spiral volute on the shoulder and another on the haunch, three curved "
             "rib lines, the fold of the groin, the rows of the mane."),
}


# --- La lisière, les bandes, le fleuron : ce qui reste dessiné ici. ---

def rosace(u, z):
    """Une rosace de la lisière : le ציץ des parois (I Rois 6:29) repris en bordure — un
    CHOIX ; corolle de lin, cœur cramoisi."""
    return [(corolle(u, z, 0.32, 8), 0.80, CLAIR), (ellipse(u, z, 0.10, 0.10), 0.65, CHAUD)]


def cadre_plein(u0, z0, u1, z1, hauteur, face):
    return ([(u0, z0), (u1, z0), (u1, z1), (u0, z1)], hauteur, face)


def lisiere():
    """La bordure : un champ pourpre entre deux filets de lin, semé de rosaces."""
    L, F, g, d = LISIERE, LISTEL, -LARGEUR / 2, LARGEUR / 2
    parties = [cadre_plein(g, 0.0, d, HAUTEUR, 0.50, POURPRE),
               cadre_plein(g + L, L, d - L, HAUTEUR - L, 0.0, FOND)]
    for (u0, z0, u1, z1) in ((g, 0.0, d, F), (g, HAUTEUR - F, d, HAUTEUR), (g, 0.0, g + F, HAUTEUR),
                             (d - F, 0.0, d, HAUTEUR), (g + L - F, L - F, d - L + F, L),
                             (g + L - F, HAUTEUR - L, d - L + F, HAUTEUR - L + F),
                             (g + L - F, L - F, g + L, HAUTEUR - L + F),
                             (d - L, L - F, d - L + F, HAUTEUR - L + F)):
        parties.append(cadre_plein(u0, z0, u1, z1, 0.60, CLAIR))
    # Les rosaces se suivent à un peu plus d'une ama, une aux quatre coins ; les rangs
    # verticaux partent du coin sans le redoubler.
    axe_bas, axe_haut, axe_g, axe_d = L / 2, HAUTEUR - L / 2, g + L / 2, d - L / 2
    for u in np.linspace(axe_g, axe_d, round((axe_d - axe_g) / 1.1) + 1):
        parties += rosace(u, axe_bas) + rosace(u, axe_haut)
    for z in np.linspace(axe_bas, axe_haut, round((axe_haut - axe_bas) / 1.1) + 1)[1:-1]:
        parties += rosace(axe_g, z) + rosace(axe_d, z)
    return parties


def guilloche(z0, z1):
    """Une bande entre deux registres : deux fils de lin qui se croisent en tresse sur le
    pourpre, un point cramoisi dans chaque maille — la torsade des cordons eux-mêmes."""
    g, d, F = -LARGEUR / 2 + LISIERE, LARGEUR / 2 - LISIERE, LISTEL
    zc, amplitude, periode = (z0 + z1) / 2, (z1 - z0) * 0.28, 1.1
    parties = [cadre_plein(g, z0, d, z1, 0.50, POURPRE),
               cadre_plein(g, z0, d, z0 + F * 0.6, 0.60, CLAIR), cadre_plein(g, z1 - F * 0.6, d, z1, 0.60, CLAIR)]
    us = np.linspace(g, d, int((d - g) / periode * 16) + 1)
    for phase in (0.0, np.pi):
        fil = [(u, zc + amplitude * np.sin(2 * np.pi * (u - g) / periode + phase)) for u in us]
        parties.append((ruban(fil, 0.09), 0.75, CLAIR))
    for k in range(int((d - g) / periode)):
        parties.append((ellipse(g + periode * (k + 0.25), zc, 0.09, 0.09), 0.65, CHAUD))
        parties.append((ellipse(g + periode * (k + 0.75), zc, 0.09, 0.09), 0.65, CHAUD))
    return parties


def fleuron(u, z, r):
    """« פְּטוּרֵי צִצִּים » (Melakhim I 6:29) : la rosette à six pétales des ossuaires de
    Jérusalem, comme aux parois — en lin, à cœur cramoisi, les pétales séparés du fond."""
    parties = [(corolle(u, z, r, 6), 0.85, CLAIR)]
    for k in range(6):
        a = np.pi * (2 * k + 1) / 6
        parties.append((ruban([(u + 0.2 * r * np.cos(a), z + 0.2 * r * np.sin(a)),
                               (u + 0.8 * r * np.cos(a), z + 0.8 * r * np.sin(a))], 0.05 * r), BOMBE_TRAIT, FOND))
    parties.append((ellipse(u, z, 0.26 * r, 0.26 * r), 0.7, CHAUD))
    return parties


def ornements():
    """Tout ce qui se dessine : la lisière, les deux bandes, le fleuron du centre."""
    (b0, b1), (c0, c1), (h0, h1) = REGISTRES["bas"], REGISTRES["centre"], REGISTRES["haut"]
    return lisiere() + guilloche(b1, c0) + guilloche(c1, h0) + fleuron(0.0, 25.3, 1.3)


def composition():
    """Les places des figures : (motif, u de l'axe, z du pied, hauteur, sens).

    « וְעָשׂוּי כְּרוּבִים וְתִמֹרִים וְתִמֹרָה בֵּין־כְּרוּב לִכְרוּב » (Ye'hezkel 41:18) : la timora
    entre deux keruvim, c'est la composition même des parois du Bayit, et le lion est
    la seconde face du keruv (41:19), tournée vers la timora. Au centre, deux grands
    keruvim dont les ailes se croisent au-dessus d'une timora — comme celles de la
    kaporet, « סֹכְכִים בְּכַנְפֵיהֶם » (Ex. 25:20) —, et au-dessus d'eux deux lions en
    cortège vers un fleuron. En bas, deux lions vers une timora ; en haut, keruv, timora,
    keruv. Les lions, les keruvim et les timorot sont aussi ceux des panneaux du Temple
    de Shlomo (Melakhim I 7:29, 36)."""
    (b0, b1), (c0, c1), (h0, h1) = REGISTRES["bas"], REGISTRES["centre"], REGISTRES["haut"]
    # La timora du centre est aussi grande que les corps des keruvim le permettent : ses
    # palmes s'ouvrent sur 0,35 de sa hauteur de chaque côté, le lion sur 0,68 — mesuré
    # sur les tissages. Les registres haut et bas restent nettement plus petits que le
    # centre, sinon la hiérarchie s'écrase.
    return [("timora", 0.0, b0 + 1.4, 5.0, 1), ("lion", -5.6, b0 + 1.8, 3.9, 1), ("lion", 5.6, b0 + 1.8, 3.9, -1),
            ("timora", 0.0, c0 + 1.4, 6.0, 1),
            ("creature", -4.5, c0 + 1.4, 8.2, 1), ("creature", 4.5, c0 + 1.4, 8.2, 1),
            ("lion", -3.3, 23.5, 3.6, 1), ("lion", 3.3, 23.5, 3.6, -1),
            ("timora", 0.0, h0 + 1.7, 4.0, 1),
            ("creature", -5.6, h0 + 1.5, 4.6, 1), ("creature", 5.6, h0 + 1.5, 4.6, 1)]


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
    dessiner, cadre, _, _ = MOTIFS[nom]
    relief, faces = rasteriser(dessiner(), cadre, TUILE_PX, TUILE_PX / (cadre[2] - cadre[0]))
    sauver_png(GUIDES / f"{nom}.png", ombrer(relief, faces, relief > 0))
    print(f"  {nom:8s} guide : tissages/guides/{nom}.png")


def tisser_figure(nom):
    """Fait tisser le guide de `nom` par gpt-image-2 et pose la figure dans `tissages/`."""
    sys.path.insert(0, str(RACINE / ".claude" / "skills" / "fal-video"))
    import fal_commun  # noqa: E402
    _, _, sujet, iconographie = MOTIFS[nom]
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
    _, cadre, _, _ = MOTIFS[nom]
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
    les faces portent (clarté, rougeur) sur leur dernier axe. Les ornements se rasterisent,
    les figures tissées se posent à leur place, chacune lue bilinéaire dans son cadre."""
    largeur, hauteur = LARGEUR_PX * SURECHANTILLON, LARGEUR_PX * SURECHANTILLON * 2
    echelle = largeur / LARGEUR
    relief, faces = rasteriser(ornements(), (-LARGEUR / 2, 0.0, LARGEUR / 2, HAUTEUR), largeur, echelle)
    figures = {nom: figure_tissee(nom) for nom in MOTIFS}
    for nom, u, z0, h, sens in composition():
        _, (cu0, cz0, cu1, cz1), _, _ = MOTIFS[nom]
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
