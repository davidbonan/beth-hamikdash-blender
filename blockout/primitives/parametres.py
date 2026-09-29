import pathlib


# ----------------------------------------------------------------------------
# PARAMÈTRES
# ----------------------------------------------------------------------------
AMA = 0.48            # mètres par ama  (alternatives : 0.525 Ritmeyer, 0.576 Hazon Ish)
TEFAH = 1 / 6
FPS = 24
MENORA_DROITE = True  # CHOIX : True = branches droites en diagonale (Rambam/Rashi), False = courbes
GEVIIM_RENVERSES = True  # CHOIX : True = coupes bouche en bas (dessin du Rambam), False = « מלמטה צר » (son commentaire)
PORTES_HEIKHAL_OUVERTES = True  # battants rabattus dans l'embrasure, comme pendant l'avoda
# Foule de Yom Kippour : False = architecture seule. Retire toute la collection
# 76_Foule — peuple de l'Ezrat Israël, cohanim de l'Ezrat Kohanim, Léviim et leurs
# instruments sur le Doukhan, masses de l'Ezrat Nashim, du Har HaBayit et du portique.
FOULE = False
# Les mâts d'or de Simhat Beit HaShoeva (Soucca 5:2) : dressés dans l'Ezrat Nashim le
# jour de Kippour aussi (CHOIX — la Mishna les dit « là », sans dire qu'on les démonte).
CANDELABRES_SHOEVA = True
NETTOYER_SCENE = True

# Niveaux (en amot)
Z_HAR = -16.0   # Har HaBayit : 12 marches du 'Heil (6) + 15 marches (7,5) + Ezrat Israël (2,5) sous l'Azara
Z_ROCHE = -240  # pied des murs de soutènement de l'esplanade, sous le fond du Kidron
Z_EZN = -10.0   # Ezrat Nashim : 15 marches sous l'Ezrat Israël (Middot 2:5), elle-même 2,5 sous l'Ezrat Kohanim (2:6)
Z_EZI = -2.5    # Ezrat Israël : « מַעֲלָה גְבוֹהָה אַמָּה וְהַדּוּכָן נָתוּן עָלֶיהָ וּבוֹ שָׁלֹשׁ מַעֲלוֹת » (Middot 2:6)
Z_AZ = 0.0      # Azara
Z_BAT = 6.0     # sol de l'Oulam / Heikhal (12 marches de 0.5)

RACINE = pathlib.Path(__file__).resolve().parents[2]


def m(v):
    return v * AMA
