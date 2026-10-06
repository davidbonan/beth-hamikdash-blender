import math

from mathutils import Vector, geometry

from ..primitives.parametres import AMA, Z_HAR
from ..primitives.matieres import (MAT_ACIER_BLANC, MAT_CHENE, MAT_DALLAGE_KOTEL, MAT_FER, MAT_FER_BRUN, MAT_MEHITSA, MAT_MURAILLE, MAT_OR, MAT_PIERRE,
                                   MAT_PIERRE_DE_JERUSALEM, MAT_PLASTIQUE, MAT_SOL, MAT_TERRE, MAT_TOILE, MAT_TOLE,
                                   MAT_VERRE_DE_LAMPE, MAT_VITRE)
from ..primitives.volumes import FACES_BOITE, alea, plage
from .calage import (CUVETTE_KOTEL, PARAPET_HAR, PAYS_DONNEES, Z_PLACE_HAUTE, Z_PLACE_KOTEL, _abscisses, _dans, _direct,
                     _plus_proche_sur_l_anneau, _point_a_l_abscisse, vers_scene, volumes)
from .place_du_kotel import (BORD_NORD, SOUS_LE_PONT, WILSON, _baie, _cap, _coupole, _devant, _extrusion, _fut, _pave, _point_de_wilson,
                             _poser, _poutre)
from .second_oeuvre import (Percements, _a_droite, _arc, _bandeau, _decale, _plaque, _unitaire, applique, climatiseur,
                            descente_d_eau, parabole, projecteur, repere_de_projecteur, verre_de_projecteur)


# Ce qui borde la place, relevé sur les photos (Wikimedia Commons, 2014–2025) et calé sur
# les emprises d'OSM. Les cotes que ni OSM ni une source ne donnent sont lues sur ces
# photos à l'échelle des dix-neuf mètres du Kotel : CHOIX.
ANGLE_DES_ARCADES, COUDE_DES_ARCADES, BOUT_DES_ARCADES, ANGLE_DE_LA_FONDATION, BOUT_DE_LA_FONDATION = BORD_NORD
BEIT_HALIBA = "w1528632636"
# La Fondation et la galerie à arcades sont bâties ici : leurs emprises d'OSM ne le sont pas deux fois.
FONDATION, GALERIE = "w394161633", "w1393400965"
PROFONDEUR_DES_ARCADES = 5 / AMA
H_ARCADES, H_ARRIERE = 4.8 / AMA, 11 / AMA
H_FONDATION, H_PAVILLON, RETRAIT_DU_PAVILLON = 10.7 / AMA, 4 / AMA, 3 / AMA
# Le côté sud de l'emprise d'OSM de la Fondation, d'est en ouest ; son parvis, lu sur les photos de 2025.
FACADE_DE_LA_FONDATION = (vers_scene(-148.5, -129.1), vers_scene(-184.6, -138.4))
H_PARVIS, LARGEUR_DU_PARVIS = 0.9 / AMA, 4.5 / AMA
AISH_HATORAH, H_AISH_HATORAH = "w288016665", 27 / AMA
# Une emprise d'OSM que le relief du modèle laisse dépasser du pied de la falaise : elle n'est pas bâtie.
AU_PIED_DE_LA_FALAISE = "w288016675"
# Les restes de l'ancienne rampe des Maghrébins : `mur_de_la_rampe` les bâtit, leur emprise d'OSM traversait son mur.
ANCIENNE_RAMPE = "w394161626"
H_MAKHKAMA = Z_HAR + PARAPET_HAR + 2.5 / AMA
H_BEIT_HALIBA, SURHAUSSE_BEIT_HALIBA = 9 / AMA, 1.2 / AMA


def _mur_a_arcades(p, q, z0, z1, epaisseur, arches=(), avance=0.0):
    """Le mur p→q, épais à sa droite et avancé d'`avance` à sa gauche, percé depuis son pied
    d'arches (abscisse du centre, portée, hauteur à la clé, flèche)."""
    bas = [(0, z0)]
    for centre, portee, cle, fleche in sorted(arches):
        bas += [(centre - portee / 2, z0)] + _arc(centre, portee / 2, z0 + cle - fleche, fleche) + [(centre + portee / 2, z0)]
    long_ = math.dist(p, q)
    profil = bas + [(long_, z0), (long_, z1), (0, z1)]
    return _extrusion(profil, _decale(p, _a_droite(p, q, -avance)), _a_droite(p, q, 1), _unitaire(p, q), epaisseur + avance)


def _plafond(anneau, z):
    """Le dessous d'une dalle : l'anneau à la cote z, faces vers le bas."""
    faces = []
    for a, b, c in geometry.tessellate_polygon([[Vector((x, y, z)) for x, y in anneau]]):
        (ax, ay), (bx, by), (cx, cy) = anneau[a], anneau[b], anneau[c]
        vers_le_bas = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) < 0
        faces.append([a, b, c] if vers_le_bas else [a, c, b])
    return [(x, y, z) for x, y in anneau], faces


def _travees(longueur, pas, marge=0.0):
    n = max(1, int((longueur - 2 * marge) / pas))
    return [(longueur - (n - 1) * pas) / 2 + i * pas for i in range(n)]


def _lisse(a, b, z, section):
    return _poutre(a, b, z, z, section / 2, -section / 2, section), FACES_BOITE


def garde_corps(trace, z, hauteur=1.1 / AMA, pas=1.5 / AMA):
    """Une main courante, une lisse basse et des potelets, à la cote z."""
    pieces = []
    for a, b in zip(trace, trace[1:]):
        pieces += [_lisse(a, b, z + hauteur - 0.05 / AMA, 0.05 / AMA), _lisse(a, b, z + 0.15 / AMA, 0.03 / AMA),
                   _lisse(a, b, z + hauteur / 2, 0.03 / AMA)]
    for s in plage(0, _abscisses(trace)[-1], pas) + [_abscisses(trace)[-1]]:
        pieces.append(_fut(_point_a_l_abscisse(trace, s)[0], z, z + hauteur, 0.03 / AMA, 4))
    return pieces


def makhkama():
    """Au nord de l'aire de prière, le mur sud de la Tankiziyya (la Ma'hkama), bâtie en 1328–1329
    sur l'arche de Wilson : une vingtaine de mètres de pierre mamelouke, deux contreforts
    talutés, trois arches basses à son pied — celle qui touche le Kotel mène sous l'arche —,
    un rang de fenêtres grillées et un rang de baies cintrées (Wikipedia, « Tankiziyya »).
    Elle dépasse le Kotel de deux à trois mètres."""
    _, u, v, _, largeur = WILSON
    p, q = _point_de_wilson(0, 0), _point_de_wilson(0, largeur)
    pied = Z_PLACE_KOTEL - 1
    hall = [(c / AMA, 4.6 / AMA, pied_cle, 1.4 / AMA) for c, pied_cle in ((3.4, 1 + 3.9 / AMA), (9.6, 1 + 3.6 / AMA))]
    _poser("Makhkama_mur", [_mur_a_arcades(p, q, pied, H_MAKHKAMA, 1.6 / AMA, hall, 0.3 / AMA)], MAT_PIERRE_DE_JERUSALEM())
    corps = [_point_de_wilson(1.6 / AMA, 0), _point_de_wilson(1.6 / AMA, largeur),
             _point_de_wilson(10 / AMA, largeur), _point_de_wilson(10 / AMA, 0)]
    volumes("Makhkama_corps", [(corps, [], Z_HAR, H_MAKHKAMA)], "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    sud = (-u[0], -u[1])
    contreforts = []
    for pv in (6.6, 13.2):
        coin = _decale(_point_de_wilson(0, (pv - 1.4) / AMA), (sud[0] * 0.3 / AMA, sud[1] * 0.3 / AMA))
        profil = [(0, pied), (1.9 / AMA, pied), (1.9 / AMA, Z_PLACE_KOTEL + 7.6 / AMA), (0, Z_PLACE_KOTEL + 10 / AMA)]
        contreforts.append(_extrusion(profil, coin, v, sud, 2.8 / AMA))
    _poser("Makhkama_contreforts", contreforts, MAT_PIERRE_DE_JERUSALEM())
    avant = lambda point: _decale(point, (sud[0] * 0.3 / AMA, sud[1] * 0.3 / AMA))
    pa, qa = avant(p), avant(q)
    baies = Percements()
    for s in (3.2, 9.9, 16.5, 19.6):
        baies.fenetre(pa, qa, s / AMA, Z_PLACE_KOTEL + 9.2 / AMA, 1.0 / AMA, 1.5 / AMA, cintre=False, grille=True)
    for s in (2.6, 8.4, 15.4):
        baies.fenetre(pa, qa, s / AMA, Z_PLACE_KOTEL + 14.2 / AMA, 1.2 / AMA, 2.0 / AMA)
    for centre, portee, cle, fleche in hall:
        baies.arche(pa, qa, centre, pied, (portee, cle, fleche))
    baies.vitres.append(_baie(pa, qa, 16.4 / AMA, Z_PLACE_KOTEL, 3.2 / AMA, 3.0 / AMA, 0.02 / AMA))
    baies.arche(pa, qa, 16.4 / AMA, Z_PLACE_KOTEL, (3.2 / AMA, 3.0 / AMA, 1.6 / AMA))
    baies.pierres += [_bandeau(pa, qa, H_MAKHKAMA - 0.3 / AMA), _bandeau(pa, qa, Z_PLACE_KOTEL + 12.6 / AMA, 0.18 / AMA, 0.05 / AMA)]
    baies.poser("Makhkama", MAT_PIERRE_DE_JERUSALEM())
    # Sur le toit, la rampe de projecteurs tournée vers la place et deux mâts ; sur les
    # contreforts, les haut-parleurs ; à l'angle du Kotel, la descente d'eau. Leur nombre : CHOIX.
    rive = [_decale(point, (u[0] * 0.5 / AMA, u[1] * 0.5 / AMA)) for point in (p, q)]
    vers_la_place = math.atan2(sud[1], sud[0])
    grilles = [_lisse(*rive, H_MAKHKAMA + 0.9 / AMA, 0.06 / AMA)]
    grilles += [_fut(_devant(rive[0], _cap(*rive), s / AMA), H_MAKHKAMA, H_MAKHKAMA + (4 if s in (2, 20) else 0.9) / AMA, 0.04 / AMA, 4)
                for s in (2, 6.5, 11, 15.5, 20)]
    rampe = [_devant(rive[0], _cap(*rive), s / AMA) for s in plage(3.5, 19, 1.9)]
    grilles += [piece for point in rampe for piece in projecteur(point, H_MAKHKAMA + 1.15 / AMA, vers_la_place)]
    _poser("Kotel_makhkama_verres", [verre_de_projecteur(point, H_MAKHKAMA + 1.15 / AMA, vers_la_place) for point in rampe], MAT_VERRE_DE_LAMPE())
    repere_de_projecteur("makhkama", rampe[len(rampe) // 2], H_MAKHKAMA + 1.3 / AMA)
    grilles += [_plaque(pa, qa, pv / AMA, Z_PLACE_KOTEL + h / AMA, 0.4 / AMA, 0.5 / AMA, 2.0 / AMA) for pv in (6.6, 13.2) for h in (5.2, 5.9)]
    grilles += descente_d_eau(pa, qa, 0.7 / AMA, Z_PLACE_KOTEL, H_MAKHKAMA)
    _poser("Makhkama_grilles", grilles, MAT_FER_BRUN())
    # À son angle ouest, le mur s'épaule d'un glacis de pierre qui redescend vers la terrasse des arcades.
    pied_du_glacis = Z_PLACE_HAUTE + H_ARRIERE - 0.5 / AMA
    glacis = [(0, pied_du_glacis), (8 / AMA, pied_du_glacis), (8 / AMA, pied_du_glacis + 0.6 / AMA), (0, H_MAKHKAMA - 4 / AMA)]
    _poser("Makhkama_glacis", [_extrusion(glacis, _decale(q, (u[0] * 1.2 / AMA, u[1] * 1.2 / AMA)), sud, v, 1.5 / AMA)], MAT_PIERRE_DE_JERUSALEM())


def toits_du_nord():
    """Ce que la photo de décembre 2025 montre au-dessus de la Ma'hkama et du mur des arcades : une
    petite coupole sur son tambour, des cuves, des paraboles et les caissons des climatiseurs,
    en désordre. Leur nombre et leur place : CHOIX."""
    _, _, _, _, largeur = WILSON
    toit = lambda pu, pv: _point_de_wilson(pu / AMA, pv / AMA)
    pierres = [_fut(toit(6, 7), H_MAKHKAMA, H_MAKHKAMA + 1.2 / AMA, 2.2 / AMA, 12), _coupole(toit(6, 7), H_MAKHKAMA + 1.2 / AMA, 2.1 / AMA)]
    pierres += [_pave(toit(5, largeur * AMA - 3), 0.2, 3 / AMA, 2.4 / AMA, H_MAKHKAMA, H_MAKHKAMA + 2.3 / AMA)]
    _poser("Makhkama_toit", pierres, MAT_PIERRE_DE_JERUSALEM())
    blancs, fers = [], []
    for k, (pu, pv) in enumerate(((3, 12), (8, 13.5), (4.5, 16), (8.5, 3), (2.5, 4))):
        if k < 2:
            blancs.append(_fut(toit(pu, pv), H_MAKHKAMA + 0.6 / AMA, H_MAKHKAMA + 1.9 / AMA, 0.45 / AMA, 8))
            fers += [_fut(_devant(toit(pu, pv), i * math.pi / 2, 0.35 / AMA), H_MAKHKAMA, H_MAKHKAMA + 0.6 / AMA, 0.03 / AMA, 4) for i in range(4)]
        else:
            blancs += parabole(toit(pu, pv), H_MAKHKAMA, 2.4 + 0.3 * k, 0.5 / AMA)
    blancs += [_pave(toit(pu, pv), 0.3 * k, 0.9 / AMA, 0.4 / AMA, H_MAKHKAMA + 0.1 / AMA, H_MAKHKAMA + 0.75 / AMA)
               for k, (pu, pv) in enumerate(((7, 16.5), (8.2, 16.5), (3, 8.5), (9, 9)))]
    _poser("Makhkama_toit_equipements", blancs, MAT_PLASTIQUE())
    _poser("Makhkama_toit_supports", fers, MAT_FER_BRUN())


def arcades_du_nord():
    """Entre la Ma'hkama et le bâtiment de la Fondation, une galerie d'un niveau ouvre sur l'aire
    des hommes par des arches en plein cintre ; son toit est une terrasse à garde-corps, sous
    un auvent de toile, adossée à un mur de pierre lisse deux fois plus haut qu'elle. Un
    mur de bout, à l'ouest, porte la grille dorée à la menora."""
    fond = _a_droite(ANGLE_DES_ARCADES, BOUT_DES_ARCADES, PROFONDEUR_DES_ARCADES)
    loin = _a_droite(ANGLE_DES_ARCADES, BOUT_DES_ARCADES, 9 / AMA)
    pied, terrasse = Z_PLACE_KOTEL - 1, Z_PLACE_HAUTE + H_ARCADES
    front = [ANGLE_DES_ARCADES, COUDE_DES_ARCADES, BOUT_DES_ARCADES, ANGLE_DE_LA_FONDATION]
    murs = []
    for p, q in zip(front[:2], front[1:3]):
        arches = [(s, 3.1 / AMA, Z_PLACE_HAUTE - pied + 3.7 / AMA, 1.55 / AMA) for s in _travees(math.dist(p, q), 4 / AMA, 0.6 / AMA)]
        murs.append(_mur_a_arcades(p, q, pied, terrasse + 0.25 / AMA, 0.6 / AMA, arches))
    murs.append(_mur_a_arcades(BOUT_DES_ARCADES, ANGLE_DE_LA_FONDATION, pied, terrasse + 0.25 / AMA, 0.6 / AMA))
    retour = _decale(ANGLE_DES_ARCADES, fond)
    murs.append(_mur_a_arcades(retour, ANGLE_DES_ARCADES, pied, terrasse + 0.25 / AMA, 0.6 / AMA,
                               [(math.dist(retour, ANGLE_DES_ARCADES) / 2, 2.6 / AMA, Z_PLACE_HAUTE - pied + 3.4 / AMA, 1.3 / AMA)]))
    _poser("Kotel_nord_arcades", murs, MAT_PIERRE_DE_JERUSALEM())
    modenature, lanternes, potences = Percements(), [], []
    for p, q in zip(front[:2], front[1:3]):
        centres = _travees(math.dist(p, q), 4 / AMA, 0.6 / AMA)
        for s in centres:
            modenature.arche(p, q, s, pied, (3.1 / AMA, Z_PLACE_HAUTE - pied + 3.7 / AMA, 1.55 / AMA))
        for s in centres[1:]:
            lanterne, potence = applique(p, q, s - 2 / AMA, Z_PLACE_HAUTE + 3.5 / AMA)
            lanternes.append(lanterne)
            potences += potence
        modenature.pierres += [_bandeau(p, q, terrasse - 0.1 / AMA), _bandeau(p, q, Z_PLACE_HAUTE, 0.5 / AMA, 0.05 / AMA)]
    modenature.poser("Kotel_nord_arcades", MAT_PIERRE_DE_JERUSALEM())
    _poser("Kotel_nord_lanternes", lanternes, MAT_VERRE_DE_LAMPE())
    emprise = front + [_decale(p, fond) for p in front[::-1]]
    volumes("Kotel_nord_arcades_sol", [(emprise, [], pied, Z_PLACE_HAUTE)], "00_HarHabayit", MAT_SOL())
    volumes("Kotel_nord_terrasse", [(emprise, [], terrasse - 0.4 / AMA, terrasse)], "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    _poser("Kotel_nord_plafond", [_plafond(emprise, terrasse - 0.4 / AMA)], MAT_PIERRE_DE_JERUSALEM())
    arriere = [_decale(p, fond) for p in front] + [_decale(p, loin) for p in front[::-1]]
    volumes("Kotel_nord_mur_arriere", [(arriere, [], pied, Z_PLACE_HAUTE + H_ARRIERE)], "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    devant = _a_droite(ANGLE_DES_ARCADES, BOUT_DES_ARCADES, 0.15 / AMA)
    rambarde = [_decale(retour, devant)] + [_decale(p, devant) for p in front]
    _poser("Kotel_nord_garde_corps", garde_corps(rambarde, terrasse), MAT_FER_BRUN())

    # Sous chaque arche, un vitrage au nu intérieur du mur et sa menuiserie de fer brun — de la
    # galerie on voit une cloison claire, pas le dos du vitrage — ; sur le premier trumeau,
    # l'horloge des douze tribus (2018).
    vitrages, menuiseries, dos = [], [], []
    for p, q in zip(front[:2], front[1:3]):
        retrait = _a_droite(p, q, 0.5 / AMA)
        pr, qr = _decale(p, retrait), _decale(q, retrait)
        for s in _travees(math.dist(p, q), 4 / AMA, 0.6 / AMA):
            dos.append(_baie(qr, pr, math.dist(p, q) - s, Z_PLACE_HAUTE, 3.1 / AMA, 3.7 / AMA, 0.02 / AMA))
            vitrages.append(_baie(pr, qr, s, Z_PLACE_HAUTE, 3.1 / AMA, 3.7 / AMA, 0.02 / AMA))
            menuiseries += [_plaque(pr, qr, s, Z_PLACE_HAUTE + 2.15 / AMA, 3.1 / AMA, 0.06 / AMA, 0.06 / AMA),
                            _plaque(pr, qr, s, Z_PLACE_HAUTE, 0.06 / AMA, 2.15 / AMA, 0.06 / AMA)]
    _poser("Kotel_nord_vitrages", vitrages, MAT_VITRE())
    _poser("Kotel_nord_cloisons", dos, MAT_PLASTIQUE())
    _poser("Kotel_nord_horloge", [_plaque(front[0], front[1], 2.3 / AMA, Z_PLACE_HAUTE + 2.4 / AMA, 0.9 / AMA, 0.9 / AMA, 0.06 / AMA)], MAT_PLASTIQUE())
    tete_du_mur = [_decale(point, fond) for point in front]
    menuiseries += potences + garde_corps(tete_du_mur, Z_PLACE_HAUTE + H_ARRIERE, 2.2 / AMA, 2.5 / AMA)
    vers_la_place = _cap((0, 0), _a_droite(ANGLE_DES_ARCADES, BOUT_DES_ARCADES, -1))
    rampe = [_point_a_l_abscisse(tete_du_mur, s)[0] for s in plage(1.5 / AMA, _abscisses(tete_du_mur[:3])[-1], 2.5 / AMA)]
    menuiseries += [piece for point in rampe for piece in projecteur(point, Z_PLACE_HAUTE + H_ARRIERE + 0.4 / AMA, vers_la_place)]
    _poser("Kotel_nord_verres", [verre_de_projecteur(point, Z_PLACE_HAUTE + H_ARRIERE + 0.4 / AMA, vers_la_place) for point in rampe], MAT_VERRE_DE_LAMPE())
    repere_de_projecteur("galerie", rampe[len(rampe) // 2], Z_PLACE_HAUTE + H_ARRIERE + 0.55 / AMA)
    # Sur le mur du fond, à l'ouest de la verrière, le grand écran noir des cérémonies (photo de décembre 2025).
    ecran = (tete_du_mur[1], tete_du_mur[2], 5 / AMA, terrasse + 0.9 / AMA)
    _poser("Kotel_nord_ecran", [_plaque(*ecran, 6 / AMA, 4.4 / AMA, 0.25 / AMA)], MAT_FER())
    _poser("Kotel_nord_ecran_cadre", [_plaque(ecran[0], ecran[1], ecran[2] + t * 3.1 / AMA, ecran[3] - 0.1 / AMA, 0.2 / AMA, 4.6 / AMA, 0.3 / AMA)
                                      for t in (-1, 1)] + [_plaque(ecran[0], ecran[1], ecran[2], ecran[3] + h, 6.4 / AMA, 0.2 / AMA, 0.3 / AMA)
                                                           for h in (-0.2 / AMA, 4.4 / AMA)], MAT_TOILE())

    # La verrière de la terrasse, contre la Ma'hkama : cinq berceaux de tôle translucide sur un cadre sombre.
    cap = _cap(ANGLE_DES_ARCADES, COUDE_DES_ARCADES)
    berceaux = [_devant(ANGLE_DES_ARCADES, cap, (1.6 + 2.3 * k) / AMA, -2.4 / AMA) for k in range(5)]
    _poser("Kotel_nord_auvent", [_voute(centre, cap + math.pi / 2, 2.3 / AMA, 4 / AMA, terrasse + 2.4 / AMA, 0.55 / AMA) for centre in berceaux],
           MAT_TOLE())
    menuiseries += [_fut(_devant(centre, cap, t * 1.15 / AMA, a * 1.9 / AMA), terrasse, terrasse + 2.4 / AMA, 0.04 / AMA, 4)
                    for centre in (berceaux[0], berceaux[2], berceaux[4]) for t in (-1, 1) for a in (-1, 1)]
    menuiseries += [_lisse(_devant(berceaux[0], cap, -1.15 / AMA, a * 1.9 / AMA), _devant(berceaux[4], cap, 1.15 / AMA, a * 1.9 / AMA),
                           terrasse + 2.35 / AMA, 0.08 / AMA) for a in (-1, 1)]
    _poser("Kotel_nord_menuiseries", menuiseries, MAT_FER_BRUN())
    # Au pied de la Ma'hkama, le kiosque où l'on prête des kippot, sous son auvent de toile.
    _, _, _, _, largeur = WILSON
    kiosque = _point_de_wilson(-2.6 / AMA, largeur - 3.5 / AMA)
    travers = _cap(_point_de_wilson(0, 0), _point_de_wilson(0, largeur))
    _poser("Kotel_nord_kiosque", [_pave(kiosque, travers, 3 / AMA, 1.6 / AMA, Z_PLACE_KOTEL, Z_PLACE_KOTEL + 1.05 / AMA),
                                  _pave(_devant(kiosque, travers, 0, 0.7 / AMA), travers, 3 / AMA, 0.2 / AMA, Z_PLACE_KOTEL, Z_PLACE_KOTEL + 2.3 / AMA)],
           MAT_CHENE())
    _poser("Kotel_nord_kiosque_auvent", [(_poutre(_devant(kiosque, travers + math.pi / 2, -0.9 / AMA), _devant(kiosque, travers + math.pi / 2, 1.3 / AMA),
                                                  Z_PLACE_KOTEL + 2.5 / AMA, Z_PLACE_KOTEL + 2.1 / AMA, 1.7 / AMA, -1.7 / AMA, 0.05 / AMA), FACES_BOITE)],
           MAT_TOILE())

    # Au bout ouest, le mur de la galerie donne sur le parvis de la Fondation ; la grille dorée à la menora y ferme l'accès de la terrasse.
    bout = (ANGLE_DE_LA_FONDATION, _decale(ANGLE_DE_LA_FONDATION, fond))
    _poser("Kotel_nord_mur_de_bout", [_mur_a_arcades(*bout, pied, terrasse + 0.25 / AMA, 0.6 / AMA)], MAT_PIERRE_DE_JERUSALEM())
    _poser("Kotel_nord_grille_de_la_menora", [_plaque(*bout, 1.4 / AMA, Z_PLACE_HAUTE + H_PARVIS, 1.8 / AMA, 2.3 / AMA, 0.06 / AMA)], MAT_MEHITSA())


def batiment_de_la_fondation(porche=7.3 / AMA, travee=2.45 / AMA, profondeur=1.6 / AMA):
    """Le bâtiment de pierre claire qui ferme la place au nord-ouest — la Fondation du patrimoine
    du Kotel, l'entrée des tunnels —, tel que les photos d'avril et juin 2025 le montrent : une
    façade lisse en deux pans de part et d'autre d'un joint creux, six paires de fenêtres au nu du
    mur à l'étage seulement, et à l'est le porche des tunnels, cinq travées en retrait — trois
    portes vitrées entre deux fenêtres sur allège, sous leur store — entre
    des piliers sous l'inscription dorée « מנהרות הכותל · Western Wall Tunnels Site » ; sur le
    toit, en retrait, un pavillon vitré à l'ossature blanche. Les cinq niveaux d'OSM se
    comptent jusqu'au pavillon. Sa façade est le côté sud de son emprise d'OSM, deux à trois
    mètres derrière le bord de la place : devant elle, un parvis surélevé derrière un parapet
    de pierre, où l'on monte par une rampe depuis l'ouest. Cotes du porche, du parvis et des
    fenêtres : lues sur ces photos à l'échelle des trente-sept mètres de la façade."""
    p, q = FACADE_DE_LA_FONDATION
    cap, longueur = _cap(p, q), math.dist(p, q)
    fond = _a_droite(p, q, 14 / AMA)
    pied, haut, seuil = Z_PLACE_KOTEL - 1, Z_PLACE_HAUTE + H_FONDATION, Z_PLACE_HAUTE + H_PARVIS
    linteau = seuil + 3.1 / AMA
    demi = 2.5 * travee + 0.3 / AMA
    dedans = lambda s, d: _devant(p, cap, s, -d)
    emprise = [p, q, _decale(q, fond), _decale(p, fond)]
    niche = [dedans(porche - demi, 0), dedans(porche - demi, profondeur), dedans(porche + demi, profondeur), dedans(porche + demi, 0)]
    joint = [dedans(longueur * 0.49 + d, creux) for d, creux in ((-0.2 / AMA, 0), (-0.2 / AMA, 0.3 / AMA), (0.2 / AMA, 0.3 / AMA), (0.2 / AMA, 0))]
    volumes("Fondation_du_Kotel", [([p] + niche + joint + emprise[1:], [], pied, linteau), ([p] + joint + emprise[1:], [], linteau, haut)],
            "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    au_fond = (dedans(0, profondeur), dedans(longueur, profondeur))
    piliers = [_pave(dedans(porche + (k - 2.5) * travee, profondeur / 2), cap, 0.6 / AMA, profondeur, seuil, linteau) for k in range(6)]
    piliers += [_plafond(niche, linteau), _plaque(p, q, porche, linteau, 2 * demi + 0.5 / AMA, 0.8 / AMA, 0.06 / AMA)]
    travees = [porche + (k - 2) * travee for k in range(5)]
    piliers += [_plaque(*au_fond, s, seuil, travee - 0.6 / AMA, 0.9 / AMA, 0.08 / AMA) for s in (travees[0], travees[-1])]
    _poser("Fondation_du_Kotel_piliers", piliers, MAT_PIERRE_DE_JERUSALEM())
    vitres = [_plaque(*au_fond, porche, seuil, 2 * demi, linteau - seuil, 0.02 / AMA)]
    cadres = [_plaque(*au_fond, porche, seuil + 2.2 / AMA, 3 * travee - 0.6 / AMA, 0.06 / AMA, 0.05 / AMA)]
    cadres += [_plaque(*au_fond, s + t * 0.5 / AMA, seuil, 0.05 / AMA, 2.2 / AMA, 0.05 / AMA) for s in travees[1:-1] for t in (-1, 1)]
    cadres += [_plaque(*au_fond, s, seuil, 0.04 / AMA, 2.2 / AMA, 0.05 / AMA) for s in travees[1:-1]]
    cadres += [_plaque(*au_fond, s + t * 0.08 / AMA, seuil + 0.9 / AMA, 0.03 / AMA, 0.35 / AMA, 0.09 / AMA) for s in travees[1:-1] for t in (-1, 1)]
    stores = [_plaque(*au_fond, s, seuil + 1.9 / AMA, travee - 0.6 / AMA, linteau - seuil - 1.9 / AMA, 0.07 / AMA) for s in (travees[0], travees[-1])]
    cadres.append(_plaque(p, q, longueur * 0.95, haut - 1.9 / AMA, 0.7 / AMA, 0.7 / AMA, 0.04 / AMA))
    tablettes = [_bandeau(p, q, haut - 0.2 / AMA, 0.2 / AMA, 0.05 / AMA)]
    for fraction in (0.06, 0.18, 0.32, 0.58, 0.74, 0.91):
        v, tb = _fentes(p, q, longueur * fraction, Z_PLACE_HAUTE + 5.8 / AMA, 1.7 / AMA, 0.95 / AMA)
        vitres, tablettes = vitres + v, tablettes + tb
    _poser("Fondation_du_Kotel_fenetres", vitres, MAT_VITRE())
    _poser("Fondation_du_Kotel_tablettes", tablettes, MAT_PIERRE())
    _poser("Fondation_du_Kotel_cages", cadres, MAT_FER_BRUN())
    _poser("Fondation_du_Kotel_stores", stores, MAT_TOILE())
    _poser("Fondation_du_Kotel_inscription", [_plaque(p, q, porche, linteau + 0.25 / AMA, 7.5 / AMA, 0.28 / AMA, 0.09 / AMA)], MAT_OR())
    _poser("Fondation_du_Kotel_panneau", [_plaque(p, q, longueur * 0.86, Z_PLACE_HAUTE + 1.2 / AMA, 1.0 / AMA, 1.6 / AMA, 0.05 / AMA)], MAT_PLASTIQUE())
    parvis_de_la_fondation()

    retrait = _a_droite(p, q, RETRAIT_DU_PAVILLON)
    pr, qr = _decale(p, retrait), _decale(q, retrait)
    pavillon = [pr, qr, _decale(q, fond), _decale(p, fond)]
    volumes("Fondation_du_Kotel_pavillon", [(pavillon, [], haut, haut + H_PAVILLON - 0.3 / AMA)], "00_HarHabayit", MAT_VITRE())
    volumes("Fondation_du_Kotel_corniche", [(emprise, [], haut + H_PAVILLON - 0.3 / AMA, haut + H_PAVILLON)], "00_HarHabayit", MAT_ACIER_BLANC())
    rive = _a_droite(p, q, 0.3 / AMA)
    poteaux = [_pave(_decale(_devant(p, cap, s), rive), cap, 0.3 / AMA, 0.3 / AMA, haut, haut + H_PAVILLON - 0.3 / AMA)
               for s in _travees(longueur, 4 / AMA, 0.4 / AMA)]
    poteaux += [_plaque(pr, qr, s, haut, 0.12 / AMA, H_PAVILLON - 0.3 / AMA, 0.08 / AMA) for s in _travees(longueur, 2 / AMA, 0.4 / AMA)]
    _poser("Fondation_du_Kotel_poteaux", poteaux, MAT_ACIER_BLANC())
    _poser("Fondation_du_Kotel_garde_corps", garde_corps([_decale(p, rive), _decale(q, rive)], haut), MAT_ACIER_BLANC())


def parvis_de_la_fondation(palier=15 / AMA, rampe=14 / AMA, epaisseur=0.4 / AMA):
    """Devant la Fondation : un palier à hauteur du porche, une rampe qui en redescend vers
    l'ouest jusqu'à la place, et le parapet de pierre qui les borde — haut devant le porche,
    bas le long de la rampe —, refermé à l'est contre la galerie."""
    p, q = FACADE_DE_LA_FONDATION
    cap = _cap(p, q)
    pied, seuil = Z_PLACE_KOTEL - 1, Z_PLACE_HAUTE + H_PARVIS
    devant = lambda s, d: _devant(p, cap, s, d)
    seuil_de_la_place = [ANGLE_DE_LA_FONDATION, BOUT_DE_LA_FONDATION, q, p]
    dalle = [devant(0, LARGEUR_DU_PARVIS), devant(palier, LARGEUR_DU_PARVIS), devant(palier, -1.6 / AMA), devant(0, -1.6 / AMA)]
    volumes("Fondation_du_Kotel_parvis", [(seuil_de_la_place, [], pied, Z_PLACE_HAUTE), (dalle, [], pied, seuil)], "00_HarHabayit", MAT_DALLAGE_KOTEL())
    pente = (_poutre(devant(palier, 0), devant(palier + rampe, 0), seuil - 1, Z_PLACE_HAUTE - 1, LARGEUR_DU_PARVIS, 0, 1), FACES_BOITE)
    _poser("Fondation_du_Kotel_rampe", [pente], MAT_DALLAGE_KOTEL())
    garde = 0.95 / AMA
    profil = [(0, Z_PLACE_HAUTE), (palier + rampe + 0.5 / AMA, Z_PLACE_HAUTE), (palier + rampe + 0.5 / AMA, Z_PLACE_HAUTE + garde),
              (palier + rampe / 2, Z_PLACE_HAUTE + garde), (palier, seuil + garde), (0, seuil + garde)]
    parapet = [_extrusion(profil, devant(0, LARGEUR_DU_PARVIS), _a_droite(p, q, -1), _unitaire(p, q), epaisseur),
               (_poutre(p, devant(0, LARGEUR_DU_PARVIS + epaisseur), Z_PLACE_HAUTE, Z_PLACE_HAUTE, epaisseur, 0, seuil + garde - Z_PLACE_HAUTE), FACES_BOITE)]
    _poser("Fondation_du_Kotel_parapet", parapet, MAT_PIERRE_DE_JERUSALEM())


def _fentes(p, q, s, seuil, hauteur, largeur=0.55 / AMA):
    """Deux fentes hautes côte à côte, au nu du mur, et sous chacune sa tablette de pierre claire : (vitres, tablettes)."""
    cotes = [s + t * (largeur / 2 + 0.3 / AMA) for t in (-1, 1)]
    return ([_plaque(p, q, c, seuil, largeur, hauteur, 0.02 / AMA) for c in cotes],
            [_plaque(p, q, c, seuil - 0.75 / AMA, largeur + 0.1 / AMA, 0.75 / AMA, 0.03 / AMA) for c in cotes])


def beit_haliba(anneau):
    """Beit HaLiba, le centre du patrimoine du Kotel d'Ada Karmi-Melamede, inauguré en novembre
    2021 au fond de la place, sur les fouilles du cardo oriental qu'il laisse voir à son
    niveau bas (Wikipedia, « Western Wall Plaza »). Sa façade, lue sur la photo de fin de
    chantier d'E.D. Rahat, l'élévation est et la perspective de l'agence (Xnet, 2015) : deux
    niveaux de pierre lisse sous un acrotère nu, presque aveugles — des fentes hautes par
    paires à l'étage, « des meurtrières » dit Xnet —, deux volumes que sépare une faille
    vitrée de toute la hauteur, celui du nord un peu plus haut, l'entrée vitrée en retrait
    sous un linteau ; sur le toit, la verrière cintrée de l'atrium des fouilles, des
    projecteurs et des mâts. Hauteurs, pas des fentes et place de la faille : CHOIX à
    l'échelle de ces images."""
    nord, sud = _plus_proches(anneau, (-182, -155)), _plus_proches(anneau, (-175, -195))
    pied, haut = Z_PLACE_KOTEL - 1, Z_PLACE_HAUTE + H_BEIT_HALIBA
    volumes("Beit_HaLiba", [(anneau, [], pied, haut)], "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    longueur = math.dist(nord, sud)
    faille = longueur * 0.42
    # Le volume du nord dépasse l'autre d'un acrotère et avance d'un demi-mètre sur la place.
    avance = _a_droite(nord, sud, -0.5 / AMA)
    proue = [nord, _devant(nord, _cap(nord, sud), faille - 0.9 / AMA)]
    proue = proue + [_decale(p, avance) for p in proue[::-1]]
    volumes("Beit_HaLiba_volume_nord", [(_direct(proue), [], pied, haut + SURHAUSSE_BEIT_HALIBA)], "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    na, sa = _decale(nord, avance), _decale(sud, avance)
    vitres, tablettes = [_plaque(nord, sud, faille, Z_PLACE_HAUTE, 1.8 / AMA, haut - Z_PLACE_HAUTE - 0.4 / AMA, 0.02 / AMA)], []
    etage = Z_PLACE_HAUTE + 5.4 / AMA
    for p, q, debut, fin in ((na, sa, 2.5 / AMA, faille - 2.5 / AMA), (nord, sud, faille + 3 / AMA, longueur - 2 / AMA)):
        for s in plage(debut, fin, 4.2 / AMA):
            v, tb = _fentes(p, q, s, etage, 2.3 / AMA)
            vitres, tablettes = vitres + v, tablettes + tb
    contour = _direct(anneau)
    for p, q in zip(contour, contour[1:] + contour[:1]):
        if {p, q} == {nord, sud} or math.dist(p, q) < 8 / AMA:
            continue
        for s in _travees(math.dist(p, q), 5 / AMA, 3 / AMA):
            v, tb = _fentes(q, p, s, etage, 2.3 / AMA)
            vitres, tablettes = vitres + v, tablettes + tb
    # L'entrée : une baie vitrée en retrait sous un linteau sombre, et deux jours carrés au rez-de-chaussée.
    entree = faille + 6 / AMA
    vitres += [_plaque(nord, sud, entree, Z_PLACE_HAUTE, 4.2 / AMA, 3.1 / AMA, 0.02 / AMA)]
    vitres += [_plaque(nord, sud, entree + s / AMA, Z_PLACE_HAUTE + 3.0 / AMA, 0.6 / AMA, 0.6 / AMA, 0.02 / AMA) for s in (7, 12)]
    menuiseries = [_plaque(nord, sud, entree, Z_PLACE_HAUTE + 3.1 / AMA, 5.2 / AMA, 0.3 / AMA, 0.9 / AMA)]
    menuiseries += [_plaque(nord, sud, entree + t * 0.7 / AMA, Z_PLACE_HAUTE, 0.05 / AMA, 3.1 / AMA, 0.05 / AMA) for t in (-3, -1, 1, 3)]
    menuiseries += [_plaque(nord, sud, faille, Z_PLACE_HAUTE + h / AMA, 1.8 / AMA, 0.05 / AMA, 0.05 / AMA) for h in plage(1.5, 8, 1.5)]
    _poser("Beit_HaLiba_vitrages", vitres, MAT_VITRE())
    _poser("Beit_HaLiba_tablettes", tablettes, MAT_PIERRE())
    # Sur le toit : la verrière de l'atrium, une rampe de projecteurs tournée vers la place, quatre mâts.
    cx, cy = sum(x for x, _ in anneau) / len(anneau), sum(y for _, y in anneau) / len(anneau)
    cap = _cap(nord, sud)
    _poser("Beit_HaLiba_verriere", [_voute((cx, cy), cap, 12 / AMA, 16 / AMA, haut + 0.3 / AMA, 1.6 / AMA)], MAT_VITRE())
    rive = [_decale(p, _a_droite(nord, sud, 1.2 / AMA)) for p in (nord, sud)]
    vers_la_place = _cap((0, 0), _a_droite(nord, sud, -1))
    menuiseries += [_lisse(_devant(rive[0], cap, faille + 8 / AMA), _devant(rive[0], cap, faille + 13 / AMA), haut + 1.6 / AMA, 0.05 / AMA)]
    rampe = [_devant(rive[0], cap, faille + s / AMA) for s in (8.6, 9.9, 11.2, 12.5)]
    menuiseries += [piece for point in rampe for piece in projecteur(point, haut + 1.65 / AMA, vers_la_place)]
    _poser("Beit_HaLiba_verres", [verre_de_projecteur(point, haut + 1.65 / AMA, vers_la_place) for point in rampe], MAT_VERRE_DE_LAMPE())
    repere_de_projecteur("beit_haliba", rampe[len(rampe) // 2], haut + 1.8 / AMA)
    menuiseries += [_fut(_devant(rive[0], cap, faille + s / AMA), haut, haut + 1.6 / AMA, 0.03 / AMA, 4) for s in (8, 13)]
    menuiseries += [_fut(_devant(rive[0], cap, longueur * f), haut, haut + 2.6 / AMA, 0.03 / AMA, 4) for f in (0.08, 0.3, 0.62, 0.92)]
    _poser("Beit_HaLiba_menuiseries", menuiseries, MAT_FER_BRUN())


def _plus_proches(anneau, metres):
    return min(anneau, key=lambda p: math.dist(p, vers_scene(*metres)))


def _voute(centre, cap, portee, longueur, naissance, fleche, epaisseur=0.12 / AMA, segments=8):
    """Un voile de béton en berceau surbaissé, `longueur` le long du cap, `portee` en travers."""
    dessus = _arc(0, portee / 2, naissance, fleche, segments)
    dessous = [(x * (1 - 2 * epaisseur / portee), z - epaisseur) for x, z in dessus]
    travers = (-math.sin(cap), math.cos(cap))
    return _extrusion(dessous + dessus[::-1], _devant(centre, cap, -longueur / 2), (math.cos(cap), math.sin(cap)), travers, longueur)


def pavillons_de_controle():
    """L'entrée de la porte des Ordures : deux rangées de berceaux de tôle translucide sur une
    ossature de piliers carrés et de poutres parées de pierre, sous lesquels on passe les
    portiques, sous les panneaux sombres « כניסה לגברים » et « כניסה לנשים » (les « roof » d'OSM ; leurs berceaux se comptent sur les photos, cinq à huit
    par rangée). Portée, flèche et hauteur : CHOIX."""
    voiles, ossature, panneaux = [], [], []
    naissance = Z_PLACE_HAUTE + 3.6 / AMA
    for auvent in (a for a in PAYS_DONNEES["abords_kotel"] if a["osm"] in ("w277508272", "w288016676")):
        anneau = [vers_scene(*p) for p in auvent["points"]]
        a, b = max(((p, q) for p in anneau for q in anneau), key=lambda e: math.dist(*e))
        cap, portee = _cap(a, b), 4.4 / AMA
        for s in plage(portee / 2, math.dist(a, b), portee):
            for t in (-12, -8, -4, 0, 4, 8, 12):
                centre = _devant(a, cap, s, t / AMA)
                if not _dans(centre, anneau):
                    continue
                voiles.append(_voute(centre, cap + math.pi / 2, portee, 4 / AMA, naissance, 1.0 / AMA))
                coins = [_devant(centre, cap, sa * portee / 2, st * 2 / AMA) for sa, st in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                ossature += [_pave(coin, cap, 0.55 / AMA, 0.55 / AMA, Z_PLACE_HAUTE - 0.3, naissance) for coin in coins]
                ossature += [(_poutre(c, d, naissance - 0.5 / AMA, naissance - 0.5 / AMA, 0.2 / AMA, -0.2 / AMA, 0.5 / AMA), FACES_BOITE)
                             for c, d in zip(coins, coins[1:] + coins[:1])]
                if t in (-4, 4):
                    panneaux += [_pave(_devant(centre, cap, sa * portee / 2), cap, 0.46 / AMA, 2.6 / AMA, naissance - 0.45 / AMA, naissance - 0.05 / AMA)
                                 for sa in (-1, 1)]
    _poser("Kotel_controle_voiles", voiles, MAT_TOLE())
    _poser("Kotel_controle_piles", ossature, MAT_PIERRE_DE_JERUSALEM())
    _poser("Kotel_controle_panneaux", panneaux, MAT_FER_BRUN())


def maisons_de_la_falaise(bords, etage=3.2 / AMA, pas=3.5 / AMA):
    """Au-dessus de la place, le quartier juif est bâti jusqu'au bord de la falaise : le haut de
    chaque mur de soutènement est une façade de maison, jusqu'à cinq rangs de fenêtres dans
    leurs chambranles — cintrées ou droites selon la maison, grillées une fois sur quatre, plus
    rares vers le bas —, un cordon sous chaque étage, et son pied reste un mur nu. Sur la façade, ce que les photos y
    montrent partout : la descente d'eau, des climatiseurs sous les fenêtres ; sur le toit, le
    chauffe-eau solaire, une parabole, et une pergola une fois sur deux. Pas des baies, hauteur
    d'étage et proportions : CHOIX."""
    baies, ferronneries, blancs = Percements(), [], []
    for anneau, _, _, haut in bords:
        p, q = anneau[0], anneau[1]
        longueur = math.dist(p, q)
        if haut - Z_PLACE_HAUTE < 3 * etage or longueur < pas:
            continue
        maison = f"Kotel_falaise_{p[0]:.0f}_{p[1]:.0f}"
        cintre = alea(maison, 1) < 0.6
        rangs = min(5, int((haut - Z_PLACE_HAUTE - 4.5 / AMA) / etage))
        for s in _travees(longueur, pas, 1 / AMA):
            for rang in range(1, rangs + 1):
                seuil = haut - rang * etage + 0.6 / AMA
                nom = f"{maison}_{s:.0f}_{rang}"
                if alea(nom, 2) < 0.15 * (rang - 2):
                    continue
                baies.fenetre(p, q, s, seuil, 1.1 / AMA, 1.8 / AMA, cintre, grille=alea(nom) < 0.25)
                if alea(nom, 1) < 0.22:
                    caisson, equerres = climatiseur(p, q, s + 0.2 / AMA, seuil - 1.0 / AMA)
                    blancs.append(caisson)
                    ferronneries += equerres
        baies.pierres.append(_bandeau(p, q, haut - 0.25 / AMA))
        baies.pierres += [_bandeau(p, q, haut - rang * etage - 0.1 / AMA, 0.15 / AMA, 0.05 / AMA) for rang in range(1, rangs + 1)]
        ferronneries += descente_d_eau(p, q, 0.5 / AMA, haut - (rangs + 0.6) * etage, haut)
        # En tête de falaise, la terrasse de la maison : son garde-corps, et sur le toit le
        # chauffe-eau solaire, sa cuve blanche et son panneau, une parabole.
        retrait = _a_droite(p, q, 0.2 / AMA)
        pr, qr = _decale(p, retrait), _decale(q, retrait)
        ferronneries += garde_corps([pr, qr], haut)
        for s in _travees(longueur, 9 / AMA, 3 / AMA):
            toit = _decale(_devant(p, _cap(p, q), s), _a_droite(p, q, (2 + 2 * alea(f"Kotel_falaise_cuve_{s:.0f}_{p[0]:.0f}")) / AMA))
            blancs.append(_fut(toit, haut + 0.9 / AMA, haut + 2.0 / AMA, 0.3 / AMA, 8))
            ferronneries.append((_poutre(_devant(toit, _cap(p, q), 1.5 / AMA, 0.7 / AMA), _devant(toit, _cap(p, q), 1.5 / AMA, -0.7 / AMA),
                                         haut + 0.9 / AMA, haut + 0.2 / AMA, 0.9 / AMA, -0.9 / AMA, 0.06 / AMA), FACES_BOITE))
            ferronneries += [_fut(_devant(toit, _cap(p, q), t * 0.3 / AMA), haut, haut + 0.9 / AMA, 0.025 / AMA, 4) for t in (-1, 1)]
            if alea(maison, 2 + int(s)) < 0.6:
                blancs += parabole(_devant(toit, _cap(p, q), -1.8 / AMA), haut, 2.2 + alea(maison, 300 + int(s)))
        if alea(f"Kotel_falaise_{p[0]:.0f}_{p[1]:.0f}") < 0.5 and longueur > 8 / AMA:
            cap, dedans = _cap(pr, qr), _a_droite(p, q, 3 / AMA)
            a, b = _devant(pr, cap, 1.5 / AMA), _devant(pr, cap, 6.5 / AMA)
            ferronneries += [_fut(coin, haut, haut + 2.4 / AMA, 0.05 / AMA, 4) for coin in (a, b, _decale(a, dedans), _decale(b, dedans))]
            ferronneries += [(_poutre(_devant(pr, cap, s / AMA), _decale(_devant(pr, cap, s / AMA), dedans), haut + 2.4 / AMA, haut + 2.4 / AMA,
                                      0.04 / AMA, -0.04 / AMA, 0.1 / AMA), FACES_BOITE) for s in plage(1.5, 6.5, 0.45)]
    baies.poser("Kotel_falaise", MAT_PIERRE())
    _poser("Kotel_falaise_ferronneries", ferronneries, MAT_FER_BRUN())
    _poser("Kotel_falaise_cuves", blancs, MAT_PLASTIQUE())


def mur_de_la_rampe(hauteur=6.5 / AMA):
    """Au bout sud de l'aire des femmes, passé le pont : le mur de pierre de l'ancienne rampe des
    Maghrébins et, derrière lui, ce qui reste de son remblai ; une porte cintrée et deux
    fenêtres s'y ouvrent du côté de la prière. À l'ouest, un mur bas ferme l'aire jusqu'à la
    place haute. Hauteurs : lues sur les photos."""
    nord_ouest, au_kotel, ouest = SOUS_LE_PONT[0], SOUS_LE_PONT[4], SOUS_LE_PONT[6]
    pied = Z_PLACE_KOTEL - 1
    derriere, remblai = _a_droite(ouest, au_kotel, 2 / AMA), _a_droite(ouest, au_kotel, 11 / AMA)
    mur = [ouest, au_kotel, _decale(au_kotel, derriere), _decale(ouest, derriere)]
    retour = [nord_ouest, ouest, _decale(ouest, _a_droite(nord_ouest, ouest, 0.6 / AMA)), _decale(nord_ouest, _a_droite(nord_ouest, ouest, 0.6 / AMA))]
    volumes("Kotel_rampe_mur", [(_direct(mur), [], pied, Z_PLACE_KOTEL + hauteur), (_direct(retour), [], pied, Z_PLACE_KOTEL + 3 / AMA)],
            "00_HarHabayit", MAT_MURAILLE())
    talus = [_decale(ouest, derriere), _decale(au_kotel, derriere), _decale(au_kotel, remblai), _decale(ouest, remblai)]
    volumes("Kotel_rampe_remblai", [(_direct(talus), [], pied, Z_PLACE_KOTEL + hauteur - 1.5 / AMA)], "00_HarHabayit", MAT_TERRE())
    long_ = math.dist(ouest, au_kotel)
    baies = Percements()
    baies.porte(ouest, au_kotel, long_ * 0.3, Z_PLACE_KOTEL, 1.6 / AMA, 2.6 / AMA, cintre=True)
    for f in (0.55, 0.8):
        baies.fenetre(ouest, au_kotel, long_ * f, Z_PLACE_KOTEL + 3.4 / AMA, 0.9 / AMA, 1.5 / AMA, grille=True)
    baies.poser("Kotel_rampe", MAT_PIERRE())


def aish_hatorah(anneau):
    """Le centre mondial d'Aish HaTorah, face au Kotel au-dessus de la place : une forteresse de
    pierre bossagée de sept niveaux, des tourelles d'angle sous leur tablette, des cordons et des
    rangs de baies cintrées jumelles dans leurs chambranles. Sa hauteur et le pas de ses baies : lus sur la photo de 2019."""
    pied, haut = Z_PLACE_KOTEL - 1, Z_PLACE_HAUTE + H_AISH_HATORAH
    volumes("Aish_HaTorah", [(anneau, [], pied, haut)], "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    # OSM arrête son emprise à quinze mètres de la place, que sa façade domine pourtant d'aplomb : le
    # relief du modèle met la falaise entre les deux. Son corps avant est donc ramené au bord de la falaise.
    proue = max(anneau, key=lambda point: point[0])
    bord = _plus_proche_sur_l_anneau(proue, CUVETTE_KOTEL)
    avance = (bord[0] - proue[0] + 0.6 / AMA, bord[1] - proue[1])
    anneau = _direct([_decale(point, avance) for point in anneau])
    volumes("Aish_HaTorah_corps_avant", [(anneau, [], pied, haut)], "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    baies, tourelles = Percements(), []
    for p, q in zip(anneau, anneau[1:] + anneau[:1]):
        longueur = math.dist(p, q)
        if longueur < 5 / AMA:
            continue
        for s in _travees(longueur, 4.5 / AMA, 2 / AMA):
            for niveau in (9, 13, 17, 21):
                baies.jumelles(q, p, longueur - s, Z_PLACE_HAUTE + niveau / AMA, 0.75 / AMA, 2.1 / AMA)
        baies.pierres += [_bandeau(q, p, Z_PLACE_HAUTE + h / AMA, 0.2 / AMA, 0.06 / AMA) for h in (7.6, 15.9)]
        baies.pierres.append(_bandeau(q, p, haut - 0.4 / AMA, 0.4 / AMA, 0.12 / AMA))
    for coin in sorted(anneau, key=lambda point: point[0], reverse=True)[:3]:
        cx, cy = sum(x for x, _ in anneau) / len(anneau), sum(y for _, y in anneau) / len(anneau)
        centre = _devant(coin, _cap(coin, (cx, cy)), 2.2 / AMA)
        tourelles.append(_pave(centre, 0, 5 / AMA, 5 / AMA, haut - 1, haut + 3.5 / AMA))
        tourelles.append(_pave(centre, 0, 5.3 / AMA, 5.3 / AMA, haut + 3.5 / AMA, haut + 3.8 / AMA))
    baies.poser("Aish_HaTorah", MAT_PIERRE())
    _poser("Aish_HaTorah_tourelles", tourelles, MAT_PIERRE_DE_JERUSALEM())
    _poser("Aish_HaTorah_garde_corps", garde_corps(anneau + anneau[:1], haut), MAT_FER())


def facades_du_kotel(bords):
    mur_de_la_rampe()
    maisons_de_la_falaise(bords)
    makhkama()
    toits_du_nord()
    arcades_du_nord()
    batiment_de_la_fondation()
    pavillons_de_controle()
