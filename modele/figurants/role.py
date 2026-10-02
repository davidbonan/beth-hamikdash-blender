from typing import NamedTuple

from beit_hamikdash_visite import Z_AZ

from .corps import Gabarit, _alea
from .ustensiles import hatzotzra, kinor, tziltzal
from .mise_en_scene import (BATTEMENT, MESURES, TEKIA, Accessoire, Stade, bouche, frapper, jouer_kinor,
                            repere_cymbale, repere_kinor, tekia, tenir, trompette_tenue)
from .bigdei_kehouna import cohen
from .tenues import fidele, levi


class Role(NamedTuple):
    nom: str
    concept: str
    batir: object
    geste: object = None
    ou: tuple = None
    cap: float = 0.0
    duree: float = 16.0
    trajet: Stade = None
    foulee: float = 1.35
    vitesse: float = 1.15
    sol_haut: float = Z_AZ
    famille: str = None
    accessoires: tuple = ()
    # Debout sur ce qu'elle porte elle-même (une bima, ses marches) : `ou` donne son sol, qu'aucun rayon ne trouverait.
    sol_porte: bool = False


LEVIIM_Y = (-23.5, -20.0, -16.5, -13.0, -9.5, -6.0, 6.0, 9.5, 13.0, 16.5, 20.0, 23.5)
# Neuf kinorot, deux nevalim, un tziltzal : les douze qu'on ne descend jamais au-dessous (Arakhin 2:3-6).
LEVIIM_INSTRUMENTS = ("kinor",) * 4 + ("nevel", "kinor", "tziltzal", "nevel") + ("kinor",) * 4


def _levi(k, genre):
    nom = f"leviim_{k + 1}"
    cap = 180.0 + 10.0 * (_alea(nom, 3) - 0.5)
    return _musicien(nom, "leviim", genre, (-13.15, LEVIIM_Y[k], Z_AZ), cap, famille="leviim")


def _musicien(nom, concept, genre, ou, cap, famille=None):
    age = 0.42 + 0.45 * _alea(nom, 0)
    gabarit = Gabarit(1.66 + 0.14 * _alea(nom, 1), age=age, peau="old_caucasian_male" if age > 0.78 else
                      "middleage_caucasian_male")
    retard = 0.06 * (_alea(nom, 2) - 0.5)

    echelle = 1.35 if genre == "nevel" else 1.0

    def batir():
        h = levi(nom, gabarit, gris=age > 0.72)
        if genre == "tziltzal":
            for cote in ("l", "r"):
                tenir(h, f"tziltzal_{cote}", tziltzal, f"hand_{cote}", repere_cymbale(h, cote))
        else:
            tenir(h, genre, lambda mm, r: kinor(mm, r, echelle), "spine_03", repere_kinor(h, echelle))
        return h

    if genre == "tziltzal":
        geste = lambda h, a, horloge, t: frapper(h, a, horloge, t, retard)
    else:
        geste = lambda h, a, horloge, t: jouer_kinor(h, a, horloge, t, echelle, retard)
    return Role(nom, concept, batir, geste, ou, cap, duree=MESURES * BATTEMENT, famille=famille)


def _israelite(nom, geste, ou, cap, concept, tete=None, apres=None):
    age = 0.30 + 0.60 * _alea(nom, 0)
    gabarit = Gabarit(1.64 + 0.18 * _alea(nom, 1), age=age, poids=0.35 + 0.35 * _alea(nom, 2),
                      peau="old_caucasian_male" if age > 0.8 else "middleage_caucasian_male")
    tete = tete or ("talith" if _alea(nom, 3) < 0.25 else "chapeau" if _alea(nom, 3) > 0.8 else "kippa")

    def batir():
        h = fidele(nom, "costume", gabarit, gris=age > 0.7, tete=tete)
        return apres(h) if apres else h
    return Role(nom, concept, batir, geste, ou, cap)


def _un_cohen(nom, ages=(0.35, 0.45)):
    age = ages[0] + ages[1] * _alea(nom, 0)
    return cohen(nom, Gabarit(1.66 + 0.14 * _alea(nom, 1), age=age), gris=age > 0.72)


def _tokea(nom, concept, ou, cap):
    def batir():
        h = cohen(nom, Gabarit(1.72 + 0.06 * _alea(nom, 1), age=0.45 + 0.3 * _alea(nom, 0)))
        h.bouche = bouche(h)
        return h
    return Role(nom, concept, batir, tekia, ou, cap, duree=TEKIA, famille="cohanim",
                accessoires=(Accessoire("hatzotzra", hatzotzra, trompette_tenue),))
