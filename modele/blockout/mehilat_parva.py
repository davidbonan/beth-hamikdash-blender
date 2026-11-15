from .primitives.parametres import Z_AZ, Z_HAR
from .primitives.matieres import MAT_MURAILLE, MAT_ROC_TAILLE
from .primitives.volumes import box, plage
from .azara import AY0
from .heil import SY0
from .lishkot import PV_X1


# ----------------------------------------------------------------------------
# 20ter — LA GALERIE DE PARVA, sous le 'Heil, jusqu'au mur sud de la Lishkat HaParva
# ----------------------------------------------------------------------------
# « מַאי ״פַּרְוָה״? אָמַר רַב יוֹסֵף: פַּרְוָה אַמְגּוּשָׁא » (Yoma 35a). Le Arukh (Tosafot ad loc.) : « חפר מחילה
# תחת הקרקע בקדש עד שיראה עבודת כהן גדול » ; le Rambam (sur Middot 5:3) : « חתר בקיר העזרה בלשכה זו ».
# La scène montre les deux : une galerie sous le sol, un puits, une brèche rebouchée au pied du mur.
# Elle part d'au-delà du Soreg, que le mage ne pouvait franchir (Kelim 1:8). Tracé, profondeur,
# section, puits, prises et bouchages : CHOIX, aucune source ne les donne.
#
# Tout est une doublure de roc posée DANS les masses pleines, qu'on ne perce pas : vue du dedans,
# elle seule a des faces. Au-dessus du dallage, le puits et la brèche portent le nom de la chambre :
# l'emprise d'un lieu est sa boîte, et une galerie montant jusqu'au sol de l'Azara aurait fait de toute
# la bande du 'Heil au-dessus d'elle « la galerie de Parva ».
EP = 0.5                                  # la doublure
BRECHE_X = (PV_X1 - 2.6, PV_X1 - 0.6)     # entre la banquette des peaux et le mur est de la chambre
GX0, GX1 = BRECHE_X
GZ0 = Z_HAR - 6                           # deux amot de roc et le dallage au-dessus de la voûte
GZ1 = GZ0 + 4
Z_SOUS_DALLAGE = Z_HAR - 1                # le dessus du soubassement, sous HarHabayit_sol
BOUCHE_Y = (SY0 - 4, SY0 - 2)             # trois amot au-delà du Soreg
PUITS_Y = (AY0 - 3, AY0 - 0.8)            # sous le mur sud de l'Azara
Z_BRECHE = (Z_AZ, Z_AZ + 2.5)
COL = "80_Lishkot"


def doublure(nom, x0, x1, y0, y1, z0, z1):
    box(nom, x0, x1, y0, y1, z0, z1, COL, MAT_ROC_TAILLE())


# La galerie, entre les deux puits.
doublure("Mehilat_Parva_sol", GX0 - EP, GX1 + EP, BOUCHE_Y[0] - EP, PUITS_Y[0], GZ0 - EP, GZ0)
doublure("Mehilat_Parva_voute", GX0 - EP, GX1 + EP, BOUCHE_Y[1], PUITS_Y[0], GZ1, GZ1 + EP)
for cote, xa, xb in (("O", GX0 - EP, GX0), ("E", GX1, GX1 + EP)):
    doublure(f"Mehilat_Parva_paroi_{cote}", xa, xb, BOUCHE_Y[1], PUITS_Y[0], GZ0, GZ1)

# Le puits du départ, fermé de pierres sous le dallage ; en surface, une dalle qui ne ressemble pas aux autres.
for cote, xa, xb in (("O", GX0 - EP, GX0), ("E", GX1, GX1 + EP)):
    doublure(f"Mehilat_Parva_bouche_{cote}", xa, xb, BOUCHE_Y[0] - EP, BOUCHE_Y[1] + EP, GZ0, Z_SOUS_DALLAGE)
doublure("Mehilat_Parva_bouche_S", GX0, GX1, BOUCHE_Y[0] - EP, BOUCHE_Y[0], GZ0, Z_SOUS_DALLAGE)
doublure("Mehilat_Parva_bouche_N", GX0, GX1, BOUCHE_Y[1], BOUCHE_Y[1] + EP, GZ1, Z_SOUS_DALLAGE)
box("Mehilat_Parva_bouche_bouchon", GX0, GX1, *BOUCHE_Y, Z_SOUS_DALLAGE - 1, Z_SOUS_DALLAGE, COL, MAT_MURAILLE())
box("Mehilat_Parva_dalle", GX0 - EP, GX1 + EP, BOUCHE_Y[0] - EP, BOUCHE_Y[1] + EP, Z_HAR, Z_HAR + 0.03,
    COL, MAT_MURAILLE())


# Le puits sous le mur et ses prises : le bas, sous le dallage, avec la galerie ; le haut avec la chambre.
def puits(nom, z0, z1):
    for cote, xa, xb in (("O", GX0 - EP, GX0), ("E", GX1, GX1 + EP)):
        doublure(f"{nom}_{cote}", xa, xb, PUITS_Y[0] - EP, PUITS_Y[1] + EP, z0, z1)
    doublure(f"{nom}_S", GX0, GX1, PUITS_Y[0] - EP, PUITS_Y[0], max(z0, GZ1), z1)
    doublure(f"{nom}_N", GX0, GX1, PUITS_Y[1], PUITS_Y[1] + EP, z0, min(z1, Z_BRECHE[0]))
    for k, z in enumerate(z for z in plage(GZ0 + 1.5, Z_BRECHE[0] - 1, 1.5) if z0 <= z < z1):
        box(f"{nom}_prise_{k:02d}", GX0 + 0.6, GX1 - 0.6, PUITS_Y[1] - 0.3, PUITS_Y[1], z, z + 0.25, COL,
            MAT_ROC_TAILLE())


doublure("Mehilat_Parva_puits_sol", GX0 - EP, GX1 + EP, PUITS_Y[0], PUITS_Y[1] + EP, GZ0 - EP, GZ0)
puits("Mehilat_Parva_puits", GZ0, Z_SOUS_DALLAGE)
puits("Lishkat_HaParva_breche_puits", Z_SOUS_DALLAGE, Z_BRECHE[1])
doublure("Lishkat_HaParva_breche_puits_haut", GX0 - EP, GX1 + EP, PUITS_Y[0] - EP, AY0, Z_BRECHE[1], Z_BRECHE[1] + EP)

# Trois pierres de bouchage, une ama et demie de face au plus, joints laissés au mur : elles
# affleurent d'un doigt devant lui, comme une reprise.
for k, (x0, x1, z0, z1) in enumerate(((GX0, GX0 + 1.1, Z_BRECHE[0], Z_BRECHE[0] + 1.2),
                                      (GX0 + 1.14, GX1, Z_BRECHE[0], Z_BRECHE[0] + 1.2),
                                      (GX0, GX1, Z_BRECHE[0] + 1.24, Z_BRECHE[1]))):
    box(f"Lishkat_HaParva_breche_{k}", x0, x1, PUITS_Y[1], AY0 + 0.04, z0, z1, COL, MAT_MURAILLE())
