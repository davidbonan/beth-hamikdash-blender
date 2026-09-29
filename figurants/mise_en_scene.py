import math
from typing import NamedTuple

import bpy
import numpy as np
from mathutils import Matrix, Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA

from .maillage import TOUR, Maillage
from .habillage import lier, materiau_de
from .ustensiles import RAYON_GIZRA, sefer


# `repere` : place au repos de l'objet, en repère d'armature.
def tenir(h, nom, construire, os_, repere):
    mm = Maillage()
    construire(mm, repere)
    return lier(h, mm, f"{h.nom}_{nom}", materiau_de(mm), os_)


def repere_vers(origine, z, x):
    z = z.normalized()
    x = (x - z * x.dot(z)).normalized()
    m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
    m.translation = origine
    return m


IMAGES = 15
BAS = Vector((0.0, 0.0, -1.0))


# `z_haut` : au-dessus du plus haut sol du trajet, sous tout toit.
def _rayon_sol(x, y, z_haut):
    scene = bpy.context.scene
    touche, lieu, *_ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((x, y, z_haut + 1.5)), BAS,
                                      distance=8.0)
    return lieu.z if touche else z_haut


# Relevé avant de poser les figures : un rayon tiré ensuite toucherait les corps.
class Terrain:
    def __init__(self, x0, x1, y0, y1, z_haut, pas=0.1):
        self.x0, self.y0, self.pas = x0, y0, pas
        nx, ny = int((x1 - x0) / pas) + 2, int((y1 - y0) / pas) + 2
        self.z = np.array([[_rayon_sol(x0 + i * pas, y0 + j * pas, z_haut) for j in range(ny)] for i in range(nx)])

    def __call__(self, x, y):
        u = min(max((x - self.x0) / self.pas, 0.0), self.z.shape[0] - 1.001)
        v = min(max((y - self.y0) / self.pas, 0.0), self.z.shape[1] - 1.001)
        i, j = int(u), int(v)
        fu, fv = u - i, v - j
        z = self.z
        return ((z[i, j] * (1 - fu) + z[i + 1, j] * fu) * (1 - fv) + (z[i, j + 1] * (1 - fu) + z[i + 1, j + 1] * fu) * fv)


# En amot : aller-retour de `a` à `b`, demi-tours de `rayon` aux deux bouts ; l'aller se fait à gauche de `a` → `b`, ou à droite avec `sens=-1`.
class Stade:
    def __init__(self, a, b, rayon, pas=0.04, sens=1):
        a, b, r = Vector(a) * AMA, Vector(b) * AMA, rayon * AMA
        d = (b - a).normalized()
        n = Vector((-d.y, d.x)) * sens
        droit = (b - a).length
        k, m = max(2, int(droit / pas)), max(8, int(math.pi * r / pas))
        points = [a + n * r + d * (droit * i / k) for i in range(k)]
        points += [b + n * (r * math.cos(math.pi * i / m)) + d * (r * math.sin(math.pi * i / m)) for i in range(m)]
        points += [b - n * r - d * (droit * i / k) for i in range(k)]
        points += [a - n * (r * math.cos(math.pi * i / m)) - d * (r * math.sin(math.pi * i / m)) for i in range(m)]
        self.points = points
        self.cumul = [0.0]
        for p, q in zip(points, points[1:] + points[:1]):
            self.cumul.append(self.cumul[-1] + (q - p).length)
        self.longueur = self.cumul[-1]

    def en(self, s):
        s %= self.longueur
        i = max(0, np.searchsorted(self.cumul, s, side="right") - 1)
        p, q = self.points[i], self.points[(i + 1) % len(self.points)]
        t = (s - self.cumul[i]) / max(self.cumul[i + 1] - self.cumul[i], 1e-9)
        return p.lerp(q, t)

    def direction(self, s):
        return (self.en(s + 0.25) - self.en(s - 0.25)).normalized()

    def bornes(self, marge):
        xs, ys = [p.x for p in self.points], [p.y for p in self.points]
        return min(xs) - marge, max(xs) + marge, min(ys) - marge, max(ys) + marge


def placement(x, y, z, direction, sol_local):
    return Matrix.Translation((x, y, z - sol_local)) @ Matrix.Rotation(math.atan2(direction.x, -direction.y), 4, "Z")


def cap_vers(cap):
    return Vector((math.cos(math.radians(cap)), math.sin(math.radians(cap))))


BATTEMENT = 60.0 / 72.0
MESURES = 16


def devant_poitrine(h, avance, sous_epaule, ecart=0.0):
    return Vector((ecart, -avance, h.z_epaule - sous_epaule))


# « מַנִּיחַ יָדוֹ הַיְמָנִית עַל גַּבֵּי רַגְלוֹ הַיְמָנִית … וְשׁוֹחֶה וּמְקַדֵּשׁ » (Rambam Bi'at HaMikdash 5:16).
def lavage(h, a, horloge, t):
    u = t / horloge.duree
    w = G.lisse((u - 0.22) / 0.14) * (1.0 - G.lisse((u - 0.68) / 0.14))
    frotte = 0.015 * horloge.onde(t, 0.9) * w

    def main(cote):
        pendante = a.au("spine_03", a.poignet[cote])
        pied = a.cheville[cote] + G.DEVANT * (0.07 + frotte) + G.HAUT * 0.055
        return lambda poses: pendante(poses).lerp(pied, w)

    return G.composer(G.debout(a, horloge, t, regard=0.04 * (1 - w)),
                      G.bassin(Vector((0.0, 0.17 * w, -0.25 * w)), tangage=0.45 * w),
                      G.buste(flexion=0.78 * w), G.tete(flexion=-0.22 * w),
                      G.bras(a, "l", main("l")), G.bras(a, "r", main("r")),
                      G.doigts(a, "l", 0.35 - 0.25 * w), G.doigts(a, "r", 0.35 - 0.25 * w))


def repere_mizrak(h):
    return repere_vers(devant_poitrine(h, 0.30, 0.34), G.HAUT, G.GAUCHE)


# La coupe tenue à deux mains, à `ecart` de son axe, que le buste penche en avant et relève.
def incliner_la_coupe(ecart):
    def geste(h, a, horloge, t):
        coupe = a.repere("spine_03", repere_mizrak(h))
        incline = 0.5 - 0.5 * horloge.onde(t, 8.0, 0.25)
        return G.composer(G.debout(a, horloge, t, 0.2, regard=0.05), G.buste(flexion=0.18 * incline),
                          G.tete(flexion=0.20 * incline),
                          G.bras(a, "l", lambda poses: coupe(poses) @ Vector((ecart, 0.0, 0.03))),
                          G.bras(a, "r", lambda poses: coupe(poses) @ Vector((-ecart, 0.0, 0.03))),
                          G.paume(a, "l", lambda poses: G.HAUT - G.GAUCHE), G.paume(a, "r", lambda poses: G.HAUT + G.GAUCHE),
                          G.doigts(a, "l", 0.25), G.doigts(a, "r", 0.25))
    return geste


zerika = incliner_la_coupe(0.11)


# Calé contre le ventre, la tête penchée en avant : tenu à bout de bras, il tendait les bras comme deux perches.
def repere_kinor(h, echelle):
    base = Vector((0.05, -0.17 - 0.04 * (echelle - 1.0), h.z_epaule - 0.46 * echelle))
    return repere_vers(base, Vector((0.12, -0.42, 1.0)), Vector((1.0, 0.0, -0.1)))


# La gauche tient le montant par-derrière, la droite pince les cordes devant, à mi-hauteur.
def jouer_kinor(h, a, horloge, t, echelle, retard):
    lyre = a.repere("spine_03", repere_kinor(h, echelle))
    b = (t / BATTEMENT - retard) % 1.0
    geste = G.lisse(b / 0.30) if b < 0.30 else 1.0 - G.lisse((b - 0.30) / 0.70)
    e = echelle
    return G.composer(G.debout(a, horloge, t, retard, regard=0.03), G.balancement(t, BATTEMENT, retard=retard),
                      G.tete(flexion=0.12),
                      G.bras(a, "l", lambda poses: lyre(poses) @ Vector((0.15 * e, 0.035, 0.30 * e))),
                      G.bras(a, "r", lambda poses: lyre(poses) @ Vector(((-0.04 + 0.10 * geste) * e, -0.07, 0.22 * e))),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, G.DEVANT - G.GAUCHE * 0.3)),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.HAUT * 0.3 + G.GAUCHE)),
                      G.doigts(a, "l", 0.45, 0.3), G.doigts(a, "r", 0.35 + 0.35 * geste, 0.4))


def repere_cymbale(h, cote):
    a = G.Acteur(h.squelette, h.sol)
    centre = a.poignet[cote] + a.jointure[cote] * 0.085 + a.paume[cote] * 0.03
    return repere_vers(centre, a.jointure[cote].cross(-a.paume[cote]), a.jointure[cote])


# « וְהִקִּישׁ בֶּן אַרְזָא בַּצֶּלְצָל, וְדִבְּרוּ הַלְוִיִּם בַּשִּׁיר » (Tamid 7:3).
def frapper(h, a, horloge, t, retard):
    q = ((t / BATTEMENT - retard) % 4.0) / 4.0
    ecart = 0.09 + 0.22 * (G.lisse(q / 0.25) if q < 0.8 else 1.0 - G.lisse((q - 0.8) / 0.2))
    centre = a.au("spine_03", devant_poitrine(h, 0.30, 0.10))
    return G.composer(G.debout(a, horloge, t, retard), G.balancement(t, BATTEMENT, 0.6, retard),
                      G.bras(a, "l", lambda poses: centre(poses) + G.GAUCHE * (ecart / 2)),
                      G.bras(a, "r", lambda poses: centre(poses) - G.GAUCHE * (ecart / 2)),
                      G.paume(a, "l", -G.GAUCHE), G.paume(a, "r", G.GAUCHE),
                      G.doigts(a, "l", 0.8, 0.5), G.doigts(a, "r", 0.8, 0.5))


def priere(h, a, horloge, t):
    va = 0.5 + 0.5 * horloge.onde(t, 1.3)
    mains = a.au("spine_03", devant_poitrine(h, 0.24, 0.30))
    return G.composer(G.pied(a, "l"), G.pied(a, "r"), G.respiration(horloge, t),
                      G.buste(flexion=0.10 + 0.16 * va), G.tete(flexion=0.12 + 0.10 * va),
                      G.bras(a, "l", lambda poses: mains(poses) + G.GAUCHE * 0.035),
                      G.bras(a, "r", lambda poses: mains(poses) - G.GAUCHE * 0.035),
                      G.doigts(a, "l", 0.55), G.doigts(a, "r", 0.55))


# La main droite posée sur le dos de la gauche, les deux paumes vers le ventre.
def mains_jointes(h, a, sous_hanche=0.02):
    mains = a.au("spine_03", Vector((0.0, -0.15, h.z_hanche - sous_hanche)))
    vers_le_ventre = lambda poses: a.dans("spine_03", poses, -G.DEVANT)
    return G.composer(G.bras(a, "l", lambda poses: mains(poses) + G.GAUCHE * 0.035),
                      G.bras(a, "r", lambda poses: mains(poses) - G.GAUCHE * 0.02 + G.DEVANT * 0.03 + G.HAUT * 0.02),
                      G.paume(a, "l", vers_le_ventre), G.paume(a, "r", vers_le_ventre),
                      G.doigts(a, "l", 0.30, 0.15), G.doigts(a, "r", 0.40, 0.2))


def ecouter(h, a, horloge, t):
    return G.composer(G.debout(a, horloge, t, 0.4, regard=0.04), G.tete(flexion=0.06 + 0.04 * horloge.onde(t, 2.4)),
                      mains_jointes(h, a))


# Un des vingt et un postes des Léviim, aux portes de l'Azara (Middot 1:1) : debout, les bras le long du corps, le regard qui va.
def garder(h, a, horloge, t):
    return G.composer(G.debout(a, horloge, t, 0.8, regard=0.45), G.doigts(a, "l", 0.35, 0.15), G.doigts(a, "r", 0.35, 0.15))


# « וְרָאשֵׁיהֶן מִבֵּין רַגְלֵי הַלְוִיִּם » (Arakhin 2:6) : les enfants chantent à terre, sans instrument.
def chanter(h, a, horloge, t, retard):
    return G.composer(G.debout(a, horloge, t, retard, regard=0.03), G.balancement(t, BATTEMENT, 0.8, retard),
                      G.tete(flexion=-0.14), mains_jointes(h, a, -0.04))


def repere_gizra(h):
    return repere_vers(devant_poitrine(h, 0.30, 0.32), G.GAUCHE, G.HAUT)


# « הֵחֵלּוּ מַעֲלִין בְּגִזְרִין לְסַדֵּר אֵשׁ הַמַּעֲרָכָה » (Tamid 2:3) : la bûche descend vers la ma'arakha, puis remonte.
def charger(h, a, horloge, t):
    u = t / horloge.duree
    w = G.lisse((u - 0.20) / 0.18) * (1.0 - G.lisse((u - 0.62) / 0.18))
    corps = G.composer(G.debout(a, horloge, t, 0.3, regard=0.03),
                       G.bassin(Vector((0.0, 0.10 * w, -0.16 * w)), tangage=0.30 * w),
                       G.buste(flexion=0.62 * w), G.tete(flexion=-0.10 * w))
    buche = a.repere("spine_03", repere_gizra(h))(a.sq.resoudre(corps)[0])
    axe = buche.col[2].to_3d()
    return saisir(a, corps, RAYON_GIZRA, {"l": buche @ Vector((0.0, 0.0, 0.22)), "r": buche @ Vector((0.0, 0.0, -0.22))},
                  {"l": -axe, "r": axe}, poles={"l": None, "r": None})


PENTE_KEVESH = 9.0 / 30.0


def repere_ever(h):
    return repere_vers(Vector((0.21, -0.20, h.z_hanche + 0.06)), 0.25 * G.DEVANT - G.HAUT, G.GAUCHE)


# « הָלְכוּ וּנְתָנוּם מֵחֲצִי הַכֶּבֶשׁ וּלְמַטָּה בְּמַעֲרָבוֹ, וּמְלָחוּם » (Tamid 4:3) : la droite va au sel, puis sale le membre que tient la gauche.
def saler(h, a, horloge, t):
    u = t / horloge.duree
    au_sel = G.lisse((u - 0.04) / 0.16) * (1.0 - G.lisse((u - 0.36) / 0.12))
    sur_ever = G.lisse((u - 0.44) / 0.10) * (1.0 - G.lisse((u - 0.86) / 0.10))
    secousse = 0.02 * math.sin(TOUR * 5.0 * u) * sur_ever
    membre = a.repere("spine_03", repere_ever(h))
    sel = a.au("spine_03", Vector((-0.12, -0.50, h.z_hanche - 0.55)))
    dessus = a.au("spine_03", Vector((0.16, -0.30, h.z_hanche + 0.06)))
    pendante = a.au("spine_03", a.poignet["r"])

    def droite(poses):
        return pendante(poses).lerp(sel(poses), au_sel).lerp(dessus(poses) + G.HAUT * secousse, sur_ever)

    penche = 0.55 * au_sel + 0.20 * sur_ever
    return G.composer(G.pied(a, "l", sol=-PENTE_KEVESH * 0.09), G.pied(a, "r", sol=PENTE_KEVESH * 0.09),
                      G.respiration(horloge, t),
                      G.bassin(Vector((0.0, 0.12 * penche, -0.18 * penche)), tangage=0.35 * penche),
                      G.buste(flexion=0.55 * penche), G.tete(flexion=0.25 * penche - 0.05),
                      G.bras(a, "l", lambda poses: membre(poses) @ Vector((0.0, 0.0, -0.03))), G.bras(a, "r", droite),
                      G.paume(a, "l", G.DEVANT - G.GAUCHE), G.paume(a, "r", G.DEVANT * (1.0 - sur_ever) - G.HAUT * sur_ever),
                      G.doigts(a, "l", 0.8, 0.5), G.doigts(a, "r", 0.35 + 0.3 * au_sel))


# « אֶבֶן הָיְתָה לִפְנֵי הַמְּנוֹרָה וּבָהּ שָׁלֹשׁ מַעֲלוֹת שֶׁעָלֶיהָ הַכֹּהֵן עוֹמֵד וּמֵטִיב אֶת הַנֵּרוֹת » (Tamid 3:9) :
# debout sur la pierre, il se penche sur les lampes ; le kouz attend sur la deuxième marche.
def hatava(h, a, horloge, t):
    va = 0.5 + 0.5 * horloge.onde(t, 2.5)
    lampe = a.au("spine_03", devant_poitrine(h, 0.56 - 0.05 * va, 0.38 - 0.05 * va, -0.10))
    pendante = a.au("spine_03", a.poignet["l"])
    return G.composer(G.debout(a, horloge, t, 0.6, regard=0.02), G.buste(flexion=0.16, torsion=0.08), G.tete(flexion=0.12),
                      G.bras(a, "l", pendante), G.bras(a, "r", lampe),
                      G.paume(a, "r", G.DEVANT - G.HAUT), G.doigts(a, "l", 0.3), G.doigts(a, "r", 0.3))


# Tenu sans peau : `matrice(h, a, horloge, t, poses)` le place dans le repère de l'armature, image par image.
class Accessoire(NamedTuple):
    nom: str
    construire: object
    matrice: object


# Les lèvres, sous le bout du nez : le point le plus avancé du profil, entre les yeux et le menton.
def bouche(h):
    profil = h.co[h.visible & h.tete_ & (np.abs(h.co[:, 0]) < 0.01)]
    profil = profil[(profil[:, 2] > h.z_tete - 0.24) & (profil[:, 2] < h.z_tete - 0.10)]
    z = float(profil[np.argmin(profil[:, 1]), 2]) - 0.045
    levres = profil[np.abs(profil[:, 2] - z) < 0.006]
    return Vector((0.0, float(levres[:, 1].min()) - 0.008, z))


def entre(m0, m1, w):
    m = m0.to_quaternion().slerp(m1.to_quaternion(), w).to_matrix().to_4x4()
    m.translation = m0.translation.lerp(m1.translation, w)
    return m


TEKIA = 12.0
# Tekia, terua, tekia (Soucca 5:4), en secondes dans la boucle.
SONNERIES = ((1.8, 3.6), (3.9, 5.4), (5.7, 7.5))


def repere_trompette(h, t):
    levee = G.lisse((t - 0.5) / 1.0) * (1.0 - G.lisse((t - 8.0) / 1.0))
    baissee = repere_vers(devant_poitrine(h, 0.10, 0.30), Vector((0.0, -1.0, -0.8)), G.GAUCHE)
    return entre(baissee, repere_vers(h.bouche, Vector((0.0, -1.0, 0.45)), G.GAUCHE), levee)


# m de l'embouchure à chaque poing : plus près, l'avant-bras gauche se dressait devant le visage.
PRISES = {"l": 0.22, "r": 0.36}
RAYON_TUBE = 0.0065


def trompette_tenue(h, a, horloge, t, poses):
    return a.repere("spine_03", repere_trompette(h, t))(poses)


# Le coude part en dehors et vers le bas : le pôle par défaut, en arrière, pliait les bras levés à rebours.
def coude_ouvert(a, cote):
    s = 1.0 if cote == "l" else -1.0
    return lambda poses: a.dans("spine_03", poses, Vector((s, 0.2, -0.6)))


# `corps` posé, chaque main `cote` ferme sa poigne sur un manche de `rayon` au point `voulus[cote]`, dans l'axe
# `directions[cote]`, le coude porté vers `poles[cote]` autant que le poignet le permet. Le bras vise le poignet,
# la main tient plus loin : trois passes y ramènent le manche.
def saisir(a, corps, rayon, voulus, directions, poles=None):
    poles = poles or {c: coude_ouvert(a, c) for c in voulus}

    def tenir_a(cibles):
        regles = [corps]
        for c in voulus:
            coude = G.coude_pour_manche(a, c, rayon, cibles[c], directions[c], poles[c])
            regles += [G.bras(a, c, cibles[c], coude), G.aligner_prise(a, c, rayon, directions[c]),
                       G.poigne(a, c, rayon)]
        return G.composer(*regles)

    cibles = dict(voulus)
    for _ in range(3):
        poses = a.sq.resoudre(tenir_a(cibles))[0]
        cibles = {c: cibles[c] + voulus[c] - G.manche(a, c, rayon, poses)[0] for c in voulus}
    return tenir_a(cibles)


# « וְעָמְדוּ שְׁנֵי כֹהֲנִים בַּשַּׁעַר הָעֶלְיוֹן … וּשְׁתֵּי חֲצוֹצְרוֹת בִּידֵיהֶן » (Soucca 5:4) : la trompette monte aux lèvres, sonne, redescend.
# Les deux mains par-dessus le tube, le pouce vers l'embouchure.
def tekia(h, a, horloge, t):
    souffle = max(G.lisse((t - debut) / 0.3) * (1.0 - G.lisse((t - fin) / 0.3)) for debut, fin in SONNERIES)
    corps = G.composer(G.debout(a, horloge, t, 0.5, regard=0.0), G.buste(flexion=-0.05 * souffle))
    visee = a.repere("spine_03", repere_trompette(h, t))(a.sq.resoudre(corps)[0])
    vers_l_embouchure = -visee.col[2].to_3d()
    return saisir(a, corps, RAYON_TUBE, {c: visee @ Vector((0.0, 0.0, PRISES[c])) for c in "lr"},
                  {c: vers_l_embouchure for c in "lr"})


# Le manche passe dans le poing fermé, la tête du côté du pouce.
def dans_la_poigne(cote, rayon):
    def matrice(h, a, horloge, t, poses):
        centre, axe = G.manche(a, cote, rayon, poses)
        return repere_vers(centre, axe, a.dans(f"hand_{cote}", poses, a.jointure[cote]))
    return matrice


def pas_de_marche(h, a, horloge, t, phase, foulee, sol):
    return G.composer(G.marche(a, phase, foulee, sol), G.respiration(horloge, t),
                      G.tete(lacet=0.08 * horloge.onde(t, 6.0)))


# Un point du Temple, en amot, dans le repère de l'armature d'une figure posée en `ou`, tournée vers `cap`, pieds à `sol`.
def vers_la_figure(ou, cap, point, sol):
    d = Vector(point) - Vector(ou)
    regard = cap_vers(cap)
    local = Matrix.Rotation(-math.atan2(regard.x, -regard.y), 3, "Z") @ Vector((d.x, d.y, 0.0))
    return Vector((local.x * AMA, local.y * AMA, d.z * AMA + sol))


# Assis sur un siège de `hauteur` m : le bassin recule et descend, les pieds restent posés, un peu avancés.
RECUL_ASSIS = 0.40
SOUS_LE_BASSIN = 0.09


def assis(a, horloge, t, hauteur, graine=0.0):
    descente = a.sol + hauteur + SOUS_LE_BASSIN - a.bassin.z
    return G.composer(G.pied(a, "l", G.DEVANT * 0.10), G.pied(a, "r", G.DEVANT * 0.10),
                      G.bassin(Vector((0.0, RECUL_ASSIS, descente)), tangage=-0.08),
                      G.respiration(horloge, t, phase=graine), G.buste(flexion=0.10))


def mains_aux_genoux(a, corps):
    poses = a.sq.resoudre(corps)[0]
    genoux = {c: poses[f"calf_{c}"].translation + Vector((0.0, 0.07, 0.07)) for c in "lr"}
    return G.composer(G.bras(a, "l", genoux["l"]), G.bras(a, "r", genoux["r"]),
                      G.paume(a, "l", -G.HAUT), G.paume(a, "r", -G.HAUT), G.doigts(a, "l", 0.35), G.doigts(a, "r", 0.35))


def repere_sefer(h):
    return repere_vers(devant_poitrine(h, 0.34, 0.30), Vector((0.0, 0.30, 1.0)), G.GAUCHE)


# Chaque main tient un rouleau à mi-hauteur ; la tête penchée sur la colonne.
def lire_le_sefer(h, a, corps, horloge, t):
    rouleau = a.repere("spine_03", repere_sefer(h))
    return G.composer(corps, G.tete(flexion=0.30 + 0.04 * horloge.onde(t, 3.1)),
                      G.bras(a, "l", lambda poses: rouleau(poses) @ Vector((0.14, 0.03, -0.02))),
                      G.bras(a, "r", lambda poses: rouleau(poses) @ Vector((-0.14, 0.03, -0.02))),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, -G.GAUCHE)),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.GAUCHE)),
                      G.doigts(a, "l", 0.9, 0.6), G.doigts(a, "r", 0.9, 0.6))


def tenir_le_sefer(h):
    tenir(h, "sefer", sefer, "spine_03", repere_sefer(h))
    return h


def tenir_la_coupe(ecart):
    def geste(h, a, horloge, t):
        coupe = a.repere("spine_03", repere_mizrak(h))
        return G.composer(G.debout(a, horloge, t, 0.3, regard=0.10), G.tete(flexion=0.12),
                          G.bras(a, "l", lambda poses: coupe(poses) @ Vector((ecart, 0.0, 0.02))),
                          G.bras(a, "r", lambda poses: coupe(poses) @ Vector((-ecart, 0.0, 0.02))),
                          G.paume(a, "l", lambda poses: G.HAUT - G.GAUCHE),
                          G.paume(a, "r", lambda poses: G.HAUT + G.GAUCHE), G.doigts(a, "l", 0.25), G.doigts(a, "r", 0.25))
    return geste
