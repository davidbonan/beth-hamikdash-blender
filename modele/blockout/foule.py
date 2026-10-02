from .primitives.parametres import FOULE, Z_AZ, Z_EZN, Z_HAR
from .primitives.matieres import MAT_BRONZE, MAT_CHENE, MAT_LIN, etoffe
from .primitives.volumes import _poser, alea, box, cone, cyl, cyl_between, plage, sphere


# ----------------------------------------------------------------------------
# 75 — FIGURES
#   De quoi bâtir un corps debout : la silhouette et ce qui distingue sa tenue.
#   Volumes grossiers, qui ne visent pas la ressemblance — ils donnent aux passes
#   Depth/Normal une structure stable, sans laquelle l'i2i réinvente les gens à
#   chaque image et le plan perd sa cohérence temporelle.
#
#   La seule mise en scène que le blockout porte est la foule de la section 76 :
#   l'état permanent du jour. Une figure de premier plan — un cohen au travail, une
#   bête, un ustensile tenu — se pose dans une collection à soi, en appelant ces
#   helpers depuis un script à part, pour que l'export puisse la masquer sans vider
#   la cour.
# ----------------------------------------------------------------------------
H_HOMME = 3.65        # 1.75 m en amot


# Tenues (fiche §12) : le peuple en habits
# d'aujourd'hui, talith sur la tête ou non ; les Léviim en robe de lin unie ; les
# cohanim dans les quatre vêtements blancs, coiffe plate (Yoma 7:5). Trois corps
# différents, et pas trois teintes : à vingt amot le styliseur ne lit qu'une silhouette.
AM, TALITH, LEVI, KOHEN = "am", "talith", "levi", "kohen"
TENUES_AM = (TALITH, TALITH, TALITH, AM, AM)

def _etoffe(tenue, nom):
    if tenue in (LEVI, KOHEN):
        return MAT_LIN()
    return MAT_FOULE() if alea(nom, 6) < 0.6 else MAT_TALITH()

def _pieces_de_tenue(name, tenue, h, col):
    """Ce qui distingue la tenue au-dessus des épaules et à la taille."""
    if tenue == TALITH:
        # Capuche du talith gadol : des épaules jusqu'au-dessus de la tête, qu'elle
        # enveloppe — la tête ronde nue est le signe de la kippa, pas du talith.
        return [cone(f"{name}_talith", 0, 0, 0.74 * h, 1.03 * h, 0.54 * h / H_HOMME,
                     0.06 * h, col, MAT_TALITH(), verts=10)]
    if tenue == KOHEN:
        k = h / H_HOMME
        return [cyl(f"{name}_coiffe", 0, 0, 0.985 * h, 1.02 * h, 0.09 * h, col, MAT_LIN(), verts=10),
                box(f"{name}_avnet", -0.30 * k, 0.30 * k, -0.38 * k, 0.38 * k,
                    0.61 * h, 0.655 * h, col, MAT_LIN())]
    return []

def silhouette(name, x, y, z0, col, tenue=KOHEN, h=H_HOMME, lacet=0.0):
    """Figure debout : robe, torse, épaules, bras, cou, tête, plus sa tenue.

    Le fût à tête ronde d'avant était un volume de tour : le profil d'une colonne
    miniature, le plus large en bas, la boule posée à même le sommet. Le styliseur le
    repeignait donc en borne de pierre et ajoutait les fidèles du prompt derrière
    (CAM_02). Ce qu'un volume tourné ne peut pas donner, c'est l'anisotropie d'un
    corps : épaules larges de face, minces de profil, et deux bras détachés du tronc.
    Les pièces sont bâties à l'origine, face à l'ouest, puis posées : `lacet` tourne la
    figure autour de sa verticale (radians), et c'est ce qui défait le garde-à-vous
    d'une foule. Cotes proportionnelles à `h` pour que les ketanim restent des enfants.
    """
    corps = _etoffe(tenue, name)
    k = h / H_HOMME
    ep, prof = 0.50 * k, 0.26 * k
    # Le me'il tombe droit « comme tous les manteaux » et n'a pas de manches (Rambam
    # Klei HaMikdash 9:3) : bras en lin de la kutonet, bas serré pour que l'éphod le frôle.
    evasement = 0.44 * k
    pieces = [
        cone(f"{name}_robe", 0, 0, 0, 0.52 * h, evasement, 0.32 * k, col, corps, verts=12),
        box(f"{name}_torse", -prof, prof, -0.34 * k, 0.34 * k, 0.50 * h, 0.83 * h, col, corps),
        box(f"{name}_epaules", -prof, prof, -ep, ep, 0.76 * h, 0.83 * h, col, corps),
        cyl(f"{name}_cou", 0, 0, 0.80 * h, 0.88 * h, 0.13 * k, col, corps, verts=8),
        sphere(f"{name}_tete", 0, 0, 0.925 * h, 0.080 * h, col, corps, segs=8),
    ]
    for s in (-1, 1):
        pieces.append(cyl(f"{name}_bras{s:+d}", 0, s * (ep - 0.11 * k), 0.50 * h,
                          0.79 * h, 0.11 * k, col, corps, verts=8))
    pieces += _pieces_de_tenue(name, tenue, h, col)
    _poser(pieces, x, y, z0, lacet)

def instrument_de_levi(nom, genre, x, y, z0, col):
    """Kinor, nevel ou tziltzal tenu devant le torse, vers le Sanctuaire (ouest).

    C'est l'instrument qui dit « Lévi » : la robe de lin est celle des cohanim, et
    l'estrade ne se voit pas de partout. Kinor et nevel sont des cadres — caisse,
    deux bras, joug — et non des planches, qui se lisaient en livres ; le tziltzal
    une paire de disques de bronze.
    """
    bois, devant = MAT_CHENE(), x - 0.30
    if genre == "tziltzal":
        for s in (-1, 1):
            cyl_between(f"{nom}_tziltzal{s:+d}", (devant - 0.12, y + s * 0.32, z0 + 2.2),
                        (devant, y + s * 0.32, z0 + 2.2), 0.28, col, MAT_BRONZE(), verts=12)
        return
    large, haut = (0.30, 2.65) if genre == "kinor" else (0.42, 2.95)
    if genre == "kinor":
        box(f"{nom}_{genre}_caisse", devant - 0.12, devant, y - large, y + large,
            z0 + 1.55, z0 + 1.85, col, bois)
    else:
        cone(f"{nom}_{genre}_caisse", devant - 0.10, y, z0 + 1.25, z0 + 1.95, large, 0.30,
             col, bois, verts=10)
    for s in (-1, 1):
        cyl(f"{nom}_{genre}_bras{s:+d}", devant - 0.06, y + s * (large - 0.04),
            z0 + 1.85, z0 + haut, 0.04, col, bois, verts=6)
    box(f"{nom}_{genre}_joug", devant - 0.10, devant - 0.02, y - large - 0.01,
        y + large + 0.01, z0 + haut - 0.05, z0 + haut + 0.03, col, bois)

# ----------------------------------------------------------------------------
# 76 — FOULE DE YOM KIPPOUR
#   Les places viennent des sources, pas de la mise en scène :
#   - le peuple dans l'Ezrat Israël, bande de 11 amot au bout est de l'Azara sur
#     toute la largeur (Middot 5:1, « מקום דריסת ישראל אחת עשרה אמה ») ; il ne
#     franchit pas l'Ezrat Cohanim sinon pour semikha, she'hita, tenoufa (Kelim 1:8) ;
#   - les cohanim dans les 11 amot suivantes, l'Ezrat Cohanim (Middot 5:1) ;
#   - le débordement dans l'Ezrat Nashim (135 × 135, Middot 2:5) puis sur le Har
#     HaBayit — l'Ezrat Israël ne fait que 11 × 135 ;
#   - les Léviim sont sur le Doukhan, entre les deux cours ;
#   - personne dans l'Oulam ni le Heikhal : « et nul homme ne sera dans la tente
#     d'assignation » (Lév. 16:17 ; Yoma 5:1 ne montre que le Cohen Gadol).
#   Collection séparée des proxys : un proxy est le sujet d'un plan, la foule est
#   l'état permanent du jour — elle est là dans tous les plans qui voient l'Azara.
#   Les Léviim en font partie : postés sur le Doukhan du matin au soir, ils ne sont
#   le sujet d'aucun plan. Rangés avec les proxys, ils disparaissaient du Doukhan
#   dès qu'un plan masquait les sujets d'un autre. Le plan 6 (prosternation) est le
#   seul à masquer cette collection : il a ses propres figures couchées.
# ----------------------------------------------------------------------------
FL = "76_Foule"
# Deux étoffes, pas une : sous une seule, la foule sort du rendu en une seule valeur
# et le styliseur habille tout le monde pareil — au plan 2, trois rangs de talith
# identiques. La laine sombre est le manteau, la claire le talith sur la tête.
MAT_FOULE = lambda: etoffe("Foule_laine", (0.46, 0.42, 0.37))
MAT_TALITH = lambda: etoffe("Talith_laine", (0.80, 0.78, 0.72))


def figurant(nom, x, y, z0, col, tenues, desordre, lacet=0.35):
    """Une figure de foule : écart, taille, tenue et lacet tirés de son nom."""
    silhouette(nom, x + (alea(nom, 0) - 0.5) * desordre, y + (alea(nom, 1) - 0.5) * desordre,
               z0, col, tenues[int(alea(nom, 3) * len(tenues))],
               h=H_HOMME * (0.93 + 0.14 * alea(nom, 2)),
               lacet=(alea(nom, 5) - 0.5) * 2 * lacet)

def foule(prefixe, xs, ys, z0, tenues, col=FL, ecart_axe=0.0, desordre=1.4, lacet=0.35):
    """Foule debout sur une grille, que le tirage défait. `ecart_axe` dégage une allée
    centrée sur y = 0.

    Une grille nue se lit en rangs d'objets identiques, pas en foule, et un jitter
    d'un quart de pas n'y change rien : on voyait encore les rangs. Trois tirages la
    défont — l'écart de chaque figure (`desordre`, amplitude en amot, plus de la
    moitié du pas), son lacet (`lacet`, demi-angle en radians), et des vides : une
    case de 3 × 3 sur trois est clairsemée, et chaque figure y manque une fois sur
    deux, pour que la densité ondule au lieu de remplir. `desordre=0` et `lacet=0`
    alignent au cordeau (chœur, file).
    """
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if abs(y) < ecart_axe:
                continue
            nom = f"{prefixe}_{i:02d}{j:02d}"
            clairseme = alea(f"{prefixe}_case_{i // 3}_{j // 3}") < 0.3
            if alea(nom, 4) < (0.5 if clairseme else 0.08):
                continue
            figurant(nom, x, y, z0, col, tenues, desordre, lacet)

def masse_foule(prefixe, xs, ys, z0, col=FL, ecart_axe=0.0):
    """Foule lointaine en blocs de 5 amot, pas en silhouettes.

    L'Ezrat Nashim fait 135 × 135 : une foule de Kippour s'y compte en milliers, que
    le blockout ne modélisera pas un par un. Un bloc à hauteur d'homme donne au
    Depth/Normal la bonne masse, et les hauteurs alternées empêchent l'ensemble de
    lire comme un mur crénelé.
    """
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if abs(y) < ecart_axe:
                continue
            h = (3.2, 3.65, 3.9)[(i + j) % 3]
            box(f"{prefixe}_{i:02d}{j:02d}", x, x + 5, y, y + 5, z0, z0 + h,
                col, MAT_FOULE())

if FOULE:
    # Le peuple : les 11 amot de l'Ezrat Israël (x -11..0), allée dégagée devant Nikanor.
    foule("Am_EzratIsrael", plage(-10, -2, 2), plage(-66, 66, 2), Z_AZ, TENUES_AM,
          ecart_axe=4)
    # Les cohanim : les 11 amot suivantes (x -22..-11), en tenue de service. On s'arrête à
    # l'est du Doukhan (x -13.5) et on laisse l'ouest libre pour le service. Désordre et
    # lacet réduits, pas nuls : le service les range, il ne les aligne pas.
    foule("Kohen_EzratKohanim", plage(-20, -15, 2.5), plage(-63, 63, 3), Z_AZ,
          (KOHEN,), desordre=1.2, lacet=0.2)
    # Débordement : Ezrat Nashim, puis la cour est du Har HaBayit. L'axe y = 0 reste
    # dégagé — c'est la ligne de mire de la para (Middot 2:4).
    # Pas de 5 pour des blocs de 5 : jointifs. Espacés d'une ama ils se lisaient en
    # caisses posées sur le dallage, et le plan 4 les prenait pour de la maçonnerie.
    masse_foule("Am_EzratNashim", plage(12, 127, 5), plage(-67, 62, 5), Z_EZN, ecart_axe=6)
    masse_foule("Am_HarHabayit", plage(157, 257, 5), plage(-67, 62, 5), Z_HAR, ecart_axe=10)
    # Les Léviim sur le Doukhan (3 marches, x -12..-13.5). « On ne descend pas au-dessous
    # de douze Léviim debout sur le Doukhan, et l'on ajoute sans limite » (Arakhin 2:6).
    # Chacun tient son instrument : jamais moins de neuf kinorot, de deux nevalim, et le
    # tziltzal seul (Arakhin 2:5, 2:3 ; Tamid 7:3) — neuf, deux et un font les douze.
    # En rang, sans lacet : c'est un chœur.
    INSTRUMENTS_DOUKHAN = ("kinor",) * 4 + ("nevel", "tziltzal", "nevel") + ("kinor",) * 5
    for i, genre in enumerate(INSTRUMENTS_DOUKHAN):
        silhouette(f"Levi_{i:02d}", -12.6, -22 + i * 4, Z_AZ + 2.5, FL, LEVI)
        instrument_de_levi(f"Levi_{i:02d}", genre, -12.6, -22 + i * 4, Z_AZ + 2.5, FL)
    # Les ketanim ne montent pas sur le Doukhan : ils se tiennent en bas, « la tête entre
    # les jambes des Léviim » (Arakhin 2:6, R. Eliézer ben Yaakov), et chantent sans
    # instrument (ibid.).
    for i in range(6):
        silhouette(f"Levi_katan_{i:02d}", -10.4, -10 + i * 4, Z_AZ + 1, FL, LEVI, h=2.3)
    # Le portique sud est l'entrée des fidèles : « on entre par la droite » depuis les
    # portes de 'Houlda (Middot 1:3, 2:2). Deux masses de part et d'autre de l'axe de la
    # nef (y = -242.5), l'axe lui-même laissé libre — c'est là que passe CAM_02.
    # Trois rangs décalés par côté, et non une file unique : des figures isolées au pas
    # régulier le long d'une nef se lisent en rangée de bornes, quand des silhouettes qui
    # se recouvrent se lisent en foule (CAM_04). Le rang extérieur reste à 2,25 amot du
    # fût des colonnes (y = -250 et -235, rayon 1,5).
    for cote in (-1, 1):
        for r, dy in enumerate((2.75, 4.0, 5.25)):
            for i, x in enumerate(plage(-180 + r * 1.0, 256, 3)):
                nom = f"Am_Portique_{cote:+d}_{r}_{i:03d}"
                if alea(nom, 4) < 0.12:
                    continue
                figurant(nom, x, -242.5 + cote * dy, Z_HAR, FL, TENUES_AM, desordre=1.2)
