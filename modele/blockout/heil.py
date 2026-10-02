from .primitives.parametres import Z_AZ, Z_EZN, Z_HAR
from .primitives.matieres import MAT_CHENE
from .primitives.volumes import box, plage
from .primitives.ouvrages import escalier, massif_evide
from .ezrat_nashim import EX1
from .azara import AX0, AY0, AY1, PORTE_BEKHOROT, PORTE_DELEK, PORTE_KORBAN, POURTOUR_Y1, T
from .lishkot import PUITS_MESIBA


# Soreg (10 tefa'him = 1.67 ama) et 'Heil. Middot 2:3 : « לִפְנִים מִמֶּנּוּ הַחֵיל, עֶשֶׂר
# אַמּוֹת » — dix amot de dégagement, et les douze marches y sont. Le soreg se pose donc
# à 10 amot de la face bâtie la plus saillante, corps de porte compris : mesuré depuis
# le mur, il traversait le Beit HaMoked et le Beit Avtinas — d'où POURTOUR_Y1, le même
# au nord et au sud. Ses treize פרצות ont été rebouchées (« חָזְרוּ וּגְדָרוּם »), il est
# donc continu.
HEIL = 10
SX0, SX1 = AX0 - T - HEIL, EX1 + 5 + HEIL
SY0, SY1 = -(POURTOUR_Y1 + HEIL), POURTOUR_Y1 + HEIL
# Un treillis de bois (Middot 2:3 ; fiche §2 : « séparation légère, pas un mur ») :
# poteaux au pas de 3 amot et deux lisses. La lame pleine d'avant se lisait en muret.
SOREG_H = 1.67
for nm, xa, xb, ya, yb in (("sud", SX0, SX1, SY0, SY0 + 0.2),
                           ("nord", SX0, SX1, SY1 - 0.2, SY1),
                           ("ouest", SX0, SX0 + 0.2, SY0 + 0.2, SY1 - 0.2),
                           ("est", SX1 - 0.2, SX1, SY0 + 0.2, SY1 - 0.2)):
    for k, (zb, zh) in enumerate(((Z_HAR + 0.55, Z_HAR + 0.68), (Z_HAR + SOREG_H - 0.13, Z_HAR + SOREG_H))):
        box(f"Soreg_{nm}_lisse_{k}", xa, xb, ya, yb, zb, zh, "00_HarHabayit", MAT_CHENE())
    long_x = (xb - xa) >= (yb - ya)
    a0, a1 = (xa, xb) if long_x else (ya + 1.5, yb - 1.5)   # les poteaux d'angle sont ceux des grands côtés
    for k, c in enumerate(plage(a0, a1, 3)):
        if long_x:
            box(f"Soreg_{nm}_poteau_{k:03d}", c - 0.15, c + 0.15, ya - 0.05, yb + 0.05,
                Z_HAR, Z_HAR + SOREG_H + 0.15, "00_HarHabayit", MAT_CHENE())
        else:
            box(f"Soreg_{nm}_poteau_{k:03d}", xa - 0.05, xb + 0.05, c - 0.15, c + 0.15,
                Z_HAR, Z_HAR + SOREG_H + 0.15, "00_HarHabayit", MAT_CHENE())
# 'Heil : 12 marches de 0.5 × 0.5 (Middot 2:3) sur ses quatre côtés. À l'est, l'accès
# principal, elles montent contre la face est du mur de l'Ezrat Nashim (x 145). Au nord et
# au sud, la terrasse du 'Heil : le sol y est celui de l'Ezrat Nashim (Z_EZN), et ses
# douze marches descendent vers le soreg en laissant quatre amot de plat devant lui. À l'ouest, dix amot de 'Heil ne laissent pas de
# terrasse : les marches montent jusqu'au pied du podium. Les corps de porte et lishkot
# du pourtour sont posés sur cette terrasse, leur porte sur le 'Heil s'ouvre dessus.
HEIL_MARCHES = 12
for cote, ya, yb, vides in (("nord", AY1 + T, POURTOUR_Y1, [(*PUITS_MESIBA, Z_HAR, Z_AZ)]),
                            ("sud", -POURTOUR_Y1, AY0 - T, [])):
    massif_evide(f"Heil_terrasse_{cote}", AX0 - T, EX1 + 5, ya, yb, Z_HAR, Z_EZN, vides, "00_HarHabayit")
# Chaque marche est un cadre autour du plateau (podium et terrasses) : la volée tourne les
# angles sans rupture. Les longs côtés portent les angles, l'est et l'ouest s'arrêtent contre eux.
for i in range(HEIL_MARCHES):
    z = Z_HAR + 0.5 * (i + 1)
    haut, pied = 0.5 * (HEIL_MARCHES - 1 - i), 0.5 * (HEIL_MARCHES - i)
    x0, x1, y1 = AX0 - T - pied, EX1 + 5 + pied, POURTOUR_Y1 + haut
    box(f"Heil_marche_nord_{i:02d}", x0, x1, POURTOUR_Y1 + haut, POURTOUR_Y1 + pied, Z_HAR, z, "00_HarHabayit")
    box(f"Heil_marche_sud_{i:02d}", x0, x1, -POURTOUR_Y1 - pied, -POURTOUR_Y1 - haut, Z_HAR, z, "00_HarHabayit")
    box(f"Heil_marche_ouest_{i:02d}", x0, AX0 - T - haut, -y1, y1, Z_HAR, z, "00_HarHabayit")
    box(f"Heil_marche_est_{i:02d}", EX1 + 5 + haut, x1, -y1, y1, Z_HAR, z, "00_HarHabayit")
# De la terrasse aux portes latérales : dix amot, vingt marches de « רוּם מַעֲלָה חֲצִי אַמָּה
# וְשִׁלְחָהּ חֲצִי אַמָּה » (Middot 2:3), sur la largeur de la baie. Devant les trois portes
# sans corps de porte ; Nitzotz et Mayim montent dans le leur, et le Beit HaMoked a les
# siens devant sa porte du 'Heil.
for nm, x, cote in (("Korban", PORTE_KORBAN, "nord"), ("Bekhorot", PORTE_BEKHOROT, "sud"), ("Delek", PORTE_DELEK, "sud")):
    if cote == "nord":
        escalier(f"Escalier_{nm}", x - 5, x + 5, AY1 + T, AY1 + T + 10, Z_EZN, Z_AZ, "+y", "20_Azara")
    else:
        escalier(f"Escalier_{nm}", x - 5, x + 5, AY0 - T - 10, AY0 - T, Z_EZN, Z_AZ, "-y", "20_Azara")
