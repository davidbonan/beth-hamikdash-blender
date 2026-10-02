import math

from ..primitives.parametres import Z_BAT
from ..primitives.matieres import MAT_OR, MAT_OR_PLAQUE
from ..primitives.volumes import box, cyl_between
from ..primitives.gravures import (BANDEAU_KIR, PAS_KIR, RAYON_ROSETTE, SAILLIE_KIR, _bande_saillante,
                                   bandeau_guirlande, emboitement, figure_du_registre, keruv, largeur_gravure,
                                   palmette)
from ..primitives.ouvrages import EPAISSEUR_PLACAGE
from .heikhal import FENETRE_INT, HK0, HK1, KK0, KK1, TR0, baies_heikhal, lambris_or


# --- Kodesh HaKodashim : même placage. « כל הבית » ne s'arrête pas au Heikhal, et
#     Melakhim I 6:20-22 dore explicitement le devir au Premier Temple. La pièce n'a
#     aucune ouverture et reste noire : l'or n'y rend que sous la braise de la ma'hta —
#     ce qui est exactement la seule lumière du plan 11.
box("KhK_or_mur_N", KK1, KK0, 10 - EPAISSEUR_PLACAGE, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_mur_S", KK1, KK0, -10, -10 + EPAISSEUR_PLACAGE, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_mur_O", KK1, KK1 + EPAISSEUR_PLACAGE, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_plafond", KK1, KK0, -10, 10, Z_BAT + 40 - EPAISSEUR_PLACAGE, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
lambris_or("KhK", KK1, KK0, "60_KodeshHakodashim", [("O", KK1 + EPAISSEUR_PLACAGE, KK1 + 0.5)])
# « וְאֶת קַרְקַע הַבַּיִת צִפָּה זָהָב לִפְנִימָה וְלַחִיצוֹן » (Melakhim I 6:30) : le sol aussi, dans le
# Heikhal et dans le Devir. Deux centièmes d'ama : les kelim s'y posent sans flotter.
box("Heikhal_or_sol", HK1, HK0, -10, 10, Z_BAT, Z_BAT + 0.02, "50_Heikhal", MAT_OR_PLAQUE())
box("KhK_or_sol", KK1, KK0, -10, 10, Z_BAT, Z_BAT + 0.02, "60_KodeshHakodashim", MAT_OR_PLAQUE())


# --- Le champ sculpté d'une paroi du Bayit. Son ÉTENDUE est Ye'hezkel 41:20 —
#     « מֵהָאָרֶץ עַד־מֵעַל הַפֶּתַח », du sol jusqu'au-dessus de l'entrée, qui fait 20 amot
#     (Middot 4:1). Au-dessus, l'or reste nu jusqu'à la corniche : deux registres
#     flottant à mi-hauteur ne sont dans aucune source.
CHAMP_KIR = (1.0, 22.0)   # bas et haut du champ sculpté, en amot au-dessus de Z_BAT
CHAMP_HAUT = (22.0, 38.0)  # du haut du champ au bas de la corniche : ce qui restait nu
# Deux registres de keruvim monumentaux, qui vont chacun d'un bandeau à l'autre. Keruv et
# palmette ont la MÊME hauteur, et c'est cette hauteur commune qui tient le champ. Aucune
# source ne donne le nombre de registres.
REGISTRES_KIR = 2         # registres de figures, séparés par des guirlandes


# « מֵסַב קָלַע » : « מֻקֶּפֶת צִיּוּרִין » (Rashi 6:29) — le champ est CEINTURÉ, il ne
# s'arrête pas où la file de figures s'épuise. L'or nu que la file laissait à chaque
# angle devient donc le montant tressé qui la ferme.
MONTANT_KIR = 1.4         # largeur maximale d'un montant, en amot
RESERVE_MONTANT = 0.45    # l'or laissé nu entre le montant et la première figure


def _montants(nom, paroi, u0, u1, z0, z1, marge, col):
    """Les deux montants tressés aux bouts d'un champ, s'il reste de quoi les poser."""
    largeur = min(MONTANT_KIR, marge - RESERVE_MONTANT)
    if largeur <= BANDEAU_KIR / 2:
        return u0, u1
    vers = math.copysign(largeur, u1 - u0)
    for k, bord in enumerate((u0, u1)):
        _bande_saillante(f"{nom}_montant_{k}", paroi, "tresse",
                         ((bord, z0), (bord + (vers if k == 0 else -vers), z1)), SAILLIE_KIR * 0.7, col)
    return u0 + vers, u1 - vers


def champ_sculpte(nom, paroi, u0, u1, col):
    """Le champ « מֵהָאָרֶץ עַד־מֵעַל הַפֶּתַח » d'une paroi : des registres de keruvim et de
    palmettes en alternance stricte, séparés par des guirlandes, et ceinturé de deux
    montants tressés. Une file commence et finit par un keruv, « וְתִמֹרָה בֵּין כְּרוּב
    לִכְרוּב » (Ye'hezkel 41:18), et se centre sur la paroi.

    Les deux figures ont la MÊME hauteur, posent sur le bandeau d'en bas et touchent celui
    d'en haut : c'est ce qui tient le champ."""
    z0, z1 = Z_BAT + CHAMP_KIR[0], Z_BAT + CHAMP_KIR[1]
    registre = (z1 - z0 - BANDEAU_KIR) / REGISTRES_KIR
    _, h = figure_du_registre(z0, registre)
    assert h * emboitement("keruv", "palmette") < PAS_KIR, \
        f"keruv de {h:.2f} amot : il mord sur la palmette voisine au pas de {PAS_KIR:.2f}"
    # La file se centre sur la paroi, n impair pour qu'elle commence et finisse par un
    # keruv ; n + 1 pas doivent y tenir, et ce qui reste à chaque angle porte le montant.
    n = 2 * int((round(abs(u1 - u0) / PAS_KIR, 6) - 2) // 2) + 1
    pas = math.copysign(PAS_KIR, u1 - u0)
    premier = (u0 + u1) / 2 - pas * (n - 1) / 2
    marge = (abs(u1 - u0) - (n - 1) * PAS_KIR - h * largeur_gravure("keruv")) / 2
    ua, ub = _montants(f"Kir_{nom}", paroi, u0, u1, z0, z1, marge, col)
    rosettes = [premier + pas / 2 * k for k in range(-2, 2 * n + 1)]
    rosettes = [u for u in rosettes if min(ua, ub) + RAYON_ROSETTE < u < max(ua, ub) - RAYON_ROSETTE]
    for r in range(REGISTRES_KIR + 1):
        bandeau_guirlande(f"Kir_{nom}_{r}", paroi, ua, ub, z0 + r * registre, col, rosettes)
    for r in range(REGISTRES_KIR):
        pied, _ = figure_du_registre(z0 + r * registre, registre)
        for i in range(n):
            u = premier + pas * i
            if i % 2 == 0:
                keruv(f"Kir_{nom}_{r}{i:02d}", paroi, u, pied, h, col)
            else:
                palmette(f"Kir_{nom}_{r}{i:02d}", paroi, u, pied, h, col)


# --- Ce qui monte AU-DESSUS du champ. « מֵהָאָרֶץ עַד־מֵעַל הַפֶּתַח » (41:20) arrête les
#     FIGURES à 22 amot ; il n'arrête pas le placage. 41:16 le fait monter plus haut —
#     « מִקַּרְקָעִית הַחוֹמָה … וְעוֹלֶה לְמַעְלָה עַד הַחַלּוֹנוֹת » (Rashi), et Metzudat David
#     « וְגַם מִמַּעַל לְהַחַלּוֹנוֹת הָיוּ מְכֻסּוֹת בְּלוּחֵי אֶרֶז » —, et 41:17 dit de quoi il est
#     fait : « מִדּוֹת », des planches TOUTES D'UNE MÊME MESURE. Rashi : « מְחֻפֶּה נְסָרִים
#     גְּדוֹלוֹת, עֲשׂוּיוֹת בְּמִדָּה » ; Metzudat David : « עֲשׂוּיוֹת בְּמִדָּה אַחַת זֶה כָּזֶה …
#     שֶׁלֹּא הָיָה מָקוֹם פָּנוּי מִבְּלִי לוּחוֹת אֶרֶז ».
#     AUCUNE FIGURE ici : 41:20 ne les met que jusqu'à 22, et deux registres flottant à
#     mi-hauteur ne sont dans aucune source. Des panneaux et des cordons, rien d'autre.
#     Les seize amot laissées nues étaient la moitié de la paroi visible.
RANGS_HAUT = 4            # rangs de panneaux entre le champ et la corniche
CORDON_HAUT = 0.5         # hauteur d'un cordon en travers, en amot
TRONCON_MINI = 1.2        # longueur sous laquelle un tronçon de rang ne vaut plus d'être taillé
RESERVE_PANNEAU = 0.30    # l'or laissé nu autour d'une baie


def _hors_baies(ua, ub, z0, z1, baies):
    """Les tronçons de [ua, ub] qu'aucune baie ne traverse, dans la tranche [z0, z1].
    Une baie hors de la tranche ne la coupe pas — le Kodesh HaKodashim n'en a aucune."""
    gauche, droite = min(ua, ub), max(ua, ub)
    coupes = sorted((min(xa, xb) - RESERVE_PANNEAU, max(xa, xb) + RESERVE_PANNEAU)
                    for xa, xb, zb, zh in baies
                    if zb - RESERVE_PANNEAU < z1 and zh + RESERVE_PANNEAU > z0)
    libre = gauche
    for xa, xb in coupes:
        if xa > libre:
            yield libre, min(xa, droite)
        libre = max(libre, xb)
    if libre < droite:
        yield libre, droite


def champ_haut(nom, paroi, u0, u1, baies, col):
    """Le placage au-dessus du champ : des rangs de panneaux de la mesure, séparés par des
    cordons en travers, entre les mêmes montants tressés que le champ d'en bas.

    Aucune FIGURE — Ye'hezkel 41:20 ne les met que jusqu'à 22 — mais pas d'or nu non plus,
    « שֶׁלֹּא הָיָה מָקוֹם פָּנוּי מִבְּלִי לוּחוֹת אֶרֶז » (Metzudat David sur 41:17) ; et le lambris
    lui-même est « מִקְלַעַת פְּקָעִים וּפְטוּרֵי צִצִּים » (Melakhim I 6:18), d'où le bouton et la
    fleur taillés au fond de chaque panneau.

    Un rang est UNE bande répétée, non douze panneaux taillés un par un. C'est l'économie
    du cordon, et c'est elle qui permet quatre rangs de panneaux carrés là où deux rangs de
    planches de 2,7 sur 6,6 amot ne rendaient rien — une seule marche de 1,5 cm sur une
    planche d'un mètre trente ne se voit sous aucune lumière.
    """
    # `Kir_` et non `Haut_` : c'est le préfixe que concepts.json donne à sculptures_murs, et
    # les deux moitiés d'une paroi doivent tomber dans le MÊME concept — sculptures_murs est
    # dans EXCLUS, le haut versé ailleurs prenait une carte de lumière que le bas n'a pas.
    z0, z1 = Z_BAT + CHAMP_HAUT[0], Z_BAT + CHAMP_HAUT[1]
    marge = (abs(u1 - u0) - (2 * int((round(abs(u1 - u0) / PAS_KIR, 6) - 2) // 2)) * PAS_KIR) / 2
    ua, ub = _montants(f"Kir_{nom}_haut", paroi, u0, u1, z0, z1, marge, col)
    rang = (z1 - z0) / RANGS_HAUT - CORDON_HAUT
    for r in range(RANGS_HAUT):
        zb = z0 + r * (rang + CORDON_HAUT)
        for motif, (bas, haut), saillie in (("panneau", (zb, zb + rang), SAILLIE_KIR),
                                            ("corde", (zb + rang, zb + rang + CORDON_HAUT),
                                             SAILLIE_KIR * 0.7)):
            for k, (a, b) in enumerate(_hors_baies(ua, ub, bas, haut, baies)):
                if abs(b - a) < TRONCON_MINI:
                    continue
                _bande_saillante(f"Kir_{nom}_haut_{motif}_{r}{k}", paroi, motif,
                                 ((a, bas), (b, haut)), saillie, col)


PAROI_EST = ("y", HK0 - EPAISSEUR_PLACAGE, -1)
PAROIS_OR = [
    ("Heikhal_N", ("x", 10 - EPAISSEUR_PLACAGE, -1), HK1, HK0, baies_heikhal(*FENETRE_INT), "50_Heikhal"),
    ("Heikhal_S", ("x", -10 + EPAISSEUR_PLACAGE, 1), HK1, HK0, baies_heikhal(*FENETRE_INT), "50_Heikhal"),
    ("KhK_N", ("x", 10 - EPAISSEUR_PLACAGE, -1), KK1, KK0, (), "60_KodeshHakodashim"),
    ("KhK_S", ("x", -10 + EPAISSEUR_PLACAGE, 1), KK1, KK0, (), "60_KodeshHakodashim"),
    ("KhK_O", ("y", KK1 + EPAISSEUR_PLACAGE, 1), -10, 10, (), "60_KodeshHakodashim"),
]
for nom, paroi, u0, u1, baies, col in PAROIS_OR:
    champ_sculpte(nom, paroi, u0, u1, col)
    champ_haut(nom, paroi, u0, u1, baies, col)
# Le mur est du Heikhal n'a pas de champ : la baie en tient le milieu, les battants
# intérieurs les côtés (Middot 4:1). « עַד־מֵעַל הַפֶּתַח » n'y laisse que la guirlande qui
# ferme le champ des murs nord et sud, au-dessus de la baie et des battants. Au-dessus,
# en revanche, l'or y est continu sur les vingt amot de la nef et prend le même
# panneautage que les trois autres parois — « שֶׁלֹּא הָיָה מָקוֹם פָּנוּי » (Metzudat David
# sur Ye'hezkel 41:17) ne fait pas d'exception pour un mur.
bandeau_guirlande("Kir_Heikhal_E_linteau", PAROI_EST, -10, 10,
                  Z_BAT + CHAMP_KIR[1] - BANDEAU_KIR, "50_Heikhal")
champ_haut("Heikhal_E", PAROI_EST, -10, 10, (), "50_Heikhal")

# « וַיְעַבֵּר בְּרַתּוּקוֹת זָהָב לִפְנֵי הַדְּבִיר » (Melakhim I 6:21) : des chaînes d'or tendues
# devant le Devir. Trois chaînettes sous le plafond, de mur à mur, devant la parokhet.
for k, (creux, z_haut) in enumerate(((3.0, 38.6), (4.5, 37.6), (6.0, 36.6))):
    points = [(TR0 + 0.6, -9.8 + 19.6 * t, Z_BAT + z_haut - creux * (1 - (2 * t - 1) ** 2))
              for t in (i / 24 for i in range(25))]
    for i in range(24):
        cyl_between(f"Devir_chaine_{k}_{i:02d}", points[i], points[i + 1], 0.06, "50_Heikhal", MAT_OR(), verts=6)
