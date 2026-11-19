from ..primitives.parametres import Z_EZN

# Le tracé seul, sans rien bâtir : le Har HaBayit et l'Ezrat Nashim, bâtis avant les galeries, s'y évident.
# « בָּנָה בּוֹ מָקוֹם לִגְנֹז בּוֹ הָאָרוֹן לְמַטָּה בְּמַטְמוֹנִיּוֹת עֲמֻקוֹת וַעֲקַלְקַלּוֹת » (Beit HaBe'hira 4:1). Tracé, cotes, degrés : CHOIX.
RITZPA_MESHUNA = (120, 124, 41.316, 49.316)
LARGEUR, HAUTEUR = 3, 5
Z_TETE = Z_EZN - 1
Z_PUITS = -20
Z_CHAMBRE = -40
BLOC = (102, 138, 29, 66, Z_CHAMBRE - 1, Z_TETE)


def _volee(xy_haut, xy_volee, xy_bas, z_haut, z_bas):
    """Un palier haut, sa volée et le palier bas : le plafond suit le palier haut jusqu'au pied de la volée."""
    return [(*xy_haut, z_haut, z_haut + HAUTEUR), (*xy_volee, z_bas, z_haut + HAUTEUR), (*xy_bas, z_bas, z_bas + HAUTEUR)]


Y_G1 = (43.8, 46.8)
X_G2 = (108, 111)
Y_G3 = (59, 62)
X_G4 = (131, 134)
VOLEES = [
    dict(nom="ouest", emprise=(113, 118, *Y_G1), z=(Z_PUITS, -25), descente="-x"),
    dict(nom="nord", emprise=(*X_G2, 49, 54), z=(-25, -30), descente="+y"),
    dict(nom="est", emprise=(120, 125, *Y_G3), z=(-30, -35), descente="+x"),
    dict(nom="sud", emprise=(*X_G4, 47, 52), z=(-35, Z_CHAMBRE), descente="-y"),
]
CHAMBRE = (124, 136, 30, 38)
ARON_GANUZ = (130, 34)
IMPASSE = (103, 108, 56, 59)

# « לֹא יָסֻרוּ מִמֶּנּוּ » (Shemot 25:15), « בַּכָּתֵף יִשָּׂאוּ » (Bamidbar 7:9) : l'Arche passe les virages avec ses barres sur l'épaule.
# CHOIX : l'angle intérieur de chaque virage abattu de deux amot. (x, y) de l'angle, (sx, sy) vers le roc, sol.
ABATTU = 2
BISEAUX = [((111, Y_G1[1]), (1, 1), -25), ((X_G2[1], Y_G3[0]), (1, -1), -30), ((X_G4[0], Y_G3[0]), (-1, -1), -35)]

# CHOIX : ceux qui ont creusé s'éclairaient à la lampe, posée dans une niche à hauteur de poitrine. (x, y) au nu du mur, sens vers le roc, sol.
NICHE_LARGEUR, NICHE_HAUTEUR, NICHE_PROFONDEUR, ALLEGE = 0.7, 0.6, 0.5, 2.6
NICHES = [((124, 45.3), (1, 0), Z_PUITS), ((110, Y_G1[0]), (0, -1), -25), ((X_G2[0], 60.5), (-1, 0), -30),
          ((128.5, Y_G3[1]), (0, 1), -35), ((127, CHAMBRE[3]), (0, 1), Z_CHAMBRE), ((CHAMBRE[1], 34), (1, 0), Z_CHAMBRE)]


def _etendue(c, s):
    return sorted((c, c + s * NICHE_PROFONDEUR)) if s else [c - NICHE_LARGEUR / 2, c + NICHE_LARGEUR / 2]


def niche(mur, sens, sol):
    return (*_etendue(mur[0], sens[0]), *_etendue(mur[1], sens[1]), sol + ALLEGE, sol + ALLEGE + NICHE_HAUTEUR)


# CHOIX : au fond de l'impasse, un pan du plafond est tombé ; son tas est dans siecles.py.
EFFONDREMENT = [(IMPASSE[0], 105.2, 56.3, 58.6, -25, -24.5), (103.5, 104.7, 56.8, 58.0, -24.5, -24.2)]

VIDES = [
    (*RITZPA_MESHUNA, Z_PUITS, Z_TETE),
    *_volee((118, 120, *Y_G1), (113, 118, *Y_G1), (X_G2[0], 113, *Y_G1), Z_PUITS, -25),
    *_volee((*X_G2, Y_G1[1], 49), (*X_G2, 49, 54), (*X_G2, 54, Y_G3[1]), -25, -30),
    (*IMPASSE, -30, -30 + HAUTEUR),
    *_volee((X_G2[1], 120, *Y_G3), (120, 125, *Y_G3), (125, X_G4[1], *Y_G3), -30, -35),
    *_volee((*X_G4, 52, Y_G3[0]), (*X_G4, 47, 52), (*X_G4, CHAMBRE[3], 47), -35, Z_CHAMBRE),
    (*CHAMBRE, Z_CHAMBRE, Z_CHAMBRE + 8),
    *[(*sorted((x, x + sx * ABATTU)), *sorted((y, y + sy * ABATTU)), z, z + HAUTEUR) for (x, y), (sx, sy), z in BISEAUX],
    *[niche(*n) for n in NICHES],
    *EFFONDREMENT,
]
