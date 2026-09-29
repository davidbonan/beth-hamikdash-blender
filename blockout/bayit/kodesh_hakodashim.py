import bpy
import math
from mathutils import Vector, noise

from ..primitives.parametres import AMA, RACINE, Z_BAT, m
from ..primitives.matieres import MAT_CEDRE, MAT_CHENE, MAT_OR, MAT_PIERRE, MAT_ROCHE, MAT_TERRE_CUITE, braise
from ..primitives.volumes import (_lisser, _objet, _poser, box, cyl_between, lampe, mesh_from_pydata,
                                  revolution, sphere, tore)
from ..mizbeach import braises
from .heikhal import ARON_X_MACHTA, ARON_Y_BAD, ARON_Z_BAD, KK0, KK1, TR0


# --- Kodesh HaKodashim : Even HaShetiya. « גְּבוֹהָה מִן הָאָרֶץ שָׁלשׁ אֶצְבָּעוֹת » (Yoma 5:2) est sa
#     seule cote : le rocher perce le sol d'or sans jamais le dépasser de 3 doigts, et il
#     est au centre, CHOIX : le « רֶיוַח עֶשֶׂר אַמּוֹת » de Bava Batra 99a est un miracle, pas une place,
#     et le Rambam la met « בְּמַעֲרָבוֹ » (Beit HaBe'hira 4:1).
#     Contour, emprise et relief : CHOIX ; plat là où l'Arche et la ma'hta se posent.
#     C'est du calcaire en place, et il se lit comme tel : un contour à arêtes, cassé le
#     long de ses diaclases, une face verticale sur tout son tour, et un dessus en lits —
#     des paliers plats séparés par des marches d'un doigt, jamais un dôme. La matière
#     (`roche`) y ajoute le piqué et les fissures.
KKC = (KK0 + KK1) / 2
DOIGT = 1 / 24
ZE = Z_BAT + 3 * DOIGT      # le haut de la pierre, où l'Arche se pose
SHETIYA_CENTRE, SHETIYA_DEMI_AXES = (KKC + 0.2, 0.1), (4.1, 4.6)
SHETIYA_ASSISE = (KKC - 0.9, ARON_X_MACHTA + 0.45, -1.45, 1.45)   # l'Arche, ce qui est devant elle, la ma'hta
# Les arêtes du contour, (direction en degrés, rayon en fraction des demi-axes) : le bord
# va droit de l'une à l'autre. Deux rentrants (0,72) sont des blocs partis.
SHETIYA_ARETES = ((0, 1.00), (24, 0.86), (58, 1.04), (85, 0.72), (110, 0.95), (150, 1.02), (172, 0.84),
                  (200, 0.98), (226, 0.90), (262, 1.05), (288, 0.72), (312, 0.94), (340, 0.88))


def _bruit(x, y, frequence, graine):
    """Bruit de Perlin dans [-1, 1] au point (x, y) ; `graine` sépare les couches."""
    return noise.noise(Vector((x * frequence, y * frequence, graine)))


def contour_shetiya(a):
    """Rayon du contour dans la direction `a`, en fraction des demi-axes."""
    aretes = [(math.radians(deg), r) for deg, r in SHETIYA_ARETES]
    a %= 2 * math.pi
    (a0, r0), (a1, r1) = next(((aretes[i - 1], aretes[i]) for i in range(1, len(aretes)) if a < aretes[i][0]),
                              (aretes[-1], (aretes[0][0] + 2 * math.pi, aretes[0][1])))
    p0, p1 = Vector((r0 * math.cos(a0), r0 * math.sin(a0))), Vector((r1 * math.cos(a1), r1 * math.sin(a1)))
    direction = Vector((math.cos(a), math.sin(a)))
    droit = p0.cross(p1) / direction.cross(p1 - p0)
    return droit + 0.012 * _bruit(math.cos(a), math.sin(a), 9.0, 8.3)


def _montee(debut, fin, v):
    t = min(1.0, max(0.0, (v - debut) / (fin - debut)))
    return t * t * (3 - 2 * t)


def dessus_shetiya(x, y):
    """Haut du rocher au-dessus du sol en (x, y) : trois lits en paliers, fendus de diaclases."""
    lit = _bruit(x, y, 0.28, 3.1)
    marches = 1.2 * (1 - _montee(-0.02, 0.06, lit)) + 0.8 * (1 - _montee(-0.40, -0.32, lit))
    fente = 1.4 * (1 - _montee(0.03, 0.07, abs(_bruit(x, y, 1.1, 12.4))))
    grain = 0.12 * _bruit(x, y, 11.0, 23.5)
    rocher = (3 - marches - fente + grain) * DOIGT
    x0, x1, y0, y1 = SHETIYA_ASSISE
    hors_assise = max(x0 - x, x - x1, y0 - y, y - y1, 0.0)
    haut = ZE - Z_BAT
    return min(haut, haut + (rocher - haut) * _montee(0.0, 0.3, hors_assise))


def cote_shetiya(x, y):
    """Cote du dessus du rocher en (x, y), en amot."""
    return Z_BAT + dessus_shetiya(x, y)


def even_hashetiya(name, col, anneaux=64, segs=420):
    """Le rocher en nappe polaire : un dessus en paliers, puis une face droite qui plonge sous l'or."""
    (cx, cy), (ax, ay) = SHETIYA_CENTRE, SHETIYA_DEMI_AXES
    verts = [(cx, cy, cote_shetiya(cx, cy))]
    for i in range(1, anneaux + 1):
        t = i / anneaux
        for s in range(segs):
            a = 2 * math.pi * s / segs
            x, y = cx + ax * t * contour_shetiya(a) * math.cos(a), cy + ay * t * contour_shetiya(a) * math.sin(a)
            verts.append((x, y, cote_shetiya(x, y)))
    verts += [(x, y, Z_BAT - 0.02) for x, y, _ in verts[-segs:]]

    def sommet(i, s):
        return 1 + (i - 1) * segs + s % segs

    faces = [[0, sommet(1, s), sommet(1, s + 1)] for s in range(segs)]
    faces += [[sommet(i, s), sommet(i + 1, s), sommet(i + 1, s + 1), sommet(i, s + 1)]
              for i in range(1, anneaux + 1) for s in range(segs)]
    return _lisser(mesh_from_pydata(name, verts, faces, col, MAT_ROCHE()), 12)


even_hashetiya("Even_HaShetiya", "60_KodeshHakodashim")

# --- Aron HaBrit, posé sur la pierre (Rambam, Beit HaBe'hira 4:1) — le Temple à venir
#     rend l'Arche cachée (Yoma 54a). Cotes : Shemot 25:10-22 ; Soucca 5a-b ; Menachot 98b.
#     2,5 × 1,5 × 1,5 amot, grand côté nord-sud, badim est-ouest le long de la largeur
#     (Menachot 98b), anneaux aux coins supérieurs (Rashi Shemot 25:12), kaporet d'un
#     tefa'h, keruvim de 10 tefa'him, ailes au-dessus des têtes, l'une vers l'autre
#     (Soucca 5b). Les badim courent jusqu'à la parokhet extérieure : c'est ce qui rend
#     physiques « entre les deux badim » (Yoma 5:1, 5:3) et les bosses du rideau.
# « ומצודדים פניהם » (Bava Batra 99a) : entre « וּפְנֵיהֶם אִישׁ אֶל אָחִיו » (Shemot 25:20) et
# « וּפְנֵיהֶם לַבָּיִת » (Divrei HaYamim II 3:13), chaque visage se tourne vers l'est. L'angle : CHOIX.
BIAIS_KERUV = math.radians(20)
KERUVIM_BLEND = RACINE / "keruvim.blend"


def keruvim():
    """Les deux keruvim de la kaporet, lus dans `keruvim.blend`.

    C'est `beit_hamikdash_keruvim.py` qui les bâtit — enfants MakeHuman (« כְּרַבְיָא »,
    Soucca 5b) agenouillés, mains jointes, ailes plumées en dais (Shemot 25:20) — et les y
    écrit : MakeHuman coûte une minute par figure, le blockout se reconstruit en cinq
    secondes. Chaque maillage est dans le repère du keruv, **-x vers l'autre keruv**,
    origine sur la kaporet, et porte `portee` : la distance de l'origine aux mains jointes,
    en mètres — les mains se rejoignent au milieu de la kaporet quel que soit le biais.
    """
    with bpy.data.libraries.load(str(KERUVIM_BLEND)) as (_, charge):
        charge.meshes = ["Keruv_garcon", "Keruv_fille"]
    return charge.meshes


def keruv(name, me, x, y, z0, col, vers):
    """`vers` est le sens en y du centre de la kaporet."""
    me.materials.clear()
    me.materials.append(MAT_OR())
    o = _objet(name, me, col)
    o["sans_biseau"] = True   # 36 000 sommets déjà lissés : le biseau n'y ajouterait que du temps
    _poser([o], x, y, z0, -vers * (math.pi / 2 + BIAIS_KERUV))   # -x vers l'autre keruv, puis vers l'est
    return o

ARON = "65_Aron"
ARON_X0, ARON_X1, ARON_Y = KKC - 0.75, KKC + 0.75, 1.25
Z_KAPORET = ZE + 1.5
box("Aron_caisse", ARON_X0, ARON_X1, -ARON_Y, ARON_Y, ZE, Z_KAPORET, ARON, MAT_OR())
box("Aron_kaporet", ARON_X0, ARON_X1, -ARON_Y, ARON_Y, Z_KAPORET, Z_KAPORET + 1 / 6, ARON, MAT_OR())
# Zer (Shemot 25:11 ; Rashi ; Yoma 72b) : trois caisses emboîtées, la caisse d'or
# extérieure plus haute que les autres — son rebord monte autour de la kaporet et la
# dépasse un peu, « comme une couronne » : le keter Torah. Un bandeau qui entoure la
# kaporet, puis une lèvre plus saillante au sommet.
Z_ZER = Z_KAPORET + 1 / 6 + 0.06
for etage, (saillie, zb, zh) in enumerate(((0.06, Z_KAPORET - 0.14, Z_ZER - 0.05),
                                           (0.10, Z_ZER - 0.05, Z_ZER))):
    for cote, (x0, x1, y0, y1) in (("N", (ARON_X0 - saillie, ARON_X1 + saillie, ARON_Y - 0.02, ARON_Y + saillie)),
                                  ("S", (ARON_X0 - saillie, ARON_X1 + saillie, -ARON_Y - saillie, -ARON_Y + 0.02)),
                                  ("E", (ARON_X1 - 0.02, ARON_X1 + saillie, -ARON_Y - saillie, ARON_Y + saillie)),
                                  ("O", (ARON_X0 - saillie, ARON_X0 + 0.02, -ARON_Y - saillie, ARON_Y + saillie))):
        box(f"Aron_zer{etage}_{cote}", x0, x1, y0, y1, zb, zh, ARON, MAT_OR())

# « וּלְפָנָיו צִנְצֶנֶת הַמָּן וּמַטֵּה אַהֲרֹן » (Rambam, Beit HaBe'hira 4:1) : devant l'Arche, entre les
# badim, la fiole de manne « צְלוֹחִית שֶׁל חֶרֶס » (Rashi Shemot 16:33) et le bâton d'Aharon avec
# ses amandes et ses fleurs (Bamidbar 17:23-25). La fiole d'huile d'onction n'est que
# « cachée avec » l'Arche (Yoma 52b) : sa place devant elle est un CHOIX.
X_DEVANT = ARON_X1 + 0.32
revolution("Aron_tsintsenet_man", X_DEVANT, 0.62, ZE,
           [(0.07, 0), (0.12, 0.05), (0.13, 0.20), (0.09, 0.28), (0.06, 0.31), (0.07, 0.35),
            (0.05, 0.35), (0.0, 0.33)], ARON, MAT_TERRE_CUITE(), verts=16)
revolution("Aron_pakh_shemen", X_DEVANT, -0.62, ZE,
           [(0.06, 0), (0.10, 0.04), (0.10, 0.16), (0.04, 0.22), (0.035, 0.30), (0.05, 0.32),
            (0.0, 0.31)], ARON, MAT_PIERRE(), verts=16)
# Le coffret des Philistins est « מִצִּדּוֹ » (Shmouel I 6:8 ; Bava Batra 14a), à côté de l'Arche
# et non devant : au nord, au-delà du bad — le côté est un CHOIX. Posé au plus bas du rocher.
ARGAZ = (KKC - 0.22, KKC + 0.22, 1.62, 2.02)
Z_ARGAZ = min(cote_shetiya(x, y) for x in ARGAZ[:2] for y in ARGAZ[2:])
box("Aron_argaz", *ARGAZ, Z_ARGAZ, Z_ARGAZ + 0.28, ARON, MAT_CEDRE())
box("Aron_argaz_couvercle", ARGAZ[0] - 0.03, ARGAZ[1] + 0.03, ARGAZ[2] - 0.03, ARGAZ[3] + 0.03,
    Z_ARGAZ + 0.28, Z_ARGAZ + 0.34, ARON, MAT_CEDRE())
PIED_MATE, TETE_MATE = (ARON_X1 + 0.62, -1.02, ZE), (ARON_X1 + 0.02, -1.14, Z_ZER + 0.30)
cyl_between("Aron_mate_Aharon", PIED_MATE, TETE_MATE, 0.03, ARON, MAT_CHENE(), verts=8)
for k, t in enumerate((0.80, 0.88, 0.96)):
    x_ = PIED_MATE[0] + t * (TETE_MATE[0] - PIED_MATE[0])
    y_ = PIED_MATE[1] + t * (TETE_MATE[1] - PIED_MATE[1]) + (0.05 if k % 2 else -0.05)
    z_ = PIED_MATE[2] + t * (TETE_MATE[2] - PIED_MATE[2])
    sphere(f"Aron_mate_amande_{k}", x_, y_, z_, 0.035, ARON, MAT_PIERRE(), segs=8)

# « כְּחִבַּת זָכָר וּנְקֵבָה » (Yoma 54a) ; le garçon au nord et la fille au sud, un peu plus menue : CHOIX.
KERUV_GARCON, KERUV_FILLE = keruvim()
Y_KERUV = 0.05 + KERUV_GARCON["portee"] / AMA * math.cos(BIAIS_KERUV)
keruv("Aron_keruv_N", KERUV_GARCON, KKC, Y_KERUV, Z_KAPORET + 1 / 6, ARON, vers=-1)
keruv("Aron_keruv_S", KERUV_FILLE, KKC, -Y_KERUV, Z_KAPORET + 1 / 6, ARON, vers=1)
for ns, sy in (("N", 1), ("S", -1)):
    for eo, x in (("E", ARON_X1 - 0.10), ("O", ARON_X0 + 0.10)):
        tore(f"Aron_anneau_{ns}{eo}", x, sy * ARON_Y_BAD, ARON_Z_BAD, 0.12, 0.03, ARON,
             MAT_OR(), rotation=(0, math.pi / 2, 0), majeur=24, mineur=8)
    cyl_between(f"Aron_bad_{ns}", (ARON_X0 - 0.5, sy * ARON_Y_BAD, ARON_Z_BAD),
                (TR0 + 0.10, sy * ARON_Y_BAD, ARON_Z_BAD), 0.06, ARON, MAT_OR(), verts=12)

# --- « עַד שֶׁלֹּא נִיטַּל הָאָרוֹן הָיָה נִכְנַס וְיוֹצֵא לְאוֹרוֹ שֶׁלְּאָרוֹן » (Yerushalmi Yoma 5:3) : tant que
#     l'Arche est là, le Cohen Gadol entre et sort à sa lumière ; enlevée, il entre et sort
#     à tâtons. Le film la ramène (§8h), et c'est elle qui éclaire la pièce. La lampe se pose
#     « מֵעַל הַכַּפֹּרֶת מִבֵּין שְׁנֵי הַכְּרֻבִים » (Shemot 25:22), 4,5 W : la pièce reste en pénombre.
# Le creux entre les deux keruvim ne laisse que ~15 cm autour d'elle : toute retouche de leur maillage se revérifie ici.
arche_lueur = lampe("Aron_lumiere", 'POINT', (m(KKC), 0.0, m(Z_KAPORET + 1 / 6 + 0.35)))
arche_lueur.data.energy = 4.5
arche_lueur.data.color = (1.0, 0.93, 0.82)
arche_lueur.data.shadow_soft_size = m(0.20)

# --- La ma'hta de Kippour, « בֵּין שְׁנֵי הַבַּדִּים » (Yoma 5:1), posée sur la pierre devant la
#     face est de l'Arche. Ce jour-là elle est d'or, tient trois kabin, est légère et son
#     manche est long, pour que l'avant-bras en porte le poids (Yoma 4:4) ; le Cohen Gadol
#     l'a portée de la main droite (Rambam, Avodat Yom HaKippurim 4:1). Bassin tronconique
#     de 0,52 à 0,60 ama sur 0,16 de haut, manche rond de 1,1 ama vers l'est, d'où il vient :
#     formes et cotes sont un CHOIX (fiche §8g). Ses braises brûlent la ketoret ; la lumière
#     de la pièce vient de l'Arche, elles n'en sont que le point chaud.
Z_MACHTA = cote_shetiya(ARON_X_MACHTA, 0)
revolution("Machta_bassin", ARON_X_MACHTA, 0, Z_MACHTA,
           [(0.24, 0.0), (0.26, 0.0), (0.30, 0.16), (0.325, 0.165), (0.325, 0.185), (0.295, 0.185),
            (0.275, 0.16), (0.235, 0.03), (0.0, 0.03)], ARON, MAT_OR(), verts=32)
# Le bassin est plein : les charbons affleurent le bord et s'y entassent.
braises("Machta_gehalim", ARON_X_MACHTA - 0.17, ARON_X_MACHTA + 0.17, -0.17, 0.17, Z_MACHTA + 0.185,
        ARON, braise("Braise"), maille=0.06, relief=0.10, profondeur=0.12)
X_POMMEAU = ARON_X_MACHTA + 0.30 + 1.1
Z_POMMEAU = cote_shetiya(X_POMMEAU, 0) + 0.04
cyl_between("Machta_manche", (ARON_X_MACHTA + 0.28, 0, Z_MACHTA + 0.14), (X_POMMEAU, 0, Z_POMMEAU),
            0.035, ARON, MAT_OR(), verts=12)
_lisser(sphere("Machta_pommeau", X_POMMEAU, 0, Z_POMMEAU, 0.055, ARON, MAT_OR(), segs=20), 20)
# 3 W : ce que pèse un bassin de charbons à côté de l'Arche (fiche §1, flammes de la Menora à 15).
machta_lueur = lampe("Machta_braise", 'POINT', (m(ARON_X_MACHTA), 0.0, m(Z_MACHTA + 0.22)))
machta_lueur.data.energy = 3
machta_lueur.data.color = (1.0, 0.45, 0.15)
machta_lueur.data.shadow_soft_size = m(0.12)
