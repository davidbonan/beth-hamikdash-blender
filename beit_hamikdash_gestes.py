"""Repère d'armature : devant = -Y, gauche = +X, haut = +Z. Une règle rend la matrice de son os à partir de sa base nulle."""
import math

import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Quaternion, Vector

TOUR = 2.0 * math.pi
DEVANT = Vector((0.0, -1.0, 0.0))
GAUCHE = Vector((1.0, 0.0, 0.0))
HAUT = Vector((0.0, 0.0, 1.0))
COUDE = Vector((-1.0, 0.0, 0.0))
GENOU = Vector((1.0, 0.0, 0.0))


def lisse(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


# Chaque oscillation fait un nombre entier de tours dans la boucle : la fin rejoint le début.
class Horloge:
    def __init__(self, duree):
        self.duree = duree

    def onde(self, t, periode, phase=0.0):
        tours = max(1, round(self.duree / periode))
        return math.sin(2.0 * math.pi * (tours * t / self.duree + phase))


class Squelette:
    def __init__(self, rig):
        self.rig = rig
        self.ordre = []

        def descendre(os_):
            self.ordre.append(os_)
            for enfant in os_.children:
                descendre(enfant)

        for os_ in rig.data.bones:
            if os_.parent is None:
                descendre(os_)
        self.repos = {b.name: b.matrix_local.copy() for b in self.ordre}
        self.relatif = {b.name: (b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local.copy())
                        for b in self.ordre}
        self.parent = {b.name: b.parent.name if b.parent else None for b in self.ordre}
        self.longueur = {b.name: b.length for b in self.ordre}

    def tete(self, nom):
        return self.repos[nom].translation.copy()

    def queue(self, nom):
        return self.repos[nom] @ Vector((0.0, self.longueur[nom], 0.0))

    def resoudre(self, regles):
        poses, bases = {}, {}
        for os_ in self.ordre:
            nom = os_.name
            parent = self.parent[nom]
            propagee = poses[parent] @ self.relatif[nom] if parent else self.repos[nom].copy()
            regle = regles.get(nom)
            pose = regle(propagee, poses) if regle else propagee
            poses[nom] = pose
            bases[nom] = propagee.inverted() @ pose
        return poses, bases


def tourner(m, axe, angle, pivot=None):
    if not angle:
        return m
    pivot = m.translation.copy() if pivot is None else pivot
    return Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, axe) @ Matrix.Translation(-pivot) @ m


def orienter(m, rotation):
    r = rotation.to_matrix().to_4x4() if isinstance(rotation, Quaternion) else rotation.to_4x4()
    sortie = r @ m.to_3x3().to_4x4()
    sortie.translation = m.translation
    return sortie


def viser(m, cible, torsion=0.0):
    tete = m.translation
    d = cible - tete
    if d.length < 1e-6:
        return m
    d.normalize()
    y = m.col[1].to_3d().normalized()
    sortie = orienter(m, y.rotation_difference(d))
    return orienter(sortie, Quaternion(d, torsion)) if torsion else sortie


def deux_os(racine, cible, l1, l2, pole):
    d = cible - racine
    distance = min(max(d.length, abs(l1 - l2) + 1e-4), (l1 + l2) * 0.9995)
    u = d.normalized()
    a = (l1 * l1 + distance * distance - l2 * l2) / (2.0 * distance)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = pole - u * pole.dot(u)
    p = p.normalized() if p.length > 1e-6 else u.orthogonal().normalized()
    return racine + u * a + p * h, racine + u * distance


def lire(valeur, poses):
    return valeur(poses) if callable(valeur) else valeur


def rouler(m, actuelle, voulue, part=1.0):
    axe = m.col[1].to_3d().normalized()
    a = actuelle - axe * actuelle.dot(axe)
    b = voulue - axe * voulue.dot(axe)
    if a.length < 1e-5 or b.length < 1e-5:
        return m
    angle = a.normalized().angle(b.normalized())
    if a.cross(b).dot(axe) < 0.0:
        angle = -angle
    return tourner(m, axe, angle * part)


# Viser seul laisse la torsion de l'os au hasard : `charniere`, normale du plan de flexion au repos, la fixe.
def chaine(squelette, haut, bas, cible, pole, charniere):
    etat = {}

    def plier(m, os_):
        premier, second = etat["milieu"] - etat["racine"], etat["bout"] - etat["milieu"]
        normale = premier.cross(second)
        pli = normale.length / max(premier.length * second.length, 1e-9)
        locale = squelette.repos[os_].to_3x3().inverted() @ charniere
        return rouler(m, m.to_3x3() @ locale, normale, lisse(pli / 0.15))

    def regle_haut(propagee, poses):
        racine = propagee.translation.copy()
        milieu, bout = deux_os(racine, lire(cible, poses), squelette.longueur[haut],
                               squelette.longueur[bas], lire(pole, poses))
        etat.update(racine=racine, milieu=milieu, bout=bout)
        return plier(viser(propagee, milieu), haut)

    def regle_bas(propagee, poses):
        return plier(viser(propagee, etat["bout"]), bas)

    return {haut: regle_haut, bas: regle_bas}


# Deux règles sur un même os s'enchaînent dans l'ordre donné.
def composer(*groupes):
    sortie = {}
    for groupe in groupes:
        for nom, regle in groupe.items():
            if nom in sortie:
                avant = sortie[nom]
                sortie[nom] = (lambda a, b: lambda m, poses: b(a(m, poses), poses))(avant, regle)
            else:
                sortie[nom] = regle
    return sortie


LATERAL = Vector((0.0, 1.0, 0.0))
DOIGTS = ("index", "middle", "ring", "pinky")
APPUI = 0.62


class Acteur:
    def __init__(self, squelette, sol):
        sq = self.sq = squelette
        self.sol = sol
        self.cheville = {c: sq.tete(f"foot_{c}") for c in "lr"}
        self.balle = {c: sq.tete(f"ball_{c}") for c in "lr"}
        self.orteil = {c: sq.queue(f"ball_{c}") for c in "lr"}
        self.poignet = {c: sq.tete(f"hand_{c}") for c in "lr"}
        self.epaule = {c: sq.tete(f"upperarm_{c}") for c in "lr"}
        self.bassin = sq.tete("pelvis")
        self.nuque = sq.tete("neck_01")
        self.paume, self.jointure = {}, {}
        for c, s in (("l", 1.0), ("r", -1.0)):
            long_doigt = (sq.tete(f"middle_02_{c}") - sq.tete(f"middle_01_{c}")).normalized()
            travers = (sq.tete(f"index_01_{c}") - sq.tete(f"pinky_01_{c}")).normalized()
            normale = long_doigt.cross(travers).normalized()
            if normale.x * -s < 0.0:
                normale = -normale
            self.paume[c] = normale
            self.jointure[c] = long_doigt

    def au(self, os_, point):
        inverse = self.sq.repos[os_].inverted()
        return lambda poses: poses[os_] @ (inverse @ point)

    def repere(self, os_, matrice):
        passage = self.sq.repos[os_].inverted() @ matrice
        return lambda poses: poses[os_] @ passage

    def dans(self, os_, poses, vecteur):
        return poses[os_].to_3x3() @ (self.sq.repos[os_].to_3x3().inverted() @ vecteur)


def bassin(decalage=Vector(), lacet=0.0, tangage=0.0, roulis=0.0):
    def regle(m, poses):
        m = tourner(tourner(tourner(m, HAUT, lacet), GAUCHE, tangage), LATERAL, roulis)
        return Matrix.Translation(decalage) @ m
    return {"pelvis": regle}


def buste(flexion=0.0, inclinaison=0.0, torsion=0.0, parts=(0.25, 0.35, 0.40)):
    regles = {}
    for nom, part in zip(("spine_01", "spine_02", "spine_03"), parts):
        regles[nom] = (lambda p: lambda m, poses: tourner(tourner(tourner(m, GAUCHE, flexion * p),
                                                                  LATERAL, inclinaison * p), HAUT, torsion * p))(part)
    return regles


def tete(flexion=0.0, lacet=0.0, inclinaison=0.0):
    regles = {}
    for nom, part in (("neck_01", 0.4), ("head", 0.6)):
        regles[nom] = (lambda p: lambda m, poses: tourner(tourner(tourner(m, HAUT, lacet * p), GAUCHE, flexion * p),
                                                          LATERAL, inclinaison * p))(part)
    return regles


# `tangage` > 0 lève la pointe autour du talon, ou le talon autour de la balle.
def pied(acteur, cote, decalage=Vector(), tangage=0.0, pivot="talon", sol=0.0):
    a = acteur
    points = [a.cheville[cote], a.balle[cote], a.orteil[cote]]
    points = [p + decalage + Vector((0.0, 0.0, sol)) for p in points]
    if tangage:
        centre = points[1] if pivot == "balle" else Vector((points[0].x, points[0].y + 0.05, a.sol + decalage.z + sol))
        r = Matrix.Rotation(-tangage if pivot == "talon" else tangage, 3, GAUCHE)
        points = [centre + r @ (p - centre) for p in points]
    cheville, balle, orteil = points
    s = 1.0 if cote == "l" else -1.0
    regles = chaine(a.sq, f"thigh_{cote}", f"calf_{cote}", cheville, DEVANT + GAUCHE * (0.15 * s), GENOU)
    regles[f"foot_{cote}"] = lambda m, poses: viser(m, balle)
    regles[f"ball_{cote}"] = lambda m, poses: viser(m, orteil)
    return regles


def bras(acteur, cote, cible, pole=None):
    s = 1.0 if cote == "l" else -1.0
    pole = pole or (lambda poses: acteur.dans("spine_03", poses, Vector((0.3 * s, 1.0, -0.3))))
    return chaine(acteur.sq, f"upperarm_{cote}", f"lowerarm_{cote}", cible, pole, COUDE)


def bras_ballant(acteur, cote, avance=0.0, ecart=0.0, hauteur=0.0):
    s = 1.0 if cote == "l" else -1.0
    point = acteur.poignet[cote] + DEVANT * avance + GAUCHE * (s * ecart) + HAUT * hauteur
    return bras(acteur, cote, acteur.au("spine_03", point))


def paume(acteur, cote, direction):
    def regle(m, poses):
        actuelle = acteur.dans(f"hand_{cote}", {f"hand_{cote}": m}, acteur.paume[cote])
        return rouler(m, actuelle, lire(direction, poses))
    return {f"hand_{cote}": regle}


def doigts(acteur, cote, flexion=0.35, pouce=0.15):
    regles = {}
    for doigt in DOIGTS + ("thumb",):
        for k in (1, 2, 3):
            nom = f"{doigt}_{k:02d}_{cote}"
            angle = (pouce if doigt == "thumb" else flexion) * (0.7 if k == 1 else 1.0)

            def regle(m, poses, angle=angle):
                d = acteur.dans(f"hand_{cote}", poses, acteur.jointure[cote])
                n = acteur.dans(f"hand_{cote}", poses, acteur.paume[cote])
                return tourner(m, d.cross(n).normalized(), angle)
            regles[nom] = regle
    return regles


def respiration(horloge, t, ampleur=0.012, periode=4.2, phase=0.0):
    return buste(flexion=-ampleur * horloge.onde(t, periode, phase), parts=(0.0, 0.3, 0.7))


def balancement(t, battement, ampleur=1.0, retard=0.0):
    b = t / battement - retard
    cote = math.sin(math.pi * b)
    creux = 0.5 - 0.5 * math.cos(TOUR * b)
    return composer(bassin(Vector((0.018 * ampleur * cote, 0.0, -0.012 * ampleur * creux)), roulis=0.020 * ampleur * cote),
                    buste(inclinaison=-0.035 * ampleur * cote, flexion=0.025 * ampleur * creux),
                    tete(inclinaison=0.045 * ampleur * math.sin(math.pi * b - 0.4), flexion=0.05 * ampleur * creux))


# `phase` couvre deux pas ; `sol(cote, decalage)` relève un pied posé plus haut.
def marche(acteur, phase, foulee, sol=None, levee=0.075):
    regles = []
    for cote, decal in (("l", 0.0), ("r", 0.5)):
        p = (phase + decal) % 1.0
        if p < APPUI:
            u = p / APPUI
            avance = foulee * APPUI * (0.5 - u)
            hauteur = 0.0
            if u < 0.15:
                tangage, pivot = 0.22 * (1.0 - lisse(u / 0.15)), "talon"
            else:
                tangage, pivot = 0.50 * lisse((u - 0.70) / 0.30), "balle"
        else:
            u = (p - APPUI) / (1.0 - APPUI)
            avance = foulee * APPUI * (lisse(u) - 0.5)
            hauteur = levee * math.sin(math.pi * u)
            if u < 0.45:
                tangage, pivot = 0.50 * (1.0 - lisse(u / 0.45)), "balle"
            else:
                tangage, pivot = 0.22 * lisse((u - 0.55) / 0.45), "talon"
        decalage = DEVANT * avance + HAUT * hauteur
        regles.append(pied(acteur, cote, decalage, tangage, pivot, sol(cote, decalage) if sol else 0.0))
    c = math.cos(TOUR * phase)
    regles.append(bassin(Vector((0.017 * math.cos(TOUR * (phase - 0.3)), 0.0,
                                 -0.024 * (0.5 + 0.5 * math.cos(2.0 * TOUR * phase)))), lacet=-0.07 * c, roulis=0.03 * c))
    regles.append(buste(flexion=0.04, torsion=0.10 * c))
    regles.append(bras_ballant(acteur, "l", avance=-0.15 * c, ecart=0.025))
    regles.append(bras_ballant(acteur, "r", avance=0.15 * c, ecart=0.025))
    regles.append(doigts(acteur, "l"))
    regles.append(doigts(acteur, "r"))
    return composer(*regles)


def debout(acteur, horloge, t, graine=0.0, regard=0.10):
    report = horloge.onde(t, 7.3, graine)
    return composer(
        pied(acteur, "l"), pied(acteur, "r"),
        bassin(Vector((0.012 * report, 0.0, -0.004 * abs(report))), roulis=0.012 * report),
        respiration(horloge, t, phase=graine),
        tete(flexion=0.03 * horloge.onde(t, 9.1, graine + 0.3), lacet=regard * horloge.onde(t, 11.7, graine + 0.6)))


class Enregistreur:
    def __init__(self, rig, squelette, nom):
        self.rig, self.squelette, self.nom = rig, squelette, nom
        self.cles = {b.name: ([], [], []) for b in squelette.ordre}
        self.objet = ([], [], [])

    def image(self, trame, bases, place=None):
        for nom, base in bases.items():
            positions, rotations, trames = self.cles[nom]
            positions.append(base.translation.copy())
            rotations.append(base.to_quaternion())
            trames.append(trame)
        if place is not None:
            positions, rotations, trames = self.objet
            positions.append(place.translation.copy())
            rotations.append(place.to_quaternion())
            trames.append(trame)

    def ecrire(self):
        rig = self.rig
        action = bpy.data.actions.new(self.nom)
        rig.animation_data_create()
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots.new(id_type="OBJECT", name=rig.name)
        sac = anim_utils.action_ensure_channelbag_for_slot(action, rig.animation_data.action_slot)
        for b in self.squelette.ordre:
            rig.pose.bones[b.name].rotation_mode = "QUATERNION"
        for nom, (positions, rotations, trames) in self.cles.items():
            chemin = f'pose.bones["{nom}"]'
            self._courbes(sac, chemin, nom, positions, rotations, trames)
        positions, rotations, trames = self.objet
        if trames:
            rig.rotation_mode = "QUATERNION"
            self._courbes(sac, "", "Objet", positions, rotations, trames)
        return action

    @staticmethod
    def _courbes(sac, chemin, groupe, positions, rotations, trames):
        prefixe = chemin + "." if chemin else ""
        for k, q in enumerate(rotations[1:], 1):
            if q.dot(rotations[k - 1]) < 0.0:
                rotations[k] = -q
        immobile = all((p - positions[0]).length < 1e-5 for p in positions)
        canaux = [] if immobile and chemin else [("location", i, [p[i] for p in positions]) for i in range(3)]
        canaux += [("rotation_quaternion", i, [q[i] for q in rotations]) for i in range(4)]
        for propriete, indice, valeurs in canaux:
            courbe = sac.fcurves.new(prefixe + propriete, index=indice, group_name=groupe)
            courbe.keyframe_points.add(len(trames))
            co = [0.0] * (2 * len(trames))
            co[0::2], co[1::2] = trames, valeurs
            courbe.keyframe_points.foreach_set("co", co)
            courbe.keyframe_points.foreach_set("interpolation", [1] * len(trames))
            courbe.update()
