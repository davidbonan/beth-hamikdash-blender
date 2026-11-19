import math

from mathutils import Vector, noise

from ..primitives.matieres import MAT_POUSSIERE, MAT_ROC_TAILLE
from ..primitives.volumes import box, mesh_from_pydata
from ..bayit.kodesh_hakodashim import (ARGAZ, ARON_X0, ARON_X1, ARON_Y, KKC, MATE_RAYON, PAKH_SHEMEN, PIED_MATE,
                                       TETE_MATE, TSINTSENET, X_DEVANT, Y_DEVANT)
from .trace import ARON_GANUZ, CHAMBRE, X_G4, Z_CHAMBRE

COL = "10_EzratNashim"


def fbm(x, y, graine, octaves=3):
    total, amplitude = 0.0, 0.5
    for o in range(octaves):
        total += amplitude * noise.noise(Vector((x, y, graine + 7.1 * o)))
        x, y, amplitude = x * 2.03, y * 2.03, amplitude * 0.5
    return total


def lisse(a, b, t):
    t = min(max((t - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def nappe(nom, emprise, z, maille, epaisseur, mat):
    """Une surface de hauteur `z + epaisseur(x, y)` sur l'emprise, d'un seul tenant : ce que la poussière a posé."""
    x0, x1, y0, y1 = emprise
    nx, ny = max(2, round((x1 - x0) / maille)), max(2, round((y1 - y0) / maille))
    sommets = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            sommets.append((x, y, z + epaisseur(x, y)))
    rang = nx + 1
    faces = [[j * rang + i, j * rang + i + 1, (j + 1) * rang + i + 1, (j + 1) * rang + i] for j in range(ny) for i in range(nx)]
    o = mesh_from_pydata(nom, sommets, faces, COL, mat)
    o.data.shade_smooth()
    o["sans_biseau"] = True
    return o


# « נִגְנְזָה עִמּוֹ צִנְצֶנֶת הַמָּן, וּצְלוֹחִית שֶׁמֶן הַמִּשְׁחָה, וּמַקְלוֹ שֶׁל אַהֲרֹן… וְאַרְגָּז » (Yoma 52b). La visite les a rendus au
# Kodesh HaKodashim : ici, leur place reste dans la poussière, disposée comme là-bas. Socle et poussière : CHOIX.
def ici(x, y):
    return ARON_GANUZ[0] + x - KKC, ARON_GANUZ[1] + y


def rectangle(x0, x1, y0, y1):
    (a, c), (b, d) = ici(x0, y0), ici(x1, y1)
    return lambda x, y: math.hypot(max(a - x, 0, x - b), max(c - y, 0, y - d)) + min(max(a - x, x - b, c - y, y - d), 0)


def rond(cx, cy, profil):
    (a, b), r = ici(cx, cy), max(rayon for rayon, _ in profil)
    return lambda x, y: math.hypot(x - a, y - b) - r


def baton():
    (a, b0), longueur = ici(PIED_MATE[0], PIED_MATE[1]), math.dist(PIED_MATE, TETE_MATE)
    return lambda x, y: math.hypot(x - a, y - min(max(y, b0), b0 + longueur)) - MATE_RAYON


PLACES = [rectangle(ARON_X0, ARON_X1, -ARON_Y, ARON_Y), rond(X_DEVANT, Y_DEVANT, TSINTSENET),
          rond(X_DEVANT, -Y_DEVANT, PAKH_SHEMEN), rectangle(ARGAZ[0] - 0.03, ARGAZ[1] + 0.03, ARGAZ[2] - 0.03, ARGAZ[3] + 0.03),
          baton()]
MARGE, H_SOCLE, AVAK = 0.4, 0.5, 0.02
SX0, SY0 = ici(ARON_X0, -ARON_Y)
SX1, SY1 = ici(max(X_DEVANT + max(r for r, _ in TSINTSENET), PIED_MATE[0] + MATE_RAYON), ARGAZ[3] + 0.03)
SOCLE = (SX0 - MARGE, SX1 + MARGE, SY0 - MARGE, SY1 + MARGE)
Z_SOCLE = Z_CHAMBRE + H_SOCLE
box("Mehilot_HaAron_socle", *SOCLE, Z_CHAMBRE, Z_SOCLE, COL, MAT_ROC_TAILLE())


# Le roc reparaît sous chaque place, où il reste des traînées ; le bord est flou et mangé, et la poussière glissée du dessus des objets s'est amassée en bourrelet à leur pied.
def sur_le_socle(x, y):
    talus = lisse(0.0, 0.18, min(x - SOCLE[0], SOCLE[1] - x, y - SOCLE[2], SOCLE[3] - y))
    distance = min(place(x, y) for place in PLACES) + 0.03 * fbm(x * 5, y * 5, 3) + 0.01 * fbm(x * 21, y * 21, 5)
    dedans = 1 - lisse(-0.02, 0.035, distance)
    fond = AVAK * (0.8 + 0.6 * fbm(x * 2.5, y * 2.5, 1))
    bourrelet = AVAK * 1.1 * math.exp(-((distance - 0.035) / 0.03) ** 2) * (0.6 + 0.8 * fbm(x * 8, y * 8, 9))
    reste = AVAK * (0.35 * fbm(x * 11, y * 11, 13) - 0.1)
    return (0.002 + talus * (fond + bourrelet)) * (1 - dedans) + reste * dedans


# Au sol, elle a coulé contre les parois et le pied du socle ; le seuil de la galerie reste à nu.
def au_sol(x, y):
    passage = X_G4[0] < x < X_G4[1]
    murs = min(x - CHAMBRE[0], CHAMBRE[1] - x, y - CHAMBRE[2], math.inf if passage else CHAMBRE[3] - y)
    socle = math.hypot(max(SOCLE[0] - x, 0, x - SOCLE[1]), max(SOCLE[2] - y, 0, y - SOCLE[3]))
    congere = 0.07 * math.exp(-murs / 0.35) + 0.04 * math.exp(-socle / 0.25)
    seuil = lisse(0.0, 0.6, CHAMBRE[3] - y) if passage else 1.0
    return max(0.002, seuil * (AVAK * (0.7 + 0.6 * fbm(x * 1.7, y * 1.7, 17)) + congere * (0.7 + 0.6 * fbm(x * 3, y * 3, 19))))


nappe("Mehilot_HaAron_avak_socle", SOCLE, Z_SOCLE, 0.05, sur_le_socle, MAT_POUSSIERE())
nappe("Mehilot_HaAron_avak", CHAMBRE, Z_CHAMBRE, 0.15, au_sol, MAT_POUSSIERE())
