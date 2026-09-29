from beit_hamikdash_visite import Z_AZ, Z_BAT

from ..corps import Gabarit, _alea
from ..ustensiles import ever, gizra, mizrak
from ..mise_en_scene import (BATTEMENT, MESURES, Stade, chanter, charger, ecouter, garder, hatava, lavage,
                             priere, repere_ever, repere_gizra, repere_mizrak, saler, tenir, zerika)
from ..bigdei_kehouna import cohen
from ..tenues import fidele, levi
from ..role import LEVIIM_INSTRUMENTS, Role, _levi


# À terre, dans l'Ezrat Israël au pied du Doukhan : la tête à hauteur des pieds des Léviim (Arakhin 2:6, R. Eliézer ben Yaakov).
def _tzoar(k, y):
    nom = f"tzoarei_haleviim_{k + 1}"
    gabarit = Gabarit(1.18 + 0.10 * _alea(nom, 1), age=0.12 + 0.05 * _alea(nom, 0), peau="young_caucasian_male")
    retard = 0.06 * (_alea(nom, 2) - 0.5)
    return Role(nom, "tzoarei_haleviim", lambda: levi(nom, gabarit, barbe=False),
                lambda h, a, horloge, t: chanter(h, a, horloge, t, retard),
                (-10.4, y, Z_AZ), 180.0 + 8.0 * (_alea(nom, 3) - 0.5), duree=MESURES * BATTEMENT)


def _cohen(nom, geste, ou, cap, gabarit, tenu=None, gris=False, duree=16.0):
    def batir():
        h = cohen(nom, gabarit, gris=gris)
        if tenu:
            objet, construire, repere = tenu
            tenir(h, objet, construire, "spine_03", repere(h))
        return h
    return Role(nom, nom, batir, geste, ou, cap, duree=duree, famille="cohanim")


# Un des cinq postes des Léviim aux portes de l'Azara (Middot 1:1), hors de la porte, sur le palier des quinze marches.
def _shomer_levi():
    return Role("shomer_levi", "shomer_levi", lambda: levi("shomer_levi", Gabarit(1.79, age=0.45)), garder,
                (9.0, 5.5, Z_AZ), 0.0, duree=24.0)


# Chaque figure fait un geste du tamid du matin, à l'endroit que la Mishna lui donne ; son nom est son concept.
def roles_du_tamid():
    return [
        # Au Kiyor (Middot 3:6) : main droite sur le pied droit, main gauche sur le pied gauche, penché.
        _cohen("kiddoush_yadayim", lavage, (-59.0, -17.4, Z_AZ), 90.0, Gabarit(1.74, age=0.55), duree=12.0),
        # Le kevesh au sud de l'autel (Middot 3:3) : on monte par la droite, on descend par la gauche (Zeva'him 6:3).
        Role("aliyat_hakevesh", "aliyat_hakevesh", lambda: cohen("aliyat_hakevesh", Gabarit(1.77, age=0.62)),
             trajet=Stade((-38.0, -52.0), (-38.0, -28.0), 2.0, sens=-1), vitesse=1.0, sol_haut=9.0, famille="cohanim"),
        # Le sang du tamid au coin nord-est (Tamid 4:1).
        _cohen("zerika", zerika, (-20.5, 4.6, Z_AZ), 142.0, Gabarit(1.72, age=0.82, peau="old_caucasian_male"),
               tenu=("mizrak", mizrak, repere_mizrak), gris=True),
        # Les membres salés sur la moitié basse du kevesh, à l'ouest, où le sel est posé (Tamid 4:3).
        _cohen("melihat_haevarim", saler, (-41.5, -46.5, 3.0), 180.0, Gabarit(1.73, age=0.50),
               tenu=("ever", ever, repere_ever), duree=6.0),
        # Le bois monté sur l'autel pour la ma'arakha, dressée à l'est (Tamid 2:3-4).
        _cohen("siddour_hamaarakha", charger, (-26.0, -9.0, 9.0), 180.0, Gabarit(1.76, age=0.42),
               tenu=("gizra", gizra, repere_gizra), duree=8.0),
        # Sur la marche haute de la pierre de la Menora (Tamid 3:9).
        _cohen("hatavat_hanerot", hatava, (-123.6, -7.5, Z_BAT + 0.9), 180.0, Gabarit(1.70, age=0.58), duree=10.0),
    ] + [_levi(k, genre) for k, genre in enumerate(LEVIIM_INSTRUMENTS)] + [
        _tzoar(0, 3.2), _tzoar(1, -3.2),
        # Les anshei ma'amad, debout sur leur korban dans l'Ezrat Israël (Ta'anit 4:2 ; Middot 5:1).
        Role("anshei_maamad_1", "anshei_maamad",
             lambda: fidele("anshei_maamad_1", "costume", Gabarit(1.76, age=0.68), tete="talith"), priere,
             (-5.0, -26.0, Z_AZ), 180.0),
        Role("anshei_maamad_2", "anshei_maamad",
             lambda: fidele("anshei_maamad_2", "costume", Gabarit(1.69, age=0.85, peau="old_caucasian_male"), gris=True),
             ecouter, (-5.5, 24.0, Z_AZ), 186.0),
    ]


VUES = [
    # Face au Kiyor, entre la Mer de bronze et l'autel : de plus loin, l'un ou l'autre le cache.
    dict(id="vue_kiddoush_yadayim", position=(-54.8, -29.2, Z_AZ), cap=105, tangage=-4),
    # Les Léviim font face au Sanctuaire ; neuf amot entre l'autel et le Doukhan ne cadrent pas les douze de face.
    dict(id="vue_leviim", position=(-20.5, -30.0, Z_AZ), cadre=["leviim"]),
    # De dos, l'autel devant lui : depuis le seuil de Nikanor, dans l'Ezrat Israël.
    dict(id="vue_anshei_maamad", position=(-1.5, -26.5, Z_AZ - 2.5), cap=180),
]
