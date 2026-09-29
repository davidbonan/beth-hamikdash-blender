import math

import numpy as np
from mathutils import Vector

import beit_hamikdash_gestes as G

from .matieres import ARGENT, BOYAU, BRONZE, CHAIR, CHENE, ETOUPE, OR
from .maillage import TOUR, pave, tube
from .habillage import HAUT_Z


def tube_simple(chemin, rayon, n=8):
    return tube(chemin, [rayon] * len(chemin), n)


def kinor(mm, repere, echelle=1.0):
    e = echelle
    place = lambda pts: [repere @ p for p in pts]
    caisse = [Vector((0.0, 0.0, z * e)) for z in (-0.01, 0.0, 0.06, 0.12, 0.14)]
    largeurs = (0.11, 0.13, 0.14, 0.13, 0.11)
    anneaux = [[repere @ (c + Vector((w * e * math.cos(a), 0.022 * e * math.sin(a), 0.0)))
                for a in np.linspace(0, TOUR, 16, endpoint=False)] for c, w in zip(caisse, largeurs)]
    mm.nappe(anneaux, CHENE, "objet", pole_fin=repere @ caisse[-1])
    for s in (-1, 1):
        chemin = [Vector((s * (0.10 + 0.08 * math.sin(math.pi * 0.9 * t)) * e, 0.0, (0.11 + 0.42 * t) * e))
                  for t in np.linspace(0, 1, 7)]
        mm.nappe([place(a) for a in tube_simple(chemin, 0.015 * e)], CHENE, "objet")
    joug = [Vector((x * e, 0.0, 0.52 * e)) for x in (-0.15, 0.0, 0.15)]
    mm.nappe([place(a) for a in tube_simple(joug, 0.013 * e)], CHENE, "objet")
    for k in range(7):
        x = (-0.075 + 0.025 * k) * e
        corde = [Vector((x, 0.004, 0.13 * e)), Vector((x * 1.2, 0.004, 0.51 * e))]
        mm.nappe([place(a) for a in tube_simple(corde, 0.0028, 4)], BOYAU, "objet")


def tziltzal(mm, repere):
    profil = ((0.000, 0.014), (0.010, 0.035), (0.016, 0.100), (0.022, 0.115), (0.016, 0.112))
    anneaux = [[repere @ Vector((r * math.cos(a), -z, r * math.sin(a))) for a in np.linspace(0, TOUR, 20, endpoint=False)]
               for z, r in profil]
    mm.nappe(anneaux, BRONZE, "objet")


# Au fond pointu (Zeva'him 88a).
def mizrak(mm, repere):
    tourner_profil(mm, repere, ((0.000, 0.004), (0.02, 0.040), (0.05, 0.080), (0.075, 0.100), (0.082, 0.104), (0.078, 0.094)), OR)


def tourner_profil(mm, repere, profil, couleur, n=22, zone="objet"):
    anneaux = [[repere @ Vector((r * math.cos(a), r * math.sin(a), z)) for a in np.linspace(0, TOUR, n, endpoint=False)]
               for z, r in profil]
    mm.nappe(anneaux, couleur, zone)


# D'argent (Tamid 7:3 ; Bamidbar 10:2), embouchure à l'origine, pavillon au bout du z ; la longueur est un CHOIX.
def hatzotzra(mm, repere):
    profil = ((0.000, 0.004), (0.006, 0.013), (0.016, 0.006), (0.30, 0.006), (0.50, 0.008), (0.56, 0.018),
              (0.60, 0.040), (0.62, 0.062), (0.617, 0.064))
    tourner_profil(mm, repere, profil, ARGENT, 16)


# Une torche : manche de bois tenu à l'origine, tête d'étoupe au bout du z, que la visite allume.
def avouka(mm, repere):
    manche = [Vector((0.0, 0.0, z)) for z in np.linspace(-0.14, 0.32, 5)]
    mm.nappe([[repere @ p for p in a] for a in tube_simple(manche, 0.017)], CHENE, "objet",
             pole_fin=repere @ manche[-1])
    tete = ((0.30, 0.020), (0.32, 0.034), (0.40, 0.038), (0.45, 0.030))
    anneaux = [[repere @ Vector((r * math.cos(a), r * math.sin(a), z)) for a in np.linspace(0, TOUR, 12, endpoint=False)]
               for z, r in tete]
    mm.nappe(anneaux, ETOUPE, "objet", pole_fin=repere @ Vector((0.0, 0.0, 0.47)))


def bout_a_bout(mm, repere, chemin, rayons, couleur, n=10):
    chemin = [Vector((0.0, 0.0, -0.01)) + chemin[0]] + chemin
    rayons = [0.004] + list(rayons)
    mm.nappe([[repere @ p for p in a] for a in tube(chemin, rayons, n)], couleur, "objet", pole_fin=repere @ chemin[-1])


# Une bûche de la ma'arakha (Tamid 2:3), le long du z du repère.
RAYON_GIZRA = 0.045


def gizra(mm, repere, longueur=0.72, rayon=RAYON_GIZRA):
    chemin = [Vector((0.0, 0.0, z)) for z in np.linspace(-longueur / 2, longueur / 2, 6)]
    bout_a_bout(mm, repere, chemin, [rayon * (1.0 + 0.08 * math.sin(3.1 * k)) for k in range(6)], CHENE)


# Une patte avant du tamid (Tamid 4:3), l'épaule en haut du repère, le sabot en bas.
def ever(mm, repere):
    chemin = [Vector((0.0, y, z)) for z, y in ((0.0, 0.0), (0.12, 0.0), (0.24, -0.03), (0.34, -0.03), (0.46, -0.02))]
    bout_a_bout(mm, repere, chemin, (0.055, 0.050, 0.030, 0.024, 0.022), CHAIR, 12)


def tabouret(mm, centre, hauteur, cote=0.38):
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            pied_ = [centre + Vector((sx * cote * 0.42, sy * cote * 0.42, z)) for z in (0.0, hauteur - 0.03)]
            mm.nappe(tube_simple(pied_, 0.018, 6), CHENE, "objet")
    pave(mm, centre + HAUT_Z * (hauteur - 0.035), G.GAUCHE.copy(), G.LATERAL.copy(), (cote, cote), 0.035, CHENE, "objet")


KLAF = (0.86, 0.80, 0.64)


# La colonne ouverte entre ses deux rouleaux ; repère : z le long des rouleaux, x de l'un à l'autre, y vers le lecteur.
def sefer(mm, repere, ecart=0.28, hauteur=0.44):
    for s in (-1.0, 1.0):
        axe = [Vector((s * ecart / 2, 0.0, z)) for z in np.linspace(-hauteur / 2 - 0.07, hauteur / 2 + 0.07, 4)]
        mm.nappe([[repere @ p for p in a] for a in tube_simple(axe, 0.014, 8)], CHENE, "objet")
        roule = [Vector((s * ecart / 2, 0.0, z)) for z in np.linspace(-hauteur / 2, hauteur / 2, 4)]
        mm.nappe([[repere @ p for p in a] for a in tube_simple(roule, 0.04, 12)], KLAF, "objet")
    xs = np.linspace(-ecart / 2 + 0.04, ecart / 2 - 0.04, 9)
    feuille = [[repere @ Vector((x, 0.012 * (1.0 - (2.0 * x / ecart) ** 2), z)) for x in xs]
               for z in np.linspace(-hauteur / 2, hauteur / 2, 5)]
    mm.nappe(feuille, KLAF, "objet", ferme=False)
    mm.nappe([rang[::-1] for rang in feuille], KLAF, "objet", ferme=False)


# « צְלוֹחִית שֶׁל זָהָב מַחֲזֶקֶת שְׁלשֶׁת לֻגִּים » (Soucca 4:9) : panse, col étroit, lèvre ; la forme est un CHOIX. Base à l'origine,
# la bouche au bout du z.
PROFIL_DE_LA_TZELOHIT = ((0.000, 0.002), (0.005, 0.050), (0.030, 0.070), (0.090, 0.072), (0.140, 0.050), (0.170, 0.022),
                         (0.210, 0.018), (0.220, 0.024), (0.225, 0.020))
PANSE_DE_LA_TZELOHIT = 0.07


def tzelohit(mm, repere):
    tourner_profil(mm, repere, PROFIL_DE_LA_TZELOHIT, OR)
