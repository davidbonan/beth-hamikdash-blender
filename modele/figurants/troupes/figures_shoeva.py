import math

from beit_hamikdash_visite import Z_EZI, Z_EZN

from ..corps import Gabarit, _alea
from ..maillage import TOUR
from ..ustensiles import avouka, hatzotzra
from ..mise_en_scene import TEKIA, Accessoire, bouche, dans_la_poigne, tekia, trompette_tenue
from ..bigdei_kehouna import cohen
from ..tenues import fidele
from ..danse import JET, RAYON_MANCHE, Hora, jongler, torche_jonglee
from ..role import Role, _musicien


CENTRE_DES_MAALOT = 5.0     # amot : EX0 du blockout, d'où les quinze demi-cercles sont tracés
# Soucca 5:4 : « בְּכִנּוֹרוֹת וּבִנְבָלִים וּבִמְצִלְתַּיִם … בְּלֹא מִסְפָּר ». Un par marche, et ce partage : CHOIX.
MAALOT_INSTRUMENTS = ("kinor", "nevel", "kinor", "tziltzal", "kinor", "kinor", "nevel", "kinor", "kinor", "tziltzal",
                      "nevel", "kinor", "kinor", "nevel", "kinor")


# Tournés vers l'Ezrat Nashim, sur le giron de la marche `i` (Middot 2:5 : une demi-ama), les pieds tenant dessus.
# Un côté puis l'autre, à 20° au moins de l'axe : les deux cohanim descendent au milieu en sonnant (Soucca 5:4).
def _levi_des_maalot(i):
    rayon = 13.1 - 0.5 * i
    cote, n = (1.0, 8) if i % 2 == 0 else (-1.0, 7)
    angle = math.radians(cote * (20.0 + 50.0 * ((i // 2 * 3) % n) / (n - 1)))
    ou = (CENTRE_DES_MAALOT + rayon * math.cos(angle), rayon * math.sin(angle), Z_EZN + 0.5 * (i + 1))
    return _musicien(f"leviim_hamaalot_{i + 1}", "leviim_hamaalot", MAALOT_INSTRUMENTS[i], ou, math.degrees(angle))


# Chacun ouvert de 35° vers son côté de la porte : de face, la trompette se cachait derrière les poings.
def _toke(k, y):
    nom = f"tokei_hatzotzrot_{k + 1}"

    def batir():
        h = cohen(nom, Gabarit(1.72 + 0.06 * _alea(nom, 1), age=0.45 + 0.3 * _alea(nom, 0)))
        h.bouche = bouche(h)
        return h
    return Role(nom, "tokei_hatzotzrot", batir, tekia, (3.0, y, Z_EZI), math.copysign(35.0, y), duree=TEKIA,
                accessoires=(Accessoire("hatzotzra", hatzotzra, trompette_tenue),))


RONDE = (78.0, 14.0)        # amot : CHOIX, hors des allées du parcours, entre les mâts de l'est et l'axe
DANSEURS = 8


def _hassid(k):
    nom = f"hassidim_veanshei_maase_{k + 1}"
    age = 0.35 + 0.55 * _alea(nom, 0)
    gabarit = Gabarit(1.66 + 0.16 * _alea(nom, 1), age=age, poids=0.4 + 0.3 * _alea(nom, 2),
                      peau="old_caucasian_male" if age > 0.8 else "middleage_caucasian_male")
    tete = "chapeau" if k % 3 == 0 else "kippa"
    torche = "l" if k in (2, 5) else "r"
    return Role(nom, "hassidim_veanshei_maase", lambda: fidele(nom, "costume", gabarit, gris=age > 0.7, tete=tete),
                trajet=Hora(RONDE, 5.0, TOUR * k / DANSEURS, torche, "ouverte" if k % 2 == 0 else "poing"),
                sol_haut=Z_EZN, accessoires=(Accessoire("avouka", avouka, dans_la_poigne(torche, RAYON_MANCHE)),))


# La nuit de Sim'hat Beit HaSho'éva (Soucca 5:4, 53a) : ce que la visite montre quand le parcours tombe la nuit.
def roles_shoeva():
    return [_levi_des_maalot(i) for i in range(15)] + [_toke(0, 2.4), _toke(1, -2.4)] + [
        _hassid(k) for k in range(DANSEURS)] + [
        Role("shemone_avoukot", "shemone_avoukot",
             lambda: fidele("shemone_avoukot", "costume", Gabarit(1.73, age=0.55), tete="kippa"),
             jongler, (*RONDE, Z_EZN), 0.0, duree=64 * JET, accessoires=tuple(torche_jonglee(j) for j in range(8))),
    ]
