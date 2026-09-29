import bpy
import numpy as np
from mathutils import Matrix, Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA

from .maillage import Maillage
from .habillage import porter
from .mise_en_scene import IMAGES, cap_vers, pas_de_marche, placement
from .danse import danse


def animer_sur_place(h, role, sol):
    a = G.Acteur(h.squelette, h.sol)
    horloge = G.Horloge(role.duree)
    x, y = role.ou[0] * AMA, role.ou[1] * AMA
    place = placement(x, y, sol, cap_vers(role.cap), h.sol)
    h.rig.matrix_world = place
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
    tenus = [[] for _ in role.accessoires]
    images = round(role.duree * IMAGES)
    for f in range(images + 1):
        t = f / IMAGES
        poses, bases = a.sq.resoudre(role.geste(h, a, horloge, t))
        rec.image(f, bases)
        tenir_image(h, a, role, horloge, t, poses, tenus)
    rec.ecrire()
    ecrire_accessoires(h, role, tenus)
    return [place]


def tenir_image(h, a, role, horloge, t, poses, tenus):
    for accessoire, suite in zip(role.accessoires, tenus):
        suite.append(accessoire.matrice(h, a, horloge, t, poses))


def ecrire_accessoires(h, role, tenus):
    for accessoire, suite in zip(role.accessoires, tenus):
        mm = Maillage()
        accessoire.construire(mm, Matrix.Identity(4))
        G.Enregistreur.objet(porter(h, mm, f"{h.nom}_{accessoire.nom}"), suite)


def animer_en_marche(h, role, terrain):
    a = G.Acteur(h.squelette, h.sol)
    trajet = role.trajet
    longueur = trajet.longueur
    foulee = longueur / max(1, round(longueur / role.foulee))
    images = round(longueur / role.vitesse * IMAGES)
    vitesse = longueur * IMAGES / images
    horloge = G.Horloge(images / IMAGES)
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
    tenus = [[] for _ in role.accessoires]
    places = []
    for f in range(images + 1):
        t = f / IMAGES
        s = (vitesse * t) % longueur
        p = trajet.en(s)
        g = terrain(p.x, p.y)
        place = placement(p.x, p.y, g, trajet.direction(s), h.sol)

        def sol(cote, decalage, place=place, g=g):
            pied = place @ (a.cheville[cote] + decalage)
            return terrain(pied.x, pied.y) - g

        regles = pas_de_marche(h, a, horloge, t, (s / foulee) % 1.0, foulee, sol)
        if role.geste:
            regles = G.composer(regles, role.geste(h, a, horloge, t))
        poses, bases = a.sq.resoudre(regles)
        rec.image(f, bases, place)
        tenir_image(h, a, role, horloge, t, poses, tenus)
        if f % IMAGES == 0:
            places.append(place)
    h.rig.matrix_world = places[0]
    rec.ecrire()
    ecrire_accessoires(h, role, tenus)
    return places


# Les pieds posés restent où ils sont sur la dalle : la racine suit leur milieu, face au centre.
def animer_en_danse(h, role, terrain):
    a = G.Acteur(h.squelette, h.sol)
    hora = role.trajet
    images = round(hora.duree * IMAGES)
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
    horloge = G.Horloge(images / IMAGES)
    tenus = [[] for _ in role.accessoires]
    places = []
    for f in range(images + 1):
        b = hora.pas.temps * f / images
        traces = {c: hora.pas.pied(c, b) for c in "lr"}
        racine = hora.monde(sum(p[0] for p in traces.values()) / 2, sum(p[1] for p in traces.values()) / 2)
        g = terrain(racine.x, racine.y)
        place = placement(racine.x, racine.y, g, hora.centre - racine, h.sol)
        inverse = place.inverted()
        pieds = {}
        for c, (x, y, hauteur, envol) in traces.items():
            dalle = hora.monde(x, y)
            local = inverse @ Vector((dalle.x, dalle.y, 0.0))
            pieds[c] = (Vector((local.x - a.cheville[c].x, local.y - a.cheville[c].y,
                                hauteur + terrain(dalle.x, dalle.y) - g)), envol)
        poses, bases = a.sq.resoudre(danse(h, a, hora, b, pieds))
        rec.image(f, bases, place)
        tenir_image(h, a, role, horloge, f / IMAGES, poses, tenus)
        if f % IMAGES == 0:
            places.append(place)
    h.rig.matrix_world = places[0]
    rec.ecrire()
    ecrire_accessoires(h, role, tenus)
    return places


# Mesurée sur la pose de la première image, avec ce que la figure porte : couché, un corps sort de sa boîte debout.
def points_poses(h):
    bpy.context.scene.frame_set(0)
    graphe = bpy.context.evaluated_depsgraph_get()
    points = []
    for objet in (o for o in h.rig.children if o.type == "MESH"):
        evalue = objet.evaluated_get(graphe)
        me = evalue.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        evalue.to_mesh_clear()
        passage = np.array(objet.matrix_local)
        co = co.reshape(-1, 3) @ passage[:3, :3].T + passage[:3, 3]
        points.append(co)
    return np.vstack(points)


def emprise(h, places):
    poses = points_poses(h)
    bas, haut = poses.min(axis=0) - 0.15, poses.max(axis=0) + 0.15
    coins = [Vector((x, y, z)) for x in (bas[0], haut[0]) for y in (bas[1], haut[1]) for z in (bas[2], haut[2])]
    points = [place @ c for place in places for c in coins]
    return ([min(p.x for p in points), min(p.z for p in points), -max(p.y for p in points)],
            [max(p.x for p in points), max(p.z for p in points), -min(p.y for p in points)])


def unir(boites):
    return {"min": [min(b[0][k] for b in boites) for k in range(3)], "max": [max(b[1][k] for b in boites) for k in range(3)]}
