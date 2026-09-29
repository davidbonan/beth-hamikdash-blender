import bpy
import json
from mathutils import Vector

from .parametres import RACINE
from .noeuds import _creuser, _noeud
from .matieres import MAT_OR_PLAQUE
from .volumes import mesh_from_pydata


# --- Relief d'une paroi -------------------------------------------------------------
# « פִּתּוּחֵי מִקְלְעוֹת » (Melakhim I 6:29), et « וְצִפָּה זָהָב מְיֻשָּׁר עַל־הַמְּחֻקֶּה » (6:35) :
# la figure est creusée, et l'or épouse le creusé. Une paroi se donne en (axe le long
# duquel court `u`, cote de la face, sens de la saillie) ; tout ce qui suit se trace
# dans le plan (u, z) de cette paroi et sort d'elle.

def _repere(paroi):
    """(point(u, z, saillie), direction de u, normale sortante) d'une paroi."""
    axe, c, sens = paroi
    if axe == "x":
        return (lambda u, z, d: Vector((u, c + sens * d, z))), Vector((1, 0, 0)), Vector((0, sens, 0))
    return (lambda u, z, d: Vector((c + sens * d, u, z))), Vector((0, 1, 0)), Vector((sens, 0, 0))


def _contour_oriente(paroi, contour, uv):
    """Les points du contour sur le nu de la paroi, tournés dans le sens direct vu du
    dehors, avec leurs `uv` et la normale sortante. Le contour a le droit d'être
    concave — l'orientation se prend sur l'aire entière, qu'un test au premier sommet
    donnerait à l'envers sur une corolle."""
    point, _, normale = _repere(paroi)
    nu = [point(u, z, 0.0) for u, z in contour]
    aire = Vector((0.0, 0.0, 0.0))
    for k in range(1, len(nu) - 1):
        aire += (nu[k] - nu[0]).cross(nu[k + 1] - nu[0])
    if aire.dot(normale) < 0:
        return nu[::-1], uv and uv[::-1], normale
    return nu, uv, normale


def _relief_profil(nom, paroi, contour, d0, d1, col, mat=None, uv=None):
    """Un contour libre tracé dans le plan de la paroi, sorti d'elle de `d0` à `d1`,
    `uv` (une coordonnée par point du contour) allant aux deux faces.

    Une silhouette d'un seul tenant, et non un assemblage de plaques rectangulaires :
    c'est le contour qui fait lire la figure, et c'est lui que la passe Normal donne au
    styliseur.
    """
    nu, uv, normale = _contour_oriente(paroi, contour, uv)
    n = len(nu)
    verts = [tuple(p + normale * d0) for p in nu] + [tuple(p + normale * d1) for p in nu]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    return mesh_from_pydata(nom, verts, faces, col, mat or MAT_OR_PLAQUE(), uv and uv + uv)


# Chaque taille laisse ici son contour ; `creuser_les_parois` en ouvre le trou dans ce
# qui la porte, une fois la scène bâtie.
_TAILLES = []


def _taille_profil(nom, paroi, contour, profondeur, col, mat=None, uv=None):
    """Un contour taillé DANS la paroi : le fond à `profondeur` sous le nu, et les flancs
    qui y descendent, tournés vers la figure. Pas de dessus — c'est le trou que
    `creuser_les_parois` ouvre dans le support."""
    nu, uv, normale = _contour_oriente(paroi, contour, uv)
    n = len(nu)
    verts = [tuple(p - normale * profondeur) for p in nu] + [tuple(p) for p in nu]
    faces = [list(range(n))]
    faces += [[n + k, n + (k + 1) % n, (k + 1) % n, k] for k in range(n)]
    o = mesh_from_pydata(nom, verts, faces, col, mat or MAT_OR_PLAQUE(), uv and uv + uv)
    o["taille"] = True
    _TAILLES.append((paroi, contour, profondeur))
    return o


def _saillie_profil(nom, paroi, contour, saillie, col, mat=None, uv=None):
    """Un contour qui SORT de la paroi de `saillie`, son dos assis de ASSISE_KIR dans le
    placage. Rien à ouvrir dans le support : la plaque est posée dessus."""
    return _relief_profil(nom, paroi, contour, -ASSISE_KIR, saillie, col, mat, uv)


def _sens_direct(paroi):
    """+1 si un contour tracé dans le sens trigonométrique du plan (u, z) regarde déjà le
    dehors de la paroi, −1 s'il faut le retourner."""
    point, _, normale = _repere(paroi)
    origine = point(0.0, 0.0, 0.0)
    aire = (point(1.0, 0.0, 0.0) - origine).cross(point(0.0, 1.0, 0.0) - origine)
    return 1 if aire.dot(normale) > 0 else -1


def _bande_saillante(nom, paroi, motif, cadre, saillie, col, allonge=1.0):
    """Une bande d'or qui sort de `saillie`, dont le dessus reparcourt la tuile de `motif`
    le long de son plus grand côté, et ses flancs jusqu'au pied assis dans le placage.
    `allonge` : longueur d'une tuile posée, en part de la largeur de la bande.

    Une figure isolée vaut une plaque ; un cordon qui court sur quarante amot en vaudrait
    des centaines. La bande n'en fait qu'UNE, et son dessus est un ruban de quadrilatères
    qui reprennent chacun la tuile entière — les sommets se dédoublent à chaque couture,
    une UV ne sachant pas sauter au milieu d'une face.

    Le motif doit se refermer sur son carré : `corde`, `tresse` et `panneau` sont dessinés,
    et non taillés par un modèle, exactement pour ça (`beit_hamikdash_gravures.py`).
    """
    (u0, z0), (u1, z1) = cadre
    fiche = GRAVURES[motif]
    mu0, mz0, mu1, _ = fiche["cadre"]
    ou, ov, tuile = fiche["tuile"]
    etendue = mu1 - mu0
    point, _, normale = _repere(paroi)
    sens = _sens_direct(paroi)
    horizontal = abs(u1 - u0) >= abs(z1 - z0)
    (l0, l1), (c0, c1) = ((u0, u1), (z0, z1)) if horizontal else ((z0, z1), (u0, u1))
    n = max(1, round(abs(l1 - l0) / (abs(c1 - c0) * allonge)))
    pas = (l1 - l0) / n
    verts, faces, uv = [], [], []
    coins_motif = [(mu0, mz0), (mu1, mz0), (mu1, mz0 + etendue), (mu0, mz0 + etendue)]

    def poser(coins, sortie):
        base = len(verts)
        ordre = range(4) if sens > 0 else range(3, -1, -1)
        for k in ordre:
            u, z = coins[k]
            verts.append(tuple(point(u, z, 0.0) + normale * sortie))
            du, dz = coins_motif[k]
            uv.append((ou + tuile * (du - mu0) / etendue, ov + tuile * (dz - mz0) / etendue))
        return base

    for k in range(n):
        a, b = l0 + pas * k, l0 + pas * (k + 1)
        long_court = [(a, c0), (b, c0), (b, c1), (a, c1)]
        base = poser(long_court if horizontal else [(c, l) for l, c in long_court], saillie)
        faces.append([base + i for i in range(4)])
    contour = [(u0, z0), (u1, z0), (u1, z1), (u0, z1)]
    haut = poser(contour, saillie)
    poser(contour, -ASSISE_KIR)
    faces += [[haut + k, haut + (k + 1) % 4, haut + 4 + (k + 1) % 4, haut + 4 + k]
              for k in range(4)]
    o = mesh_from_pydata(nom, verts, faces, col, matiere_gravee(MAT_OR_PLAQUE()), uv)
    # Un chanfrein sur une bande de quarante amot en mangerait le cordon et dédoublerait
    # chaque couture : ce sont ses deux longs bords qui la dessinent, pas son biseau.
    o["sans_biseau"] = True
    return o


# --- Les trois figures gravées du Bayit, et le palmier de tous ses jambages :
#     « כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » (Melakhim I 6:29 pour les parois, 6:32 et 6:35
#     pour les vantaux). Ye'hezkel 41:18-19 donne l'ORDRE dans lequel elles alternent —
#     « וְתִמֹרָה בֵּין כְּרוּב לִכְרוּב, וּשְׁנַיִם פָּנִים לַכְּרוּב », chaque profil tourné vers la
#     timora qui le jouxte.
#     Au Bayit la timora est une palmette en éventail ; sur les jambages, « וְתִמֹרִים
#     אֶל־אֵילָיו, אֶחָד מִפּוֹ וְאֶחָד מִפּוֹ » (Ye'hezkel 40:26, 31, 34, 37), le chapiteau que
#     Rashi y lit, « כּוֹתֶרֶת, דּוֹמֶה לְדֶקֶל » (40:16) — le seul ornement que les sources
#     donnent aux baies des cours.
#
#     Une figure est UNE plaque à sa silhouette, et son modelé — corps qui bombe, pennes
#     séparées d'un sillon, palmes qui ploient — est une carte de hauteur que la plaque
#     lit par ses UV : `beit_hamikdash_gravures.py` écrit la carte et les silhouettes,
#     tracées sur la carte même. Des plaques empilées, aussi bien découpées fussent-elles,
#     se lisaient en emporte-pièce : seul le chanfrein prenait la lumière.
# Le bandeau porte un cordon ET les rosettes enfilées dessus (`bandeau_guirlande`) : à
# 0,55 ama les deux se disputaient la même ligne et le cordon sortait en filet sale.
BANDEAU_KIR = 0.8         # hauteur d'un bandeau, en amot
# Sur la pierre — jambages, frise de la gezuztra — la figure est TAILLÉE, rien n'en sort :
# son modelé bombe au fond de la taille, et c'est le flanc tourné vers elle qui en trace
# le contour. 3,4 cm. À 0,05 le contour rendait une ligne d'ombre de 2,5 cm à quinze
# mètres, et la figure se lisait imprimée plutôt que taillée.
# Conséquence à connaître, non une borne : 0,07 < EPAISSEUR_PLACAGE (0,1), donc une taille
# dans l'or n'atteint pas le mur porteur ; au-delà son booléen y mordrait, et changerait
# ce que `separer_collees` voit à 2 cm derrière les faces voisines.
PROFONDEUR_KIR = 0.07
# Sur l'or du Bayit, parois et vantaux, la figure SORT de la plaque : « שׁוֹקֵעַ בִּמְקוֹם
# שִׁקּוּעוֹ, וּבוֹלֵט בִּמְקוֹם בְּלִיטָתוֹ » (Rashi sur Melakhim I 6:35). 4,8 cm, et le modelé
# par-dessus. La plaque s'ASSIED dans le placage : un dos au nu même de l'or y clignoterait.
SAILLIE_KIR = 0.10
ASSISE_KIR = 0.02
# Le pas d'un keruv à la palmette voisine, en amot : 8 pas sur les 40 amot du Heikhal —
# sept figures par rang, un pas de marge pour les montants —, et le Kodesh HaKodashim prend
# le même, pour que ses keruvim aient la taille de ceux du Heikhal. Les figures font la
# hauteur du registre, 9,4 amot, et leurs silhouettes s'emboîtent à ce pas à 5 cm près
# (`emboitement`). À un seul registre, le Kodesh HaKodashim ne tenait plus qu'un keruv par
# paroi, sans la timora que Ye'hezkel 41:18 met entre deux.
PAS_KIR = 40 / 8
PAS_FLEURON = 3.7         # pas d'un fleuron dans un bandeau, en amot
GRAVURES_JSON = RACINE / "visite" / "matieres" / "gravures.json"
MODELE_GRAVURE = 0.09     # amot : ce dont le modelé bombe par-dessus la plaque, 4,3 cm sur un
                          # keruv de paroi. La visite le prend en part de la hauteur de la
                          # figure (matieres.js, RELIEF_GRAVURE) ; ici c'est le keruv qui règle.


def _lire_gravures():
    try:
        return json.loads(GRAVURES_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"{GRAVURES_JSON.name} absent : lancer beit_hamikdash_gravures.py d'abord.")


FICHE_GRAVURES = _lire_gravures()
GRAVURES = FICHE_GRAVURES["motifs"]
# L'atlas porte sa taille dans sa fiche : un nom de fichier en dur mentait dès que
# `beit_hamikdash_gravures.py` changeait de grille.
CARTE_GRAVURES = GRAVURES_JSON.with_name(f"gravures_{FICHE_GRAVURES['pixels']}.webp")
_GRAVEES = {}


def matiere_gravee(mat):
    """La même matière, qui lit en plus la carte des gravures par les UV de la plaque.

    Une copie nommée `<matière>_grave`, une par matière et par exécution — comme les
    matières de `_neuf`, la copie d'une exécution précédente est jetée, sans quoi le
    .blend figerait la première version. La visite retrouve la famille au nom de base.
    """
    nom = f"{mat.name}_grave"
    if nom in _GRAVEES:
        return _GRAVEES[nom]
    ancien = bpy.data.materials.get(nom)
    if ancien is not None:
        bpy.data.materials.remove(ancien)
    copie = mat.copy()
    copie.name = nom
    uv = _noeud(copie, "ShaderNodeUVMap", -1500, 900)
    carte = _noeud(copie, "ShaderNodeTexImage", -1200, 900)
    carte.image = bpy.data.images.load(str(CARTE_GRAVURES), check_existing=True)
    carte.image.colorspace_settings.name = "Non-Color"
    carte.image.alpha_mode = "CHANNEL_PACKED"
    carte.extension = "EXTEND"
    copie.node_tree.links.new(uv.outputs["UV"], carte.inputs["Vector"])
    _creuser(copie, carte.outputs["Color"], 1.0, MODELE_GRAVURE)
    _GRAVEES[nom] = copie
    return copie


def _silhouette_posee(motif, u, z0, h):
    """Le contour du motif posé en (u, z0) à la hauteur `h`, et l'UV de chaque sommet dans
    sa tuile de l'atlas."""
    fiche = GRAVURES[motif]
    u0, z_bas, u1, _ = fiche["cadre"]
    ou, ov, taille = fiche["tuile"]
    cadre = u1 - u0
    contour = [(u + du * h, z0 + dz * h) for du, dz in fiche["silhouette"]]
    uv = [(ou + taille * (du - u0) / cadre, ov + taille * (dz - z_bas) / cadre)
          for du, dz in fiche["silhouette"]]
    return contour, uv


def _relief_grave(nom, paroi, motif, u, z0, h, col, mat=None):
    """La taille d'une figure gravée : sa silhouette, enfoncée de PROFONDEUR_KIR."""
    contour, uv = _silhouette_posee(motif, u, z0, h)
    return _taille_profil(nom, paroi, contour, PROFONDEUR_KIR, col, matiere_gravee(mat or MAT_OR_PLAQUE()), uv)


def _relief_saillant(nom, paroi, motif, u, z0, h, col):
    """Une figure sur l'or du Bayit : sa plaque sort de SAILLIE_KIR, et son modelé bombe
    par-dessus."""
    contour, uv = _silhouette_posee(motif, u, z0, h)
    return _saillie_profil(nom, paroi, contour, SAILLIE_KIR, col, matiere_gravee(MAT_OR_PLAQUE()), uv)


def _etendue_a(silhouette, z):
    """Les abscisses extrêmes où la ligne de hauteur `z` coupe la silhouette."""
    coupes = [ua + (ub - ua) * (z - za) / (zb - za)
              for (ua, za), (ub, zb) in zip(silhouette, silhouette[1:] + silhouette[:1])
              if za != zb and min(za, zb) <= z <= max(za, zb)]
    return (min(coupes), max(coupes)) if coupes else None


def emboitement(motif_a, motif_b):
    """Le pas, en part de la hauteur commune, sous lequel deux figures voisines se
    mordent, lu hauteur par hauteur des deux côtés. Les boîtes des silhouettes ne
    s'emboîtent pas là où les ailes et les palmes, elles, s'emboîtent : les ailes du
    keruv sont larges en haut, la palmette au milieu."""
    a, b = GRAVURES[motif_a]["silhouette"], GRAVURES[motif_b]["silhouette"]
    pire = 0.0
    for k in range(1001):
        ea, eb = _etendue_a(a, k / 1000), _etendue_a(b, k / 1000)
        if ea and eb:
            pire = max(pire, ea[1] - eb[0], eb[1] - ea[0])
    return pire


def largeur_gravure(motif):
    """Largeur de la figure, en part de sa hauteur, lue sur sa silhouette dans l'atlas."""
    us = [du for du, _ in GRAVURES[motif]["silhouette"]]
    zs = [dz for _, dz in GRAVURES[motif]["silhouette"]]
    return (max(us) - min(us)) / (max(zs) - min(zs))


def timora(nom, paroi, u, z0, h, col, mat=None):
    """« תִּמֹרָה » d'un jambage : sept palmes en fontaine sur une base en cloche —
    « כּוֹתֶרֶת, דּוֹמֶה לְדֶקֶל » (Rashi sur Ye'hezkel 40:16) —, taillée dans la pierre d'une
    porte du Har HaBayit, que nulle source ne dore (`beit_hamikdash_gravures.py`)."""
    return _relief_grave(nom, paroi, "timora", u, z0, h, col, mat)


def palmette(nom, paroi, u, z0, h, col):
    """« תִּמֹרָה » du Bayit, entre deux keruvim sur les parois et les vantaux — « וּפְנֵי
    אָדָם אֶל־הַתִּמֹרָה » (Ye'hezkel 41:18-19), et le keruv y tourne ses faces : une palme
    stylisée, un grand éventail de palmes étagées sur une base cerclée, aussi riche que
    les ailes qui l'encadrent."""
    return _relief_saillant(nom, paroi, "palmette", u, z0, h, col)


def keruv(nom, paroi, u, z0, h, col):
    """« כְּרוּבִים » — la 'haya de la vision, « וָאֵדַע כִּי כְרוּבִים הֵמָּה » (Ye'hezkel 10:20) :
    deux immenses ailes levées à rangs de plumes étagés, deux qui couvrent le corps, les
    mains dessous, une jambe droite au sabot de veau (1:7-11), et une petite tête à deux
    faces, le lion et l'homme sans traits, chacune vers la palmette qui le jouxte (41:19)."""
    return _relief_saillant(nom, paroi, "keruv", u, z0, h, col)


def petur_tzitz(nom, paroi, u, z, r, col, mat=None):
    """« פְּטוּרֵי צִצִּים » : la fleur épanouie, de rayon `r` autour de (u, z), taillée. Sans
    chanfrein : 3 cm de biseau sur 22 cm de corolle en mangeaient le pétale, et le
    dédoublaient en sommets par centaines de fleurons."""
    o = _relief_grave(nom, paroi, "fleuron", u, z - r, 2 * r, col, mat)
    o["sans_biseau"] = True
    return o


def fleur_de_guirlande(nom, paroi, u, z, r, col):
    """La même fleur, enfilée en saillie sur le cordon d'une guirlande du Bayit."""
    o = _relief_saillant(nom, paroi, "fleuron", u, z - r, 2 * r, col)
    o["sans_biseau"] = True
    return o


# Les deux traits d'un bandeau, en amot au-dessus de son bas : entre le bord et ce que
# le bandeau porte, qui en laisse de quoi ne pas le toucher — deux tailles qui se
# touchent ne font plus qu'un trou.
TRAITS_BANDEAU = ((0.014, 0.042), (BANDEAU_KIR - 0.042, BANDEAU_KIR - 0.014))


def bandeau_fleurons(nom, paroi, u0, u1, z, col, mat=None):
    """Un bandeau de fleurons isolés, celui de la frise de la gezuztra : une corolle tous
    les PAS_FLEURON, bordée de deux traits taillés. Les parois du Bayit, elles, portent
    la guirlande (`bandeau_guirlande`) : le Targum y lit un cordon, pas des fleurs
    posées seules."""
    for bord, (zb, zh) in enumerate(TRAITS_BANDEAU):
        _taille_profil(f"{nom}_trait_{bord}", paroi,
                       [(u0, z + zb), (u1, z + zb), (u1, z + zh), (u0, z + zh)],
                       PROFONDEUR_KIR * 0.4, col, mat)
    n = max(1, round((u1 - u0) / PAS_FLEURON))
    pas = (u1 - u0) / n
    for i in range(n):
        petur_tzitz(f"{nom}_fleuron_{i:02d}", paroi, u0 + pas * (i + 0.5), z + BANDEAU_KIR / 2,
                    BANDEAU_KIR * 0.42, col, mat)


# La guirlande de l'image validée : un gros cordon qui tient presque toute la hauteur du
# bandeau entre deux filets plats, et des rosettes enfilées au milieu du cordon. En amot
# au-dessus du bas du bandeau. Un cordon d'un tiers de bandeau, des fleurs debout dessus et
# des filets d'un centimètre se lisaient en rang d'objets posés, non en corde.
FILET_GUIRLANDE = 0.07
CORDON_GUIRLANDE = (0.13, BANDEAU_KIR - 0.13)
RAYON_ROSETTE = 0.36
# Une torsion par diamètre de corde, la tuile de `corde` en portant deux : sur une tuile
# carrée les mèches tombaient au demi-diamètre et le cordon sortait en hachures.
ALLONGE_CORDE = 2.0
# Une rosette sous chaque figure et une à chaque point où deux figures se touchent : c'est
# le pas des figures qui règle celui des fleurs, et le cordon se lit avec la file.
PAS_ROSETTE = PAS_KIR / 2


def rosettes_regulieres(u0, u1):
    """Les rosettes d'un bandeau qui ne porte pas de file de figures : au pas le plus
    proche de PAS_ROSETTE, centrées."""
    n = max(1, round(abs(u1 - u0) / PAS_ROSETTE))
    pas = (u1 - u0) / n
    return [u0 + pas * (i + 0.5) for i in range(n)]


def bandeau_guirlande(nom, paroi, u0, u1, z, col, rosettes=None):
    """« פְּטוּרֵי צִצִּים » tel que le Targum le lit : « אָטוּנִין שׁוֹשַׁנִין », des cordes de
    fleurs, et Rashi le décompose sur 6:18 — « פְּטוּרֵי לְשׁוֹן חֲבָלִים … צִצִּים לְשׁוֹן
    פְּרָחִים », « צוּרַת שַׁלְשְׁלָאוֹת ». Le bandeau est donc un CORDON qui court, et des fleurs
    enfilées dessus, en `rosettes` (abscisses) ou au pas régulier.

    C'est le cordon, et lui seul, qui tient les figures : elles posent le pied sur le
    filet du haut et touchent de la tête celui du bandeau suivant (`figure_du_registre`).
    """
    for bord, (zb, zh) in enumerate(((0.0, FILET_GUIRLANDE),
                                      (BANDEAU_KIR - FILET_GUIRLANDE, BANDEAU_KIR))):
        _saillie_profil(f"{nom}_trait_{bord}", paroi,
                        [(u0, z + zb), (u1, z + zb), (u1, z + zh), (u0, z + zh)],
                        SAILLIE_KIR * 0.4, col)
    bas, haut = CORDON_GUIRLANDE
    _bande_saillante(f"{nom}_cordon", paroi, "corde", ((u0, z + bas), (u1, z + haut)),
                     SAILLIE_KIR * 0.7, col, ALLONGE_CORDE)
    for i, u in enumerate(rosettes_regulieres(u0, u1) if rosettes is None else rosettes):
        fleur_de_guirlande(f"{nom}_fleur_{i:02d}", paroi, u, z + BANDEAU_KIR / 2, RAYON_ROSETTE, col)


def figure_du_registre(z, registre):
    """Pied et hauteur d'une figure du registre qui commence en `z` : de la moitié du filet
    du bandeau d'en bas à la moitié du filet de celui d'en haut. Une figure qui flotte
    entre deux bandeaux se lit posée au hasard sur l'or ; c'est le contact qui fait scène."""
    return z + BANDEAU_KIR - FILET_GUIRLANDE / 2, registre - BANDEAU_KIR + FILET_GUIRLANDE


REGISTRES_VANTAIL = 3     # figures empilées sur un vantail : « תמרה בין כרוב לכרוב »


def vantail_sculpte(nom, paroi, u0, u1, z0, z1, col):
    """« כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » sur un vantail, et de l'or par-dessus la taille —
    « וְצִפָּה זָהָב מְיֻשָּׁר עַל הַמְּחֻקֶּה » (Melakhim I 6:32 et 6:35). Ye'hezkel 41:25 le redit
    des portes du Heikhal, « כַּאֲשֶׁר עֲשׂוּיִם לַקִּירוֹת » : les mêmes figures que les parois.

    Un vantail est haut et étroit là où une paroi est large : la file de figures y monte
    au lieu de courir. Ce qui tient, c'est l'ALTERNANCE — « וְתִמֹרָה בֵּין כְּרוּב לִכְרוּב »
    (Ye'hezkel 41:18), une timora entre deux keruvim, quel que soit le sens de la file.
    Et c'est la figure DES PAROIS : « כַּאֲשֶׁר עֲשׂוּיִם לַקִּירוֹת » (41:25) — les vantaux
    portent ce que portent les murs.
    """
    registre = (z1 - z0 - BANDEAU_KIR) / REGISTRES_VANTAIL
    _, h = figure_du_registre(z0, registre)
    assert h * largeur_gravure("keruv") <= abs(u1 - u0), f"keruv de {h:.2f} amot sur un vantail de {abs(u1 - u0):.2f}"
    for r in range(REGISTRES_VANTAIL + 1):
        bandeau_guirlande(f"{nom}_{r}", paroi, u0, u1, z0 + r * registre, col, [(u0 + u1) / 2])
    for r in range(REGISTRES_VANTAIL):
        motif = keruv if r % 2 == 0 else palmette
        pied, _ = figure_du_registre(z0 + r * registre, registre)
        motif(f"{nom}_{r}", paroi, (u0 + u1) / 2, pied, h, col)
