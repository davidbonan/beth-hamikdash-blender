import bpy

from ..primitives.parametres import AMA, RACINE, Z_BAT
from ..primitives.matieres import MAT_OR, MAT_PAROKHET
from ..primitives.volumes import ellipsoide, mesh_from_pydata, sphere
from .heikhal import ARON_Y_BAD, ARON_Z_BAD, TR0, TR1


# --- Les deux Parokhot (Yoma 5:1) : « הַחִיצוֹנָה הָיְתָה פְרוּפָה מִן הַדָּרוֹם, וְהַפְּנִימִית מִן הַצָּפוֹן ».
#     « אָרְכָּהּ אַרְבָּעִים אַמָּה וְרָחְבָּהּ עֶשְׂרִים אַמָּה », « עָבְיָהּ טֶפַח » (Shekalim 8:5).
PAROKHET_EP = 1 / 6            # טפח : l'épaisseur que la michna donne à l'étoffe
PERIFA_BLEND = RACINE / "perifa.blend"
PERIFA_HAUT = 24               # amot : la hauteur que la simulation de tissu tient ; au-dessus, l'étoffe pend à plat


def etoffe_en_x(name, contour, x0, x1, col, mat):
    """Étoffe plane tendue en travers de l'axe E-O : `contour`, des (y, z) en amot dans
    le sens direct vu de l'est, épaissie de x0 à x1."""
    n = len(contour)
    verts = [(x0, y, z) for y, z in contour] + [(x1, y, z) for y, z in contour]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return mesh_from_pydata(name, verts, faces, col, mat)


def perifa(nom):
    """Le coin replié de la parokhet `nom` et son anneau, lus dans `perifa.blend`.

    C'est `beit_hamikdash_perifa.py` qui les simule en tissu, chacun avec le rideau voisin
    pour obstacle. Les maillages sont en mètres, dans le repère du coin : x depuis le mur,
    y vers l'est, z depuis le sol.
    """
    with bpy.data.libraries.load(str(PERIFA_BLEND)) as (_, charge):
        charge.meshes = [f"Perifa_{nom}", f"Perifa_{nom}_keres"]
    return charge.meshes


def coin_replie(name, modele, x_pli, cote, col, mat):
    """Le coin simulé, posé contre le rideau : x du coin court vers le centre depuis le mur
    `cote` (+1 nord, -1 sud), y du coin vers l'est. Au sud, ce repère retourne l'espace et
    les faces se relisent à l'envers."""
    verts = [(x_pli + v.co.y / AMA, cote * (10 - v.co.x / AMA), Z_BAT + v.co.z / AMA)
             for v in modele.vertices]
    faces = [list(f.vertices) if cote > 0 else list(f.vertices)[::-1] for f in modele.polygons]
    o = mesh_from_pydata(name, verts, faces, col, mat)
    o.data.shade_smooth()
    return o


def parokhet_perufa(name, nom_coin, x_ouest, cote):
    """Rideau de mur à mur dont le coin du côté `cote` est relevé par-dessus l'étoffe et
    tenu par un keres d'or : ce que le repli découvre est le passage.

    « פְּרוּפָה — רֹאשָׁהּ כְּפוּלָה לְצַד הַחִיצוֹן וְנֶאֱחֶזֶת בְּקֶרֶס שֶׁל זָהָב לִהְיוֹת פְּתוּחָה וְעוֹמֶדֶת »
    (Rashi Yoma 52b ; Bartenura 5:1). Le rideau a la largeur du Heikhal et se replie sur
    lui-même (Rashash, ibid.) ; Tosfot Yom Tov, qui le fait déborder le long du mur, est écarté.
    Le pan plat s'arrête où commence le coin simulé, dont les bords y restent épinglés.
    """
    def direct(points):                                          # sens direct vu de l'est
        contour = [(cote * (10 - u), Z_BAT + z) for u, z in points]
        return contour if cote < 0 else contour[::-1]

    etoffe_en_x(name, direct([(0, PERIFA_HAUT), (20, PERIFA_HAUT), (20, 40), (0, 40)]),
                x_ouest, x_ouest + PAROKHET_EP, "60_KodeshHakodashim", MAT_PAROKHET())
    etoffe, anneau = perifa(nom_coin)
    x_pli = x_ouest + PAROKHET_EP / 2
    coin_replie(f"{name}_coin", etoffe, x_pli, cote, "60_KodeshHakodashim", MAT_PAROKHET())
    coin_replie(f"{name}_keres", anneau, x_pli, cote, "60_KodeshHakodashim", MAT_OR())
    bpy.data.meshes.remove(etoffe)
    bpy.data.meshes.remove(anneau)


parokhet_perufa("Parokhet_ext", "ext", TR0 - PAROKHET_EP, -1)
parokhet_perufa("Parokhet_int", "int", TR1, +1)
# Le motif est dans la matière (voir `parokhet`), et le même sur les deux faces. Un
# maassé 'hoshev en porte un AUTRE au revers — « מצד זה ארי ומצד זה נשר » (Rashi sur Yoma
# 72b) ; aucun plan ne cadre le revers, et il n'est pas tissé.
# Les badim de l'Arche pressent le rideau et se voient du Heikhal « כִּשְׁנֵי דַּדֵּי אִשָּׁה »
# (Yoma 54a ; Mena'hot 98b ; Melakhim I 8:8). Yoma 54a n'a qu'une parokhet ; avec deux, la
# barre emporte l'intérieure à travers l'ama de Traksin jusqu'à l'extérieure, qui bombe
# seule dans le Heikhal. Rien de ces volumes ne passe à l'ouest de la parokhet intérieure.
TRAKSIN_VIDE = (TR0 - PAROKHET_EP) - (TR1 + PAROKHET_EP)
for ns, y in (("N", ARON_Y_BAD), ("S", -ARON_Y_BAD)):
    ellipsoide(f"Parokhet_int_tension_{ns}", (TR0 + TR1) / 2, y, ARON_Z_BAD,
               (TRAKSIN_VIDE / 2, 0.3, 0.3), "60_KodeshHakodashim", MAT_PAROKHET())
    ellipsoide(f"Parokhet_ext_tension_{ns}", TR0 - PAROKHET_EP, y, ARON_Z_BAD,
               (PAROKHET_EP + 0.25, 0.92, 0.92), "60_KodeshHakodashim", MAT_PAROKHET())
    sphere(f"Parokhet_ext_bosse_{ns}", TR0 + 0.16, y, ARON_Z_BAD, 0.36,
           "60_KodeshHakodashim", MAT_PAROKHET())
