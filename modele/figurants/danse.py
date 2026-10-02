import math
from typing import NamedTuple

from mathutils import Matrix, Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA

from .maillage import TOUR
from .ustensiles import avouka
from .mise_en_scene import Accessoire, coude_ouvert, saisir


# « חֲסִידִים וְאַנְשֵׁי מַעֲשֶׂה הָיוּ מְרַקְּדִים לִפְנֵיהֶם בַּאֲבוּקוֹת שֶׁל אוֹר שֶׁבִּידֵיהֶן » (Soucca 5:4) : la ronde est une
# hora, CHOIX : face au centre, pas de côté, pas croisé derrière, pas de côté, sautillé jambe lancée, deux fois,
# puis quatre pas vers celui qui jongle, torches levées, et quatre pas en arrière ; la même chose vers la droite.
BATTEMENT_HORA = 60.0 / 126.0
PAS_HORA = 0.22
ECART_HORA = 0.10


class Appui(NamedTuple):
    envol: float
    pose: float
    x: float
    y: float
    coup: tuple = None


# En temps (battements) et en mètres dans la ronde : x vers la gauche du danseur, y vers l'extérieur.
class Choregraphie:
    def __init__(self):
        self.appuis, self.suspens = {"l": [], "r": []}, {}
        self.sauts, self.elans, self.sens = [], [], []
        x = 0.0
        for k in range(3):
            x = self.hora(6.0 * k, x, 1.0)
        self.vers_le_centre(18.0, x, "l")
        for k in range(3):
            x = self.hora(26.0 + 6.0 * k, x, -1.0)
        self.vers_le_centre(44.0, x, "r")
        self.temps = 52.0

    def poser(self, cote, pose, x, y, envol=None, coup=None):
        if cote in self.suspens:
            envol, coup = self.suspens.pop(cote)
        self.appuis[cote].append(Appui(pose - 0.8 if envol is None else envol, pose, x, y, coup))

    def hora(self, b0, x0, sens):
        w, a = ECART_HORA, PAS_HORA
        mene, suit = ("l", "r") if sens > 0 else ("r", "l")

        def X(v):
            return x0 + sens * v
        self.poser(mene, b0 + 0.8, X(w + a), 0.0, envol=b0)
        self.poser(suit, b0 + 1.8, X(w + a - 0.08), 0.09, envol=b0 + 1.0)
        self.poser(mene, b0 + 2.8, X(w + 2 * a), 0.0, envol=b0 + 2.0)
        self.poser(suit, b0 + 4.6, X(2 * a - w), 0.0, envol=b0 + 3.0, coup=(X(w + 2 * a - 0.03), -0.17, 0.16))
        self.suspens[mene] = (b0 + 5.0, (X(2 * a - w + 0.03), -0.17, 0.16))
        self.sauts += [(b0 + 3.5, mene), (b0 + 5.5, suit)]
        self.sens.append((b0, b0 + 6.0, sens))
        return X(2 * a)

    def vers_le_centre(self, b0, x0, mene):
        suit = "r" if mene == "l" else "l"
        pieds = {"l": x0 + ECART_HORA, "r": x0 - ECART_HORA}
        for k, (cote, y) in enumerate(zip((mene, suit) * 4, (-0.22, -0.44, -0.66, -0.66, -0.44, -0.22, 0.0, 0.0))):
            self.poser(cote, b0 + k + 0.8, pieds[cote], y, envol=b0 + k)
        self.elans.append((b0, b0 + 8.0))

    # (x, y, hauteur, envol) du pied au temps `b` ; envol = (part du pas, jambe lancée) en l'air, None posé.
    def pied(self, cote, b):
        x, y = (ECART_HORA if cote == "l" else -ECART_HORA), 0.0
        for ap in self.appuis[cote]:
            if b < ap.envol:
                break
            if b < ap.pose:
                u = (b - ap.envol) / (ap.pose - ap.envol)
                if ap.coup is None:
                    v = G.lisse(u)
                    return x + (ap.x - x) * v, y + (ap.y - y) * v, 0.07 * math.sin(math.pi * u), (u, False)
                cx, cy, hauteur = ap.coup
                if u < 0.5:
                    v = G.lisse(u / 0.5)
                    px, py = x + (cx - x) * v, y + (cy - y) * v
                else:
                    v = G.lisse((u - 0.5) / 0.5)
                    px, py = cx + (ap.x - cx) * v, cy + (ap.y - cy) * v
                return px, py, hauteur * math.sin(math.pi * u), (u, True)
            x, y = ap.x, ap.y
        return x, y, 0.0, None

    def saut(self, b, cote=None):
        return max([math.sin(math.pi * (b - t + 0.5)) for t, c in self.sauts
                    if abs(b - t) < 0.5 and cote in (None, c)] or [0.0])

    def lever(self, b):
        return max([G.lisse((b - d) / 3.5) * (1.0 - G.lisse((b - f + 4.0) / 3.5)) for d, f in self.elans] or [0.0])

    def cote_de_marche(self, b):
        return next((s for d, f, s in self.sens if d <= b < f), 0.0)


CHOREGRAPHIE = Choregraphie()


# En amot : le danseur tient sa place `depart` (angle) sur le cercle de `rayon` autour de `centre`, face au centre.
class Hora:
    def __init__(self, centre, rayon, depart, torche="r", main_libre="ouverte"):
        self.centre, self.rayon, self.depart = Vector(centre) * AMA, rayon * AMA, depart
        self.torche, self.main_libre = torche, main_libre
        self.pas = CHOREGRAPHIE
        self.duree = self.pas.temps * BATTEMENT_HORA

    def monde(self, x, y):
        angle = self.depart - x / self.rayon
        return self.centre + Vector((math.cos(angle), math.sin(angle))) * (self.rayon + y)

    def bornes(self, marge):
        c, r = self.centre, self.rayon + 1.0 + marge
        return c.x - r, c.x + r, c.y - r, c.y + r


RAYON_MANCHE = 0.017


def danse(h, a, hora, b, pieds):
    pas = hora.pas
    lever = pas.lever(b)
    appui = 0.5 + 0.5 * math.cos(TOUR * (b % 1.0 - 0.85))
    saut = pas.saut(b)
    regles = []
    for cote, (decalage, envol) in pieds.items():
        if envol is None:
            tangage, pivot = 0.35 * pas.saut(b, cote), "balle"
        elif envol[1]:
            tangage, pivot = 0.25 * math.sin(math.pi * envol[0]), "talon"
        else:
            tangage, pivot = 0.35 * math.sin(math.pi * envol[0]), "balle"
        regles.append(G.pied(a, cote, decalage, tangage, pivot))
    marche = pas.cote_de_marche(b)
    corps = G.composer(*regles, G.bassin(Vector((0.0, 0.0, -0.035 - 0.035 * appui + 0.045 * saut)),
                                         roulis=0.03 * marche * appui),
                       G.buste(flexion=0.08 + 0.08 * lever, inclinaison=-0.05 * marche),
                       G.tete(flexion=-0.12 - 0.10 * lever + 0.04 * appui, inclinaison=0.04 * marche))
    poses = a.sq.resoudre(corps)[0]
    t = hora.torche
    s = 1.0 if t == "l" else -1.0
    # La torche, coude plié à hauteur de tête, se soulève à chaque temps un peu après le rebond du corps, traîne
    # à l'opposé du pas de côté, et monte bras tendu vers le jongleur quand la ronde avance.
    elan = 0.5 - 0.5 * math.cos(TOUR * (b - 0.2))
    traine = -marche * (1.0 - lever)
    torche = a.au("spine_03", a.epaule[t] + G.HAUT * (0.13 + 0.05 * elan + 0.22 * lever)
                  + G.GAUCHE * (s * 0.10 + 0.03 * traine) + G.DEVANT * (0.20 + 0.20 * lever))
    droite = a.dans("spine_03", poses, G.HAUT + G.GAUCHE * (s * 0.12 * (1.0 - lever) + 0.08 * traine)
                    + G.DEVANT * (0.05 + 0.12 * lever))
    tenue = saisir(a, corps, RAYON_MANCHE, {t: torche(poses)}, {t: droite})
    libre = "r" if t == "l" else "l"
    s = -s
    main = a.au("spine_03", a.epaule[libre] + G.HAUT * (0.05 + 0.18 * lever + 0.07 * (1.0 - appui))
                + G.GAUCHE * (s * (0.22 - 0.10 * lever)) + G.DEVANT * (0.22 + 0.18 * lever))
    ouverte = hora.main_libre == "ouverte"
    return G.composer(tenue, G.bras(a, libre, main, coude_ouvert(a, libre)),
                      G.paume(a, libre, lambda p: a.dans("spine_03", p, G.DEVANT - G.GAUCHE * (0.5 * s))),
                      G.doigts(a, libre, 0.15, 0.2) if ouverte else G.doigts(a, libre, 1.3, 0.9))


# « הָיָה נוֹטֵל שְׁמֹנֶה אֲבוּקוֹת שֶׁל אוֹר, וְזוֹרֵק אַחַת וְנוֹטֵל אַחַת וְאֵין נוֹגְעוֹת זוֹ בָּזוֹ » (Soucca 53a) :
# huit torches en fontaine, quatre par main, chacune relancée par la main qui l'a reçue. Les cadences sont un CHOIX.
JET = 0.225             # s entre deux lancers, d'une main à l'autre
TENUE = 0.30            # s dans la main, de la réception au lancer
VOL = 8 * JET - TENUE
PESANTEUR = 9.81
INCLINAISON_TENUE = 0.75   # rad : la tête de la torche en avant, loin du visage
AXE_TENUE = Vector((0.0, -math.sin(INCLINAISON_TENUE), math.cos(INCLINAISON_TENUE)))


# La poigne dans son cycle de deux jets : lancé à l'intérieur à `phase` 0, vide par-dessus, reçu dehors, porté par-dessous.
def poing_du_jongleur(h, cote, phase):
    s = 1.0 if cote == "l" else -1.0
    z0 = h.z_hanche + 0.20
    dedans, dehors = s * 0.10, s * 0.30
    tenue = TENUE / (2 * JET)
    if phase < 1.0 - tenue:
        u = phase / (1.0 - tenue)
        return Vector((dedans + (dehors - dedans) * u, -0.38, z0 + 0.05 * math.sin(math.pi * u)))
    v = (phase - 1.0 + tenue) / tenue
    return Vector((dehors + (dedans - dehors) * v, -0.38, z0 - 0.10 * math.sin(math.pi * v)))


def depart_du_poing(cote):
    return 0.0 if cote == "l" else JET


def poing_a(h, cote, t):
    return poing_du_jongleur(h, cote, ((t - depart_du_poing(cote)) / (2 * JET)) % 1.0)


def torche_jonglee(j):
    cote = "lr"[j % 2]
    decalage = depart_du_poing(cote) + 2 * JET * (j // 2)

    def matrice(h, a, horloge, t, poses):
        u = (t - decalage) % (8 * JET)
        if u >= VOL:
            p, tour = poing_a(h, cote, t), 0.0
        else:
            lancer, reception = poing_du_jongleur(h, cote, 0.0), poing_du_jongleur(h, cote, 1.0 - TENUE / (2 * JET))
            p = lancer.lerp(reception, u / VOL)
            p.z += PESANTEUR * u * (VOL - u) / 2
            tour = TOUR * u / VOL
        m = Matrix.Rotation(INCLINAISON_TENUE + tour, 4, "X")
        m.translation = p
        return m
    return Accessoire(f"avouka_{j + 1}", avouka, matrice)


# Les coudes au corps, la poigne toujours fermée sur la torche qu'elle tient ou attend.
def jongler(h, a, horloge, t):
    corps = G.composer(G.debout(a, horloge, t, 0.2, regard=0.0), G.buste(flexion=-0.03), G.tete(flexion=-0.32))
    return saisir(a, corps, RAYON_MANCHE, {c: poing_a(h, c, t) for c in "lr"}, {c: AXE_TENUE for c in "lr"},
                  poles={c: None for c in "lr"})
