import math
from typing import NamedTuple

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import beit_hamikdash_gestes as G

from .matieres import (ARGAMAN, DRAP_NOIR, LAINE_BLEUE, LIN, METAUX, RAIE_TALITH, SHANI, TALITH, TEKHELET,
                       bois, metal)
from .etoffes import Habit, hors_de, poids_de, surface_de
from .corps import _alea
from .maillage import TOUR, Maillage, Teintes, _angles, _lisser_cercle, _vers, enveloppe, tranche, tube


AVNET_BRODE = Teintes(((0.000, LIN), (0.010, TEKHELET), (0.022, ARGAMAN), (0.034, SHANI), (0.046, TEKHELET), (0.056, LIN),
                       (0.064, LIN)), (TEKHELET, ARGAMAN, SHANI))
# « וְאַרְבַּעְתָּן לְבָנִים … וּמִן הַפִּשְׁתָּן לְבַדּוֹ הֵם » (Rambam Klei HaMikdash 8:3) : à Kippour, l'avnet est de lin seul.
AVNET_DE_LIN = Teintes(tuple((dz, LIN) for dz, _ in AVNET_BRODE.bandes), (LIN,) * 3)


def avnet(mm, ceinture, surface, teintes=AVNET_BRODE):
    z0 = ceinture.z - 0.032
    th = _angles()
    anneaux, couleurs = [], []
    for dz, couleur in teintes.bandes:
        epaisseur = 0.003 if dz in (0.0, teintes.bandes[-1][0]) else 0.010
        anneaux.append([ceinture.point(t, z0 + dz, epaisseur) for t in th])
        couleurs.append(couleur)
    mm.nappe(anneaux, lambda i, j: couleurs[i + 1], "buste")
    raies = teintes.raies
    for depart, longueur in ((0.42, 0.52), (0.52, 0.44)):
        travers = Vector((math.cos(depart), math.sin(depart), 0.0))
        rangs = []
        for k in range(14):
            centre = hors_de(surface, ceinture.point(depart, z0 + 0.03 - longueur * k / 13, 0.016), 0.008)
            rangs.append([centre + travers * (0.027 * c) for c in (-1.0, -0.33, 0.33, 1.0)])
        mm.nappe(rangs, lambda i, j: raies[j], "jupe", ferme=False)


def _crane(humain, dessus=()):
    points = humain.co[humain.visible & humain.tete_]
    if len(dessus):
        points = np.vstack([points] + [humain.points_objet(o) for o in dessus])
    return points


# rangs = (z relatif au sommet, écart, échelle) ; `ouverture(dz)` dégage le visage.
def coiffe(mm, humain, rangs, couleur, zone="head", ouverture=None, n=40):
    points = _crane(humain, humain.poils)
    sommet = float(points[:, 2].max())
    tout = _angles(n)
    anneaux = []
    for dz, ecart, echelle in rangs:
        z = sommet + dz
        bande = points[np.abs(points[:, 2] - min(z, sommet - 0.01)) < 0.012]
        if len(bande) < 3:
            bande = points[points[:, 2] > sommet - 0.03]
        cy = 0.5 * (bande[:, 1].min() + bande[:, 1].max())
        r = _lisser_cercle(enveloppe(bande, (0.0, cy), n)) * echelle + ecart
        demi = ouverture(dz) if ouverture else 0.0
        th = np.linspace(demi, TOUR - demi, n) if ouverture else tout
        ri = np.interp(th, np.append(tout, TOUR), np.append(r, r[0]))
        anneaux.append([Vector((a * _vers(t)[0], cy + a * _vers(t)[1], z)) for t, a in zip(th, ri)])
    fin = anneaux[-1]
    mm.nappe(anneaux, couleur, zone, ferme=ouverture is None, pole_fin=sum(fin, Vector()) / len(fin))


# Une bande de lin enroulée « comme un chapeau » (Rambam Klei HaMikdash 8:2), chaque tour chevauchant le précédent ;
# `bas` : son premier tour, sous le sommet du crâne.
def migbaat(mm, humain, tours=5.0, par_tour=40, largeur=0.048, epaisseur=0.009, montee=0.022, bas=0.085):
    h = humain
    points = _crane(h, h.poils)
    sommet = float(points[:, 2].max())
    contours = {}

    def contour(z):
        cle = round(z * 400) / 400
        if cle not in contours:
            bande = points[np.abs(points[:, 2] - min(cle, sommet - 0.015)) < 0.01]
            cy = 0.5 * (bande[:, 1].min() + bande[:, 1].max())
            contours[cle] = (_lisser_cercle(enveloppe(bande, (0.0, cy)), 6), cy)
        return contours[cle]

    angles = np.append(_angles(), TOUR)
    z0, total = h.z_tete - bas, int(tours * par_tour)
    sections = []
    for s in range(total + 1):
        t = s / par_tour
        th = TOUR * t + 0.6
        z = z0 + montee * t + 0.007 * math.sin(th - 0.9)
        r_env, cy = contour(z)
        dome = G.lisse((z - (sommet - 0.05)) / 0.07)
        r = float(np.interp(th % TOUR, angles, np.append(r_env, r_env[0]))) * (1.0 - 0.5 * dome) + epaisseur * (0.8 + 0.3 * t)
        dx, dy = _vers(th)
        centre, dehors = Vector((r * dx, cy + r * dy, z)), Vector((dx, dy, 0.0))
        haut = (HAUT_Z - dehors * (0.2 + 0.9 * dome)).normalized()
        w = largeur * (0.35 + 0.65 * G.lisse(s / 10) * G.lisse((total - s) / 10)) / 2
        e = epaisseur / 2
        profil = ((-e, -w), (e, -0.9 * w), (1.3 * e, 0.0), (e, 0.9 * w), (-e, w), (-0.6 * e, 0.0))
        sections.append([centre + dehors * a + haut * b for a, b in profil])
    mm.nappe(sections, LIN, "head")
    coiffe(mm, h, [(-0.035, 0.010, 0.80), (-0.015, 0.010, 0.62), (0.0, 0.008, 0.42), (0.008, 0.004, 0.2)], LIN, "head")


# « כֹּהֵן גָּדוֹל צוֹנֵף בָּהּ כְּמִי שֶׁלּוֹפֵף עַל הַשֶּׁבֶר » (Rambam Klei HaMikdash 8:2) : la même bande, enroulée à plat.
def mitznefet(mm, humain):
    migbaat(mm, humain, tours=6.0, montee=0.010)


# « שְׂעָרוֹ הָיָה נִרְאֶה בֵּין צִיץ לְמִצְנֶפֶת » (Zeva'him 19a) : portée plus haut, elle laisse le front au tsits.
def mitznefet_relevee(mm, humain):
    migbaat(mm, humain, tours=6.0, montee=0.008, bas=0.050)


HAUT_Z = Vector((0.0, 0.0, 1.0))


def _crane_et_cheveux(humain):
    h = humain
    return _crane(h, [h.cheveux] if h.cheveux else [])


def _centre_de_voute(points):
    voute = points[points[:, 2] > points[:, 2].max() - 0.07]
    (cx, cy, cz, _), *_ = np.linalg.lstsq(np.hstack([2.0 * voute, np.ones((len(voute), 1))]), (voute ** 2).sum(axis=1), rcond=None)
    return Vector((cx, cy, cz))


# Calotte sur le sommet un peu en arrière, `rayon` celui de son bord : sa distance au centre du crâne est un polynôme cubique
# des rayons lancés sur crâne et cheveux, tirée vers les plus saillants puis relevée du dernier dépassement : lisse et ronde quelles que soient les mèches.
def calotte(mm, humain, couleur, rayon=0.060, recul=0.50, ecart=0.007, rangs=14, n=56):
    h = humain
    tete = h.visible & h.tete_
    arbre = surface_de(h, [], tete)
    centre = _centre_de_voute(h.co[tete])
    axe = Vector((0.0, math.sin(recul), math.cos(recul)))
    u = Vector((1.0, 0.0, 0.0))
    w = axe.cross(u)
    ouverture = math.asin(min(rayon / 0.09, 0.95))
    phis = np.linspace(0.0, TOUR, n, endpoint=False)
    rangs_ = [(ouverture + 0.008, -0.006), (ouverture + 0.003, -0.001)] + [(ouverture * (1.0 - k / rangs), 0.0) for k in range(rangs)]

    def direction(a, phi):
        return axe * math.cos(a) + (u * math.cos(phi) + w * math.sin(phi)) * math.sin(a)

    def termes(a, phi):
        x, y = math.sin(a) * math.cos(phi), math.sin(a) * math.sin(phi)
        return (1.0, x, y, x * x, x * y, y * y, x ** 3, x * x * y, x * y * y, y ** 3)

    echantillons = [(a, phi) for a in np.linspace(0.0, ouverture + 0.12, 10) for phi in phis[::2]]
    mesures = []
    for a, phi in echantillons:
        d = direction(a, phi)
        touche = arbre.ray_cast(centre + d * 0.3, -d)[0]
        mesures.append((touche - centre).length if touche is not None else np.nan)
    mesures = np.array(mesures)
    garde = ~np.isnan(mesures)
    a_, m = np.array([termes(a, phi) for a, phi in echantillons])[garde], mesures[garde]
    poids = np.ones(len(m))
    for _ in range(12):
        coef, *_ = np.linalg.lstsq(a_ * poids[:, None], m * poids, rcond=None)
        poids = np.where(m > a_ @ coef, 1.0, 0.25)
    releve = float((m - a_ @ coef).max()) + ecart

    def distance(a, phi):
        return float(np.dot(termes(a, phi), coef)) + releve

    anneaux = [[centre + direction(a, phi) * (distance(a, phi) + dehors) for phi in phis] for a, dehors in rangs_]
    mm.nappe(anneaux, couleur, "head", pole_fin=centre + axe * distance(0.0, 0.0))


FEUTRE = DRAP_NOIR
RUBAN = (0.006, 0.006, 0.008)


class Borsalino(NamedTuple):
    hauteur: float = 0.120
    bord: float = 0.070
    pli: float = 0.032
    ruban: float = 0.036
    inclinaison: float = 0.10
    ecart: float = 0.006


# Borsalino noir : calotte haute pincée devant et creusée d'un pli, bord large relevé sur les côtés, ruban gros-grain noué à gauche.
# Le bandeau passe à 5 cm au-dessus des yeux, un peu plus bas derrière ; θ = 0 devant.
class Chapeau:
    N = 72
    ARRONDI = 0.018

    def __init__(self, humain, forme):
        h, f = humain, forme
        self.forme = f
        points = _crane_et_cheveux(h)
        yeux = h.points_objet(h.accessoires[0]).mean(axis=0)
        self.pente = math.tan(f.inclinaison)
        niveau = points[:, 2] + self.pente * points[:, 1]
        self.z_bande = float(yeux[2] + 0.052 + self.pente * yeux[1])
        tour = points[(niveau > self.z_bande - 0.01) & (niveau < self.z_bande + 0.06)]
        self.cy = 0.5 * float(tour[:, 1].min() + tour[:, 1].max())
        self.th = _angles(self.N)
        self.r_bande = _lisser_cercle(enveloppe(tour[:, :2], (0.0, self.cy), self.N), 12) + f.ecart
        self.hauteur = max(f.hauteur, float(niveau.max()) - self.z_bande + f.pli + 0.014)

    def point(self, t, r, dz):
        x, y = r * math.sin(t), self.cy - r * math.cos(t)
        return Vector((x, y, self.z_bande - self.pente * y + dz))

    def haut(self, t):
        return self.hauteur - 0.007 * math.cos(t)

    def paroi(self, k, s):
        t = self.th[k]
        pince = sum(math.exp(-((((t - c) + math.pi) % TOUR - math.pi) / 0.45) ** 2) for c in (0.8, TOUR - 0.8))
        return self.r_bande[k] * (1.0 - 0.11 * s) - 0.011 * s * s * pince, self.haut(t) * s

    def couronne(self, mm):
        n, a = self.N, self.ARRONDI
        anneaux = [[self.point(self.th[k], *self.paroi(k, s)) for k in range(n)] for s in np.linspace(0.0, 1.0, 10)[:-1]]
        for phi in np.linspace(0.0, math.pi / 2, 5):
            anneaux.append([self.point(self.th[k], self.paroi(k, 1.0)[0] - a * (1.0 - math.cos(phi)),
                                       self.haut(self.th[k]) - a + a * math.sin(phi)) for k in range(n)])
        r_haut = [self.paroi(k, 1.0)[0] - a for k in range(n)]
        long_ = 0.5 * (r_haut[0] + r_haut[n // 2])

        def creux(p):
            y = p.y - self.cy
            largeur = 0.030 + 0.006 * y / long_
            return Vector((0.0, 0.0, self.forme.pli * G.lisse(1.0 - abs(p.x) / largeur) * G.lisse((long_ - abs(y)) / 0.028)))

        for lam in np.linspace(1.0, 0.0, 15)[1:-1]:
            dome = 0.004 * (1.0 - lam * lam)
            anneaux.append([self.point(self.th[k], lam * r_haut[k], self.haut(self.th[k]) + dome) for k in range(n)])
            anneaux[-1] = [p - creux(p) for p in anneaux[-1]]
        pole = self.point(0.0, 0.0, self.hauteur + 0.004)
        mm.nappe(anneaux, FEUTRE, "head", pole_fin=pole - creux(pole))

    def bord(self, mm):
        epaisseur = 0.0022
        profil = ([(s, -epaisseur) for s in np.linspace(0.0, 1.0, 6)] + [(1.03, 0.0)]
                  + [(s, epaisseur) for s in np.linspace(1.0, 0.0, 6)])

        def releve(t, s):
            return s * s * (0.006 + 0.016 * math.sin(t) ** 2)

        mm.nappe([[self.point(t, r - 0.002 + s * self.forme.bord, releve(t, min(s, 1.0)) + dz) for t, r in zip(self.th, self.r_bande)]
                  for s, dz in profil], FEUTRE, "head")

    def _ceinture(self, s, dehors):
        return [self.point(self.th[k], self.paroi(k, s)[0] + dehors, self.paroi(k, s)[1]) for k in range(self.N)]

    def ruban(self, mm):
        haut = self.forme.ruban / self.hauteur
        mm.nappe([self._ceinture(s, dehors) for s, dehors in ((0.0, 0.0), (0.0, 0.0018), (haut, 0.0018), (haut, 0.0))], RUBAN, "head")
        k0 = int(round(self.N * 0.39))
        rangs = []
        for dk in range(-4, 5):
            demi = 0.55 * haut * (0.45 + 0.55 * min(abs(dk) / 2.0, 1.0))
            k = (k0 + dk) % self.N
            rangs.append([self.point(self.th[k], self.paroi(k, s)[0] + 0.0035, self.paroi(k, s)[1])
                          for s in np.linspace(0.5 * haut - demi, 0.5 * haut + demi, 4)])
        mm.nappe(rangs, RUBAN, "head", ferme=False)


def chapeau(mm, humain, forme=Borsalino()):
    c = Chapeau(humain, forme)
    c.couronne(mm)
    c.bord(mm)
    c.ruban(mm)


RAIES_TALITH = ((0.10, 0.175), (0.20, 0.225), (0.25, 0.275))
ATARA = (0.70, 0.70, 0.68)


# Plié en étole : l'atara cerne la nuque, les deux pans descendent sur la poitrine et tombent par-dessus les bras.
def talith(mm, humain, longueur=1.90, largeur=0.20, pas=0.02):
    h = humain
    surface = surface_de(h, h.vetements_mpfb, h.visible)
    z_col = h.z_cou - 0.01
    cou = tranche(h, h.cou & h.visible, z_col, 0.02)
    cy = 0.5 * (cou[:, 1].min() + cou[:, 1].max())
    r_col = float(np.median(enveloppe(cou, (0.0, cy)))) + 0.02
    th_devant = 0.55
    arc = r_col * (math.pi - th_devant)
    dx, dy = _vers(th_devant)
    depart = Vector((r_col * dx, cy + r_col * dy, z_col))
    sortie_col, sortie_pan = Vector((dx, dy, -0.9)).normalized(), Vector((1.0, 0.0, -0.1)).normalized()

    def bord(s):
        if s <= arc:
            vx, vy = _vers(math.pi - s / r_col)
            return Vector((r_col * vx, cy + r_col * vy, z_col)), Vector((vx, vy, -0.9)).normalized()
        d = s - arc
        return depart + Vector((0.02, -0.15, -1.0)) * d, sortie_col.lerp(sortie_pan, G.lisse(d / 0.12)).normalized()

    nu, nv = round(longueur / pas) + 1, round(largeur / pas) + 1
    rangs = []
    for i in range(nu):
        u = -longueur / 2 + i * pas
        p, dehors = bord(abs(u))
        rang = []
        for j in range(nv):
            q = p + dehors * (j * pas)
            if u < 0:
                q.x = -q.x
            rang.append(hors_de(surface, q, 0.02))
        rangs.append(rang)

    def couleur(i, j):
        s = abs(-longueur / 2 + (i + 0.5) * pas)
        if any(a <= longueur / 2 - s < b for a, b in RAIES_TALITH):
            return RAIE_TALITH
        return ATARA if j < 3 and s < 0.30 else TALITH

    base = len(mm.sommets)
    mm.nappe(rangs, couleur, "voile", ferme=False)
    mm.epingles.update({base + i * nv + j: 1.0 for i in range(nu) for j in range(nv)
                        if abs(-longueur / 2 + i * pas) < arc and j * pas < 0.07})
    return [base, base + nv - 1, base + (nu - 1) * nv, base + nu * nv - 1]


def tzitzit(mm, coins, longueur=0.34):
    for coin in coins:
        for k in range(4):
            ecart = Vector((math.cos(k * 1.57), math.sin(k * 1.57), 0.0)) * 0.005
            chemin = [coin + ecart * (1.0 + 2.0 * s) - HAUT_Z * (longueur * s) for s in np.linspace(0.0, 1.0, 7)]
            rayons = [0.0045 if s < 0.3 and k == 0 else 0.0015 for s in np.linspace(0.0, 1.0, 7)]
            mm.nappe(tube(chemin, rayons, 5), TALITH, "voile")


class Tissu(NamedTuple):
    obstacles: object
    masse: float = 0.2
    tension: float = 12.0
    compression: float = 4.0
    flexion: float = 0.5
    images: int = 36


TALITH_TISSU = dict(masse=0.25, tension=15.0, compression=8.0, flexion=1.2)


# Le tissu tombe sous la pesanteur, retenu par ses épingles et arrêté par `obstacles` ; sa forme finale est gardée.
def draper(objet, epingles, tissu):
    groupe = objet.vertex_groups.new(name="epingles")
    for i, poids in epingles.items():
        groupe.add([i], poids, "REPLACE")
    modificateur = objet.modifiers.new("tissu", "CLOTH")
    reglage = modificateur.settings
    reglage.quality = 8
    reglage.mass = tissu.masse
    reglage.tension_stiffness = tissu.tension
    reglage.compression_stiffness = reglage.shear_stiffness = tissu.compression
    reglage.bending_stiffness = tissu.flexion
    reglage.air_damping = 2.0
    reglage.vertex_group_mass = groupe.name
    contact = modificateur.collision_settings
    contact.collection = tissu.obstacles
    contact.distance_min = 0.008
    contact.collision_quality = 4
    contact.use_self_collision = False
    modificateur.point_cache.frame_start, modificateur.point_cache.frame_end = 1, tissu.images
    scene = bpy.context.scene
    for image in range(1, tissu.images + 1):
        scene.frame_set(image)
    graphe = bpy.context.evaluated_depsgraph_get()
    drape = bpy.data.meshes.new_from_object(objet.evaluated_get(graphe), preserve_all_data_layers=True, depsgraph=graphe)
    derive = max((a.co - b.co).length for a, b in zip(objet.data.vertices, drape.vertices))
    if derive > 0.5:
        raise RuntimeError(f"{objet.name} : la simulation du tissu a divergé ({derive:.2f} m)")
    objet.modifiers.remove(modificateur)
    objet.vertex_groups.remove(groupe)
    ancien, objet.data = objet.data, drape
    nom = ancien.name
    bpy.data.meshes.remove(ancien)
    drape.name = nom
    scene.frame_set(1)


def _objet(humain, mm, nom, materiau):
    h = humain
    me = bpy.data.meshes.new(nom)
    me.from_pydata([p[:] for p in mm.sommets], [], mm.faces)
    me.update()
    me.materials.append(materiau)
    couleurs = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    valeurs = []
    for poly, c in zip(me.polygons, mm.couleurs):
        valeurs.extend([*c, 1.0] * poly.loop_total)
    couleurs.data.foreach_set("color", valeurs)
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", [x for face in mm.uvs for coin in face for x in coin])
    me.shade_smooth()
    objet = bpy.data.objects.new(nom, me)
    for c in h.rig.users_collection:
        c.objects.link(objet)
    objet.parent = h.rig
    return objet


def materiau_de(mm):
    return metal() if all(c in METAUX for c in mm.couleurs) else bois()


# Tenu sans peau : `Enregistreur.objet` l'anime dans le repère de l'armature.
def porter(humain, mm, nom):
    return _objet(humain, mm, nom, materiau_de(mm))


def lier(humain, mm, nom, materiau, os_fixe=None, tissu=None):
    h = humain
    objet = _objet(h, mm, nom, materiau)
    if tissu is not None:
        draper(objet, mm.epingles, tissu)
    groupes = {}
    for i, (sommet, zone) in enumerate(zip(objet.data.vertices, mm.zones)):
        poids = {os_fixe: 1.0} if os_fixe else poids_de(h, zone, sommet.co)
        for groupe, w in poids.items():
            if groupe not in groupes:
                groupes[groupe] = objet.vertex_groups.new(name=groupe)
            groupes[groupe].add([i], w, "REPLACE")
    modificateur = objet.modifiers.new("Armature", "ARMATURE")
    modificateur.object = h.rig
    return objet


def appliquer_visibilite(humain, visible):
    h = humain
    groupe = h.corps.vertex_groups.get("visible") or h.corps.vertex_groups.new(name="visible")
    groupe.add([int(i) for i in np.nonzero(visible)[0]], 1.0, "REPLACE")
    for m in list(h.corps.modifiers):
        if m.type == "MASK":
            h.corps.modifiers.remove(m)
    masque = h.corps.modifiers.new("visible", "MASK")
    masque.vertex_group = "visible"
    h.corps.modifiers.move(len(h.corps.modifiers) - 1, 0)


# La barbe « sigmund » faisait un masque plein, la bouche ouverte dessus en crocs : la viking est seule en mèches.
BARBE = "rehmanpolanski_beard_viking"
MOUSTACHE = "rehmanpolanski_moustache_viking"
CHEVEUX_COURTS = ("short01", "short04")
BRUN = (0.30, 0.24, 0.20)
GRIS = (1.1, 1.05, 1.0)


def _poils(nom, gris):
    return dict(cheveux=CHEVEUX_COURTS[int(_alea(nom, 5) * 2)], barbe=(BARBE, MOUSTACHE), teinte_poils=GRIS if gris else BRUN,
                sourcils=1 + int(_alea(nom, 6) * 9))


# Robe de moine CC0 (Donitz) sans pèlerine ni cordon : la coupe longue à manches de la kutonet.
KUTONET = Habit("donitz_monk_robe", "Figure_Kutonet", LIN, pieces=(0, 2, 3), longue=True, epaules="haut")
ROBE = Habit("punkduck_medieval_dress", "Figure_Robe", LAINE_BLEUE, longue=True)
COSTUME = Habit("male_elegantsuit01", epaules="manches")


# Les faces de la robe sont larges : coupées au plan d'abord, sinon celles qui l'enjambent dressent des ailerons.
def _trancher(humain, objet, z, jeter):
    passage = humain.rig.matrix_world.inverted() @ objet.matrix_world
    retour = passage.inverted()
    bm = bmesh.new()
    bm.from_mesh(objet.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=retour @ Vector((0.0, 0.0, z)),
                           plane_no=(passage.to_3x3().transposed() @ HAUT_Z).normalized())
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if jeter([(passage @ v.co).z for v in f.verts])], context="FACES")
    bm.to_mesh(objet.data)
    bm.free()


def rogner(humain, objet, z):
    _trancher(humain, objet, z, lambda hauteurs: min(hauteurs) > z - 1e-5)


def ourler(humain, objet, z):
    _trancher(humain, objet, z, lambda hauteurs: max(hauteurs) < z + 1e-5)


# Le tissage de la robe, pris autour du point de `source` le plus proche de `ancre` et à sa densité, replié en miroir
# tous les `demi` mètres : `plan(p)` rend la place de chaque sommet dans le tissu, en mètres, et `tour` la longueur
# d'un tour, pour qu'une face à cheval sur la couture reste d'un seul tenant.
def uv_en_piece(humain, objet, source, ancre, plan, tour, demi=0.10):
    me = source.data
    passage = humain.rig.matrix_world.inverted() @ source.matrix_world
    uvs = me.uv_layers.active.data
    aire_3d = sum(p.area for p in me.polygons)
    aire_uv = sum(abs(_aire_plane([uvs[b].uv for b in p.loop_indices])) for p in me.polygons)
    par_metre = math.sqrt(aire_uv / aire_3d)
    proche = min(me.loops, key=lambda b: (passage @ me.vertices[b.vertex_index].co - ancre).length)
    centre = uvs[proche.index].uv.copy()

    def replier(x):
        return abs((x + demi) % (4.0 * demi) - 2.0 * demi) - demi

    retour = humain.rig.matrix_world.inverted() @ objet.matrix_world
    couche = objet.data.uv_layers.active.data
    for face in objet.data.polygons:
        places = [plan(retour @ objet.data.vertices[v].co) for v in face.vertices]
        u0 = places[0][0]
        for boucle, (u, v) in zip(face.loop_indices, places):
            u -= tour * round((u - u0) / tour)
            couche[boucle].uv = centre + Vector((replier(u), replier(v))) * par_metre


def _aire_plane(coins):
    return 0.5 * sum(a.x * b.y - b.x * a.y for a, b in zip(coins, coins[1:] + coins[:1]))


OURLET = (0.0015, 0.003, 0.005)


# La robe sans pèlerine s'arrêtait net à hauteur d'épaule, les manches dressées en ailerons : rognée dessous,
# elle reçoit un empiècement de son propre lin, tiré en rayons vers la base du cou, par-dessus robe, manches et épaules.
def empiecement(humain, robe, ecart=0.008, rangs=12, n=56):
    h = humain
    z_bas, z_haut = h.z_epaule - 0.055, h.z_cou - 0.05
    entiere = robe.copy()
    entiere.data = robe.data.copy()
    rogner(h, robe, z_bas + 0.01)
    surface = surface_de(h, [robe], h.visible & ~h.tete_ & ~h.main)
    cou = tranche(h, h.cou & h.visible, h.z_cou, 0.02)
    cy = 0.5 * (cou[:, 1].min() + cou[:, 1].max())
    portee = 0.6
    pivots, directions, rayons = [], [], np.zeros((rangs, n))
    for k in range(rangs):
        u = k / (rangs - 1)
        phi = math.radians(62.0) * u
        pivots.append(Vector((0.0, cy, z_bas + (z_haut - z_bas) * u)))
        rang = []
        for j, th in enumerate(_angles(n)):
            dx, dy = _vers(th)
            d = Vector((dx * math.cos(phi), dy * math.cos(phi), math.sin(phi)))
            touche = surface.ray_cast(pivots[k] + d * portee, -d)[0]
            rayons[k, j] = portee - (touche - (pivots[k] + d * portee)).length if touche is not None else 0.08
            rang.append(d)
        directions.append(rang)
    # Le lin passe d'un relief à l'autre sans entrer dans les creux, entre bras et poitrine ; l'encolure, elle, colle au cou.
    ponts = np.max([np.roll(rayons, k, axis=1) for k in (-2, -1, 0, 1, 2)], axis=0)
    colle = np.array([G.lisse((rangs - 1 - k) / 3) for k in range(rangs)])[:, None]
    rayons = np.array([_lisser_cercle(r, 4 + 10 * (k >= rangs - 3)) for k, r in enumerate(ponts * colle + rayons * (1.0 - colle))])
    rayons[1:-1] = 0.25 * rayons[:-2] + 0.5 * rayons[1:-1] + 0.25 * rayons[2:]
    anneaux = [[pivots[k] + d * (rayons[k, j] + ecart) for j, d in enumerate(directions[k])] for k in range(rangs)]
    # L'ourlet est plaqué sur la robe entière : pas de marche, et le bord rogné reste dessous.
    lin_de_la_robe = surface_de(h, [entiere])
    for k, dehors in enumerate(OURLET):
        anneaux[k] = [lieu + normale * dehors for lieu, normale, _, _ in map(lin_de_la_robe.find_nearest, anneaux[k])]
    mm = Maillage()
    mm.nappe(anneaux, LIN, "voile")
    objet = lier(h, mm, f"{h.nom}_empiecement", robe.data.materials[0])
    # Un tour du cou vaut trois périodes du tissu replié : la couture du dos tombe sans raccord.
    tour = 1.2

    def autour_du_cou(p):
        dx, dy = p.x, p.y - cy
        return math.atan2(dx, -dy) / TOUR * tour, math.hypot(dx, dy) + z_haut - p.z

    uv_en_piece(h, objet, entiere, Vector((0.0, cy - 0.25, h.z_epaule - 0.12)), autour_du_cou, tour)
    bpy.data.meshes.remove(entiere.data)
    return objet
