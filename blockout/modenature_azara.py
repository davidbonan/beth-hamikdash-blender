from .primitives.parametres import Z_AZ, Z_EZI, Z_EZN
from .primitives.ouvrages import (BANDEAU, CORNICHE, ENCADREMENT_SHAAR, LISHKA_DEBORD, SAILLIE_BANDEAU, SOCLE,
                                  moulure, ordre_de_pilastres)
from .azara import (AX0, AX1, AY0, AY1, CADRE_LISHKA_EZI, GAZIT_X0, GAZIT_X1, GOLA_X0, GOLA_X1, H_MUR,
                    LISHKOT_EZI, OUVERTURES, PISHPESHIM, PORTE_MOKED, SOUS_CORNICHE, T, X_DOUKHAN)
from .lishkot import LISHKOT_NIKANOR, MEDICHIN_X, MELACH_X, NZ_X0, NZ_X1, PARVA_X, SM_X0, SM_X1


# Couronnement des murs de l'Azara : une assise en débord sur la crête, qui saute
# les corps passant les 25 amot (Beit HaMoked, HaGazit, HaGola, et les terrasses
# de Sha'ar HaNitzotz et de Sha'ar HaMayim).
moulure("Azara_couronnement_est", AX1, AX1 + T, AY0 - T, AY1 + T, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("deborde", "deborde"))
moulure("Azara_couronnement_ouest", AX0 - T, AX0, AY0, AY1, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("bute", "bute"))
CORPS_NORD = [(PORTE_MOKED - 10.5, PORTE_MOKED + 10.5),
              (GAZIT_X0 - LISHKA_DEBORD, GAZIT_X1 + LISHKA_DEBORD),
              (GOLA_X0 - LISHKA_DEBORD, GOLA_X1 + LISHKA_DEBORD),
              (NZ_X0 - LISHKA_DEBORD, NZ_X1 + LISHKA_DEBORD)]
CORPS_SUD = [(SM_X0 - LISHKA_DEBORD, SM_X1 + LISHKA_DEBORD)]
moulure("Azara_couronnement_nord", AX0 - T, AX1, AY1, AY1 + T, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("deborde", "bute"), reserve=CORPS_NORD)
moulure("Azara_couronnement_sud", AX0 - T, AX1, AY0 - T, AY0, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("deborde", "bute"), reserve=CORPS_SUD)
# Le socle ne se pose que du côté de la cour : dehors, ces murs soutiennent dix amot de
# remblai et leur pied est sur la terrasse du 'Heil, pas sur le dallage de l'Azara. Il
# saute les baies — une porte n'a pas de pied de mur en travers — et les corps bâtis.
LISHKOT_NIKANOR_EMPRISES = [(y0 - LISHKA_DEBORD, y1 + LISHKA_DEBORD) for y0, y1 in LISHKOT_NIKANOR.values()]
moulure("Azara_socle_est", AX1, AX1 + T, AY0 - T, AY1 + T, Z_AZ, SOCLE, "20_Azara",
        mitres=("deborde", "deborde"), cotes=(True, False), reserve=[(-5, 5)] + LISHKOT_NIKANOR_EMPRISES)
moulure("Azara_socle_ouest", AX0 - T, AX0, AY0, AY1, Z_AZ, SOCLE, "20_Azara",
        mitres=("bute", "bute"), cotes=(False, True))
LISHKOT_COUR_SUD = [(x0 - LISHKA_DEBORD, x1 + LISHKA_DEBORD) for x0, x1 in (MELACH_X, PARVA_X, MEDICHIN_X)]
for _nm, _y0, _y1, _cotes, _corps in (("nord", AY1, AY1 + T, (True, False), CORPS_NORD),
                                      ("sud", AY0 - T, AY0, (False, True), CORPS_SUD + LISHKOT_COUR_SUD)):
    moulure(f"Azara_socle_{_nm}", AX0 - T, AX1, _y0, _y1, Z_AZ, SOCLE, "20_Azara",
            mitres=("deborde", "bute"), cotes=_cotes,
            reserve=_corps + [(p - 5, p + 5) for p in OUVERTURES[_nm]])
# Face est, celle que l'Ezrat Nashim regarde : ce mur-là descend jusqu'à la terrasse du
# 'Heil, et c'est là que son pied se pose. Trente-cinq amot de parement d'un seul tenant
# se lisent en gros œuvre ; le bandeau y porte, comme dans l'Ezrat Nashim, le niveau du
# dallage de l'Azara qui est derrière.
moulure("Azara_socle_est_bas", AX1, AX1 + T, AY0 - T, AY1 + T, Z_EZN, SOCLE, "20_Azara",
        mitres=("deborde", "deborde"), cotes=(False, True),
        reserve=[(-5, 5)] + [(p - 2 - CADRE_LISHKA_EZI, p + 2 + CADRE_LISHKA_EZI) for _, _, _, p in LISHKOT_EZI])
moulure("Azara_bandeau_est", AX1, AX1 + T, AY0 - T, AY1 + T, Z_AZ, BANDEAU, "20_Azara",
        saillie=SAILLIE_BANDEAU, mitres=("deborde", "deborde"), cotes=(False, True),
        reserve=[(-5, 5)])
# Pilastres côté cour, dans le parti de l'Ezrat Nashim : CHOIX (Rambam, Beit HaBe'hira 1:11).
# Ils sautent les portes avec leur cadre et les corps bâtis ; l'Ezrat Israël, deux amot et
# demie plus bas, a les siens sur le mur est.
PORTES_EN_CADRE = {nm: [(p - 5 - ENCADREMENT_SHAAR, p + 5 + ENCADREMENT_SHAAR) for p in OUVERTURES[nm]]
                   for nm in OUVERTURES}
for nm, paroi, corps in (("nord", ("x", AY1, -1), CORPS_NORD),
                         ("sud", ("x", AY0, 1), CORPS_SUD + LISHKOT_COUR_SUD)):
    ordre_de_pilastres(f"Azara_pilastre_{nm}", paroi, (AX0, X_DOUKHAN), (Z_AZ, SOUS_CORNICHE),
                       "20_Azara", reserve=corps + PORTES_EN_CADRE[nm])
ordre_de_pilastres("Azara_pilastre_ouest", ("y", AX0, 1), (AY0, AY1), (Z_AZ, SOUS_CORNICHE), "20_Azara")
NIKANOR_CADRE = (-5 - ENCADREMENT_SHAAR, 5 + ENCADREMENT_SHAAR)
ordre_de_pilastres("Azara_pilastre_est", ("y", AX1, -1), (AY0, AY1), (Z_EZI, SOUS_CORNICHE),
                   "20_Azara", reserve=[NIKANOR_CADRE] + [(y0 - 0.3, y1 + 0.3) for _, y0, y1 in PISHPESHIM])
