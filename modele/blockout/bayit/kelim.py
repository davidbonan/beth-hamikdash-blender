import math
from mathutils import Vector

from ..primitives.parametres import GEVIIM_RENVERSES, MENORA_DROITE, TEFAH, Z_BAT, m
from ..primitives.matieres import MAT_LECHEM, MAT_OR, MAT_OR_MIKSHE, MAT_PETILA, MAT_SHEMEN
from ..primitives.volumes import box, cyl, cyl_between, lampe, link_to, revolution_axe, sphere, tore


# --- Ustensiles du Heikhal (Yoma 33b ; Menachot 98b) : dans la moitié ouest,
#     à 2.5 amot des murs. Table au NORD, Menora au SUD, autel d'or entre les deux, vers l'est.
XU = -125
# Shoul'han 2 × 1 × 1.5, longueur E-O (Rambam Beit HaBe'hira 3:12), à 2,5 amot du mur nord (Yoma 33b)
YS0, YS1 = 6.5, 7.5
Z_TABLE = Z_BAT + 1.5
# Le'hem hapanim (Rambam Temidin 5:9 ; Mena'hot 11:4, 94b, 96a) : pain de 10 × 5 tefa'him, posé en
# travers de la Table qui en a 6 et relevé de 2 de chaque côté — 5 le long de la Table, fond d'un
# tefa'h, deux parois de 7 etzbaot ; deux piles de 6 séparées de 2 tefa'him, 3 kanim entre les pains
H_PAIN, PAS_PAIN = 7 / 4 * TEFAH, 2 * TEFAH
# « וְקַרְנוֹתָיו שֶׁבַע אֶצְבָּעוֹת » (Mena'hot 11:4) : pâte collée à chaque angle (Bartenura), au sommet
# des parois (Rashi 96a) ; un carré de 7 etzbaot rabattu vers l'intérieur du pain : CHOIX
CORNE_PAIN, EP_PAROI = 7 / 4 * TEFAH, 0.08


def shulchan(nom, x, avec_pain):
    """Shoul'han 2 × 1 × 1.5, longueur E-O (Rambam Beit HaBe'hira 3:12), à 2,5 amot du mur nord (Yoma 33b)."""
    box(nom, x - 1, x + 1, YS0, YS1, Z_BAT, Z_TABLE, "70_Kelim", MAT_OR())
    if not avec_pain:
        return
    for k in range(2):
        x0 = x - 1 + k * 7 * TEFAH
        x1 = x0 + 5 * TEFAH
        for p in range(6):
            z = Z_TABLE + p * PAS_PAIN
            box(f"Lechem_{k}{p}", x0, x1, YS0, YS1, z, z + TEFAH, "70_Kelim", MAT_LECHEM())
            for cote, ya, yb, yc0, yc1 in (("S", YS0, YS0 + EP_PAROI, YS0, YS0 + CORNE_PAIN),
                                           ("N", YS1 - EP_PAROI, YS1, YS1 - CORNE_PAIN, YS1)):
                box(f"Lechem_{k}{p}_paroi_{cote}", x0, x1, ya, yb, z, z + H_PAIN, "70_Kelim", MAT_LECHEM())
                for bout, xc0, xc1 in (("O", x0, x0 + CORNE_PAIN), ("E", x1 - CORNE_PAIN, x1)):
                    box(f"Lechem_{k}{p}_keren_{cote}{bout}", xc0, xc1, yc0, yc1, z + H_PAIN - EP_PAROI, z + H_PAIN,
                        "70_Kelim", MAT_LECHEM())
            if p < 5:   # kanim : 3 sous chaque pain sauf le premier, 2 sous le dernier (Rambam 3:15)
                for q, xq in enumerate((x0 + 1 * TEFAH, x0 + 2.5 * TEFAH, x0 + 4 * TEFAH)[: 2 if p == 4 else 3]):
                    cyl_between(f"Kaneh_{k}{p}{q}", (xq, YS0 - 0.15, z + H_PAIN), (xq, YS1 + 0.15, z + H_PAIN), 0.03, "70_Kelim")
        # snifim : montants d'or au sol de part et d'autre de la Table, dépassant les piles (Mena'hot 11:6 ; 94b)
        Z_SNIF = Z_TABLE + 6 * PAS_PAIN + 0.3
        for cote, y in (("S", YS0 - 0.1), ("N", YS1 + 0.1)):
            box(f"Snif_{k}{cote}", (x0 + x1) / 2 - 0.08, (x0 + x1) / 2 + 0.08, y - 0.04, y + 0.04, Z_BAT, Z_SNIF, "70_Kelim", MAT_OR())
        # bazikh d'encens posé sur la pile, selon les Sages (Mena'hot 11:5) ; CHOIX, le Rambam le met à côté (Beit HaBe'hira 3:14)
        cyl(f"Bazikh_{k}", (x0 + x1) / 2, (YS0 + YS1) / 2, Z_TABLE + 5 * PAS_PAIN + TEFAH, Z_TABLE + 5 * PAS_PAIN + TEFAH + 0.12, 0.15, "70_Kelim", MAT_OR())


shulchan("Shulchan", XU, avec_pain=True)
# Mizbea'h HaZahav 1 × 1 × 2, au centre, légèrement vers l'est, quatre cornes (Ex 30:2)
box("Mizbeach_Zahav", -119.5, -118.5, -0.5, 0.5, Z_BAT, Z_BAT + 2, "70_Kelim", MAT_OR())
for ns, cy in (("S", -0.5), ("N", 0.5 - 0.15)):
    for eo, cx in (("O", -119.5), ("E", -118.5 - 0.15)):
        box(f"Mizbeach_Zahav_keren_{ns}{eo}", cx, cx + 0.15, cy, cy + 0.15, Z_BAT + 2, Z_BAT + 2.15, "70_Kelim", MAT_OR())
# Menora : 18 tefa'him, 7 branches dans le plan N-S, trois marches devant
YM = -7.5
for i in range(3):
    box(f"Menora_marche_{i}", XU + 1.2 + i * 0.4, XU + 1.6 + i * 0.4, YM - 1.5, YM + 1.5,
        Z_BAT, Z_BAT + 0.3 * (3 - i), "70_Kelim")

# « וְאִם הָיְתָה חֲלוּלָה כְּשֵׁרָה » (Beit HaBe'hira 3:4) : creuse, d'où l'épaisseur, sous le poids d'un
# kikar avec ses lampes (Rashi sur Shemot 25:39). Paroi et diamètres : CHOIX.
TIGE_R, BRANCHE_R = 0.35 * TEFAH, 0.3 * TEFAH
# « שֶׁכָּל הַכַּפְתּוֹרִים שִׁיעוּר אֶחָד לְכֻלָּן, וְכֵן הַגְּבִיעִים כֻּלָּן שָׁוִין, וְהַפְּרָחִים גַּם כֵּן » (Rambam sur
# Mena'hot 3:7) : une seule taille par ornement, sur la tige comme sur les branches, la hauteur
# de celle qui tient à trois dans un tefa'h (Mena'hot 28b) ; la largeur est libre.
H_GAVIA, H_KAFTOR, H_PERACH = 0.35 * TEFAH, 0.4 * TEFAH, 0.25 * TEFAH
R_GAVIA, R_KAFTOR, R_PERACH = 0.66 * TEFAH, 0.68 * TEFAH, 0.76 * TEFAH
# Bouton de la tige d'où sort chaque paire de branches (Beit HaBe'hira 3:10), et l'écart de
# ses lampes en pas : la plus basse est la plus longue (Rashi sur Shemot 25:32).
PAIRES = ((8.5, 3), (10.5, 2), (12.5, 1))
PAS_NER = 3 * TEFAH             # CHOIX : sept lampes à pas égal, la Menora aussi large que haute
SOMMET = 18 - H_PERACH / TEFAH  # pied de la fleur qui porte chaque lampe, en tefa'him
# Sous chaque lampe, sur la tige comme sur les branches : trois coupes, un bouton, la fleur,
# chacun au milieu de sa part des trois derniers tefa'him — distances sous SOMMET.
SOUS_KAFTOR, SOUS_GEVIIM = 0.65 * TEFAH, (1.25 * TEFAH, 1.85 * TEFAH, 2.45 * TEFAH)
NER_R, NER_H, NER_BEC = 0.66 * TEFAH, 0.56 * TEFAH, 0.8
NIVEAU_SHEMEN, PETILA_R = 0.72, 0.03 * TEFAH
NER_PROFIL = [(0, 0), (0.5 * NER_R, 0), (0.82 * NER_R, 0.14 * NER_H), (0.98 * NER_R, 0.45 * NER_H),
              (NER_R, 0.8 * NER_H), (0.97 * NER_R, NER_H), (0.86 * NER_R, NER_H),
              (0.84 * NER_R, 0.8 * NER_H), (0.62 * NER_R, 0.5 * NER_H), (0, 0.44 * NER_H)]
# « הרגלים והפרח ג' » (Mena'hot 28b, cité par le Rambam sur Mena'hot 3:7) : le pied et sa fleur font trois tefa'him.
YEREKH_HAUT = 3 - H_PERACH / TEFAH
YEREKH_PROFIL = [(0, 1.1 * TEFAH), (1.3 * TEFAH, 1.1 * TEFAH), (1.45 * TEFAH, 1.22 * TEFAH),
                 (1.45 * TEFAH, 1.38 * TEFAH), (1.22 * TEFAH, 1.5 * TEFAH), (1.22 * TEFAH, 2.25 * TEFAH),
                 (1.4 * TEFAH, 2.37 * TEFAH), (1.4 * TEFAH, 2.5 * TEFAH), (0.8 * TEFAH, 2.64 * TEFAH),
                 (TIGE_R + 0.06 * TEFAH, YEREKH_HAUT * TEFAH), (0, YEREKH_HAUT * TEFAH)]


def cotes_amande(n, creux):
    """« מְשֻׁקָּדִים » : « מַעֲשֵׂה שְׁקֵדִים », l'or battu « עַד שֶׁיִּהְיֶה כֻּלּוֹ שְׁקֵדִים שְׁקֵדִים » (Rambam sur
    Mena'hot 3:7) — n côtes effilées aux deux bouts."""
    return lambda th, t: 1 - creux * (1 - abs(math.cos(n * th / 2)) ** 0.5) * math.sin(math.pi * t) ** 0.8


def lys(n, creux):
    """« ופרח צורת שושן » (Rambam sur Mena'hot 3:7) : n pétales fendus dans la lèvre — six : CHOIX."""
    return lambda th, t: 1 - creux * (1 - abs(math.cos(n * th / 2)) ** 0.3) * min(1.0, max(0.0, (t - 0.8) / 0.1))


def bec(th, t):
    """Le bec du ner, pincé dans la lèvre du bord, dans la direction du premier méridien."""
    return 1 + NER_BEC * max(0.0, math.cos(th)) ** 14 * min(1.0, max(0.0, (t - 0.3) / 0.6)) ** 1.5


def gavia_profil(rt):
    """« פִּיהֶן רָחָב וְשׁוּלֵיהֶן קָצָר » (Beit HaBe'hira 3:9) : pied serré sur la tige, bouche large."""
    e, h = (R_GAVIA - rt) / 0.36, H_GAVIA
    return [(rt, 0), (rt + 0.12 * e, 0), (rt + 0.12 * e, 0.06 * h), (rt + 0.04 * e, 0.14 * h),
            (rt + 0.07 * e, 0.28 * h), (rt + 0.17 * e, 0.45 * h), (rt + 0.26 * e, 0.63 * h),
            (rt + 0.31 * e, 0.8 * h), (rt + 0.33 * e, 0.92 * h), (rt + 0.36 * e, h), (rt + 0.29 * e, h),
            (rt + 0.27 * e, 0.9 * h), (rt + 0.22 * e, 0.7 * h), (rt + 0.12 * e, 0.52 * h),
            (rt + 0.03 * e, 0.4 * h), (rt / 2, 0.36 * h)]


def kaftor_profil(rt):
    """« אֲרֻכִּין מְעַט כְּבֵיצָה שֶׁשְּׁנֵי רָאשֶׁיהָ כַּדִּין » (Beit HaBe'hira 3:9)."""
    return [(rt + (R_KAFTOR - rt) * (1 - (i / 12 - 1) ** 2) ** 0.4, H_KAFTOR * i / 24) for i in range(25)]


def perach_profil(rt):
    """« כְּמִין קְעָרָה וּשְׂפָתָהּ כְּפוּלָה לַחוּץ » (Beit HaBe'hira 3:9)."""
    lev, d, h = 0.09 * TEFAH, R_PERACH - rt, H_PERACH
    return [(rt, 0), (rt + 0.1 * d, 0.15 * h), (rt + 0.38 * d, 0.45 * h), (rt + 0.72 * d, 0.72 * h),
            (R_PERACH, 0.84 * h), (R_PERACH + lev, 0.9 * h), (R_PERACH + 1.2 * lev, 0.97 * h),
            (R_PERACH + 0.6 * lev, h), (R_PERACH - 0.4 * lev, 0.96 * h), (rt + 0.6 * d, 0.62 * h),
            (rt + 0.2 * d, 0.4 * h), (rt / 2, 0.3 * h)]


def or_cisele(o):
    """Lissé jusqu'aux vrais plis — lèvres, arêtes du yerekh —, et sans biseau : sur des lèvres
    d'un demi-tefa'h il n'écraserait que les bords."""
    o.data.set_sharp_from_angle(angle=math.radians(40))
    o["sans_biseau"] = True
    return o


def gavia(nom, centre, axe, rt):
    """`GEVIIM_RENVERSES` : bouche vers le bas, comme au dessin du Rambam."""
    a = Vector(axe).normalized()
    sens = -a if GEVIIM_RENVERSES else a
    pied = Vector(centre) - sens * H_GAVIA / 2
    return or_cisele(revolution_axe(f"{nom}_gavia", pied, sens, gavia_profil(rt), "70_Kelim",
                                    MAT_OR_MIKSHE(), 40, forme=cotes_amande(6, 0.18)))


def kaftor(nom, centre, axe, rt):
    a = Vector(axe).normalized()
    return or_cisele(revolution_axe(f"{nom}_kaftor", Vector(centre) - a * H_KAFTOR / 2, a, kaftor_profil(rt),
                                    "70_Kelim", MAT_OR_MIKSHE(), 32))


def perach(nom, base, rt):
    return or_cisele(revolution_axe(f"{nom}_perach", base, (0, 0, 1), perach_profil(rt), "70_Kelim",
                                    MAT_OR_MIKSHE(), 72, forme=lys(6, 0.3)))


def point_du_chemin(chemin, s):
    """Point et tangente à `s` amot du début d'une ligne brisée."""
    for p, q in zip(chemin, chemin[1:]):
        pas = q - p
        if s <= pas.length or q is chemin[-1]:
            return p + pas.normalized() * s, pas.normalized()
        s -= pas.length


def menora_pied(nom, x, y):
    """« וְשָׁלֹשׁ רַגְלַיִם הָיוּ לָהּ » (Beit HaBe'hira 3:2), sous le yerekh, « כְּמִין תֵּבָה »
    d'où elles descendent (Rashi sur Shemot 25:31) — hexagonal : CHOIX. Puis la fleur
    « סָמוּךְ לִירֵכָהּ » (Beit HaBe'hira 3:1)."""
    or_cisele(revolution_axe(f"{nom}_yerekh", (x, y, Z_BAT), (0, 0, 1), YEREKH_PROFIL, "70_Kelim",
                             MAT_OR_MIKSHE(), 6, depart=(-1, 0, 0)))
    for k, angle in enumerate((180, 60, -60)):
        cap = Vector((math.cos(math.radians(angle)), math.sin(math.radians(angle)), 0))
        haut = Vector((x, y, Z_BAT + 1.2 * TEFAH)) + cap * 0.9 * TEFAH
        bas = Vector((x, y, Z_BAT + 0.4 * TEFAH)) + cap * 4.0 * TEFAH
        L = (bas - haut).length
        or_cisele(revolution_axe(f"{nom}_regel_{k}", haut, bas - haut,
                                 [(0.6 * TEFAH, 0), (0.54 * TEFAH, 0.2 * L), (0.44 * TEFAH, 0.5 * L),
                                  (0.54 * TEFAH, 0.56 * L), (0.54 * TEFAH, 0.6 * L), (0.42 * TEFAH, 0.66 * L),
                                  (0.36 * TEFAH, L)], "70_Kelim", MAT_OR_MIKSHE(), 24))
        or_cisele(revolution_axe(f"{nom}_regel_{k}_patin", (bas.x, bas.y, Z_BAT), (0, 0, 1),
                                 [(0, 0), (0.62 * TEFAH, 0), (0.66 * TEFAH, 0.1 * TEFAH), (0.54 * TEFAH, 0.26 * TEFAH),
                                  (0.3 * TEFAH, 0.44 * TEFAH), (0, 0.46 * TEFAH)], "70_Kelim", MAT_OR_MIKSHE(), 32))
    perach(f"{nom}_pied", (x, y, Z_BAT + YEREKH_HAUT * TEFAH), TIGE_R)


def menora_tige(nom, x, y):
    """La tige tefa'h par tefa'h (Mena'hot 28b ; Beit HaBe'hira 3:10) : pied et fleur 3, lisse 2,
    coupe-bouton-fleur 1, lisse 2, trois boutons à branches séparés d'un tefa'h lisse, lisse 2,
    et trois coupes, un bouton et une fleur dans les trois derniers."""
    z = lambda t: Z_BAT + t * TEFAH
    haut = (0, 0, 1)
    cyl_between(f"{nom}_tige", (x, y, z(YEREKH_HAUT - 0.1)), (x, y, z(SOMMET + 0.05)), TIGE_R, "70_Kelim", MAT_OR_MIKSHE(), verts=24)
    gavia(f"{nom}_tige_0", (x, y, z(5) + H_GAVIA / 2), haut, TIGE_R)
    kaftor(f"{nom}_tige_0", (x, y, z(5) + H_GAVIA + H_KAFTOR / 2), haut, TIGE_R)
    perach(f"{nom}_tige_0", (x, y, z(6) - H_PERACH), TIGE_R)
    for h, _ in PAIRES:
        kaftor(f"{nom}_tige_{h:g}", (x, y, z(h)), haut, TIGE_R)
    for j, sous in enumerate(SOUS_GEVIIM):
        gavia(f"{nom}_tige_{j + 1}", (x, y, z(SOMMET) - sous), haut, TIGE_R)
    kaftor(f"{nom}_tige_haut", (x, y, z(SOMMET) - SOUS_KAFTOR), haut, TIGE_R)


def menora_branche(nom, chemin):
    """Une branche : trois coupes, un bouton, puis la fleur (Beit HaBe'hira 3:2), aux mêmes
    distances sous la lampe que sur la tige — leur place le long de la branche : CHOIX."""
    for i, (p, q) in enumerate(zip(chemin, chemin[1:])):
        cyl_between(f"{nom}_{i}", p[:], q[:], BRANCHE_R, "70_Kelim", MAT_OR_MIKSHE(), verts=24)
    or_cisele(sphere(f"{nom}_noeud", *chemin[-1], BRANCHE_R * 1.05, "70_Kelim", MAT_OR_MIKSHE(), segs=16))
    longueur = sum((q - p).length for p, q in zip(chemin, chemin[1:]))
    kaftor(nom, *point_du_chemin(chemin, longueur - SOUS_KAFTOR), BRANCHE_R)
    for j, sous in enumerate(SOUS_GEVIIM):
        gavia(f"{nom}_{j}", *point_du_chemin(chemin, longueur - sous), BRANCHE_R)


def chemin_branche(x, y, h, ecart):
    depart = Vector((x, y, Z_BAT + h * TEFAH))
    montee = (SOMMET - h) * TEFAH
    if MENORA_DROITE:
        return [depart, depart + Vector((0, ecart, montee))]
    arc = (math.pi / 2 * i / 16 for i in range(17))
    return [depart + Vector((0, ecart * math.sin(a), montee * (1 - math.cos(a)))) for a in arc]


def menora_ner(nom, sommet, vers):
    """La fleur et son ner « כְּמִין בָּזֵךְ » (Rashi sur Shemot 25:31), fixé à la branche
    (Beit HaBe'hira 3:7), bec tourné vers `vers`, l'huile et la mèche couchée dans le bec.
    Rend le bout de la mèche, où brûle la flamme."""
    perach(nom, sommet, BRANCHE_R)
    base = Vector(sommet) + Vector((0, 0, 0.12 * TEFAH))
    or_cisele(revolution_axe(f"{nom}_ner", base, (0, 0, 1), NER_PROFIL, "70_Kelim", MAT_OR_MIKSHE(), 48,
                             depart=vers, forme=bec))
    shemen = revolution_axe(f"{nom}_ner_shemen", base, (0, 0, 1),
                            [(0.8 * NER_R, (NIVEAU_SHEMEN - 0.05) * NER_H), (0.8 * NER_R, NIVEAU_SHEMEN * NER_H)],
                            "70_Kelim", MAT_SHEMEN(), 48, depart=vers, forme=lambda th, _: bec(th, NIVEAU_SHEMEN))
    v = Vector(vers).normalized()
    bout = base + v * 1.62 * NER_R + Vector((0, 0, NER_H + 0.08 * TEFAH))
    petila = cyl_between(f"{nom}_ner_petila", (base + v * 0.7 * NER_R + Vector((0, 0, 0.6 * NER_H)))[:], bout[:],
                         PETILA_R, "70_Kelim", MAT_PETILA(), verts=8)
    shemen["sans_biseau"] = petila["sans_biseau"] = True
    return bout


def menora(nom, x, y, allumee):
    """Menora de 18 tefa'him, sept branches dans le plan N-S ; `allumee` : ses sept flammes.
    Les six becs regardent la lampe du milieu, dont le bec regarde le Kodesh HaKodashim,
    à l'ouest (Beit HaBe'hira 3:8)."""
    menora_pied(nom, x, y)
    menora_tige(nom, x, y)
    becs = {"centre": menora_ner(f"{nom}_centre", (x, y, Z_BAT + SOMMET * TEFAH), (-1, 0, 0))}
    for h, pas in PAIRES:
        for s, cote in ((-1, "S"), (1, "N")):
            chemin = chemin_branche(x, y, h, s * pas * PAS_NER)
            menora_branche(f"{nom}_branche_{pas}{cote}", chemin)
            becs[f"{pas}{cote}"] = menora_ner(f"{nom}_branche_{pas}{cote}", chemin[-1], (0, -s, 0))
    if not allumee:
        return
    # Une lampe ponctuelle par mèche. Les becs se donnent en coordonnées et non en relisant
    # leur objet : un volume construit en bpy.data porte sa position dans son maillage.
    for suffixe, pointe in becs.items():
        l = lampe(f"{nom}_flamme_{suffixe}", 'POINT', tuple(m(c) for c in pointe))
        l.data.energy = 15
        l.data.color = (1.0, 0.75, 0.4)
        l.data.shadow_soft_size = m(0.05)
        link_to(l, "70_Kelim")


def kuz(nom, x, y, z):
    """Le kuz, « דּוֹמֶה לְקִיתוֹן גָּדוֹל שֶׁל זָהָב » (Tamid 3:6), laissé entre les deux
    préparations « עַל מַעֲלָה שְׁנִיָּה » (Tamid 3:9, 6:1) ; bec vers la Menora. Taille : CHOIX."""
    bec_kuz = lambda th, t: 1 + 0.5 * max(0.0, math.cos(th)) ** 10 * min(1.0, max(0.0, (t - 0.82) / 0.18))
    or_cisele(revolution_axe(nom, (x, y, z), (0, 0, 1),
                             [(0, 0), (0.62 * TEFAH, 0), (0.7 * TEFAH, 0.1 * TEFAH), (1.05 * TEFAH, 0.8 * TEFAH),
                              (1.12 * TEFAH, 1.2 * TEFAH), (0.95 * TEFAH, 1.75 * TEFAH), (0.5 * TEFAH, 2.1 * TEFAH),
                              (0.42 * TEFAH, 2.3 * TEFAH), (0.55 * TEFAH, 2.55 * TEFAH), (0.6 * TEFAH, 2.62 * TEFAH),
                              (0.5 * TEFAH, 2.62 * TEFAH), (0.36 * TEFAH, 2.35 * TEFAH), (0, 2.2 * TEFAH)],
                             "70_Kelim", MAT_OR(), 40, depart=(0, -1, 0), forme=bec_kuz))
    or_cisele(tore(f"{nom}_anse", x, y + 1.0 * TEFAH, z + 1.4 * TEFAH, 0.45 * TEFAH, 0.09 * TEFAH, "70_Kelim",
                   MAT_OR(), rotation=(math.pi / 2, 0, math.pi / 2), majeur=32, mineur=12))


menora("Menora", XU, YM, allumee=True)
kuz("Menora_kuz", XU + 1.8, YM + 0.9, Z_BAT + 0.6)
