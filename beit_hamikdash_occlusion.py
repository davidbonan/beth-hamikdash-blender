"""Cuit dans Cycles, par concept de la visite, l'occlusion du ciel (visite/occlusion/) ou la lumière indirecte (visite/lumiere/), sur la couche UV « Occlusion »."""
import math
import pathlib
import subprocess
import tempfile
import time

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

VISITE = pathlib.Path(__file__).resolve().parent / "visite"
COUCHE = "Occlusion"

# Plus fin qu'un texel (barreaux, treillis du soreg), un objet prend l'ombre de ses faces cachées et vire au noir.
AIRE_MIN = 50.0
TEXELS_PAR_FACE_MIN = 10
TEXEL = 0.2
TAILLE = (128, 2048)
ECHANTILLONS = 256
PORTEE = 8.0
# La sonde de visite/sonde.js écarte déjà le ciel du Heikhal : une portée longue y éteindrait la Menora.
PORTEE_SOUS_SONDE = 3.0
SOUS_SONDE = {"heikhal", "parokhet"}
# Sa pénombre (matieres.js) suffit ; cuites, ses parois s'assombriraient et pas les plaques de sculptures_murs.
# Celles-ci sont à cheval sur le Heikhal et le KhK : une seule carte pour les deux les mettrait en désaccord.
EXCLUS = {"kodesh_hakodashim", "sculptures_murs"}
# Deux faces collées se disputent la profondeur : la cachée cuit noire et perce, mouchetée, sur les GPU mobiles.
COLLEE = 0.01
PARALLELE = 0.99
TOLERANCE = 0.0005
RETRAIT = 0.98
PAS_TEMOIN = 0.25
PAS_MAX = 128

# Le soleil de visite/visite.js et le ciel vu de visite/ciel.js, en repère Blender : (x, y, z) three = (x, z, -y).
SOLEIL = Vector((150.0, -55.0, 58.0)).normalized()
SOLEIL_COULEUR = 0xFFD6A0
SOLEIL_FORCE = 4.9
DIAMETRE_SOLEIL = 0.0093
CIEL = {"haut": 0x4D7FB8, "bas": 0xD8DCD4, "sol": 0xA89C86, "horizon": 6.0}
# Ciel clair, soleil à 20° : le ciel pose au sol de l'ordre du tiers de ce qu'y pose le soleil. Le dôme vu, lui, est réglé pour l'écran.
DIFFUS = 0.33
# Le bleu du dôme vu, entier, virait les ombres des cours au bleu franc.
SATURATION_CIEL = 0.5
# La Menora et les braises de visite/visite.js (candela, et le souffle moyen des braises) ; en repère three, comme reperes.json.
LAMPES = {"flammes": {"couleur": 0xFFB36B, "intensite": 150.0, "hauteur": 0.35},
          "braises": {"couleur": 0xFF7A2A, "intensite": 18.0 * 0.86, "hauteur": 0.0}}
# Albédo de la visite rapporté à celui de Cycles, mesuré en rendant les deux depuis la même caméra ; les autres matières sont à 3 % près.
ALBEDO_VISITE = {"Marbre_Herode": (1.12, 1.07, 1.07), "Sol": (1.11, 1.10, 1.09)}
ECHANTILLONS_REBONDS = 1024
# L'adaptatif s'arrête au bruit, pas au plafond : à 0.02 l'Ezrat Nashim cuit deux fois plus vite pour 1,7 niveau sRGB d'écart.
SEUIL_REBONDS = 0.02
TOUS = "tout"
# Un rayon réfléchi par l'or vers la pierre tombe rarement, et fort : sans borne il laisse des étincelles dans la carte.
BORNE_INDIRECTE = 4.0


def aire(obj):
    echelle = obj.matrix_world.to_scale()
    return sum(p.area for p in obj.data.polygons) * abs(echelle.x * echelle.y * echelle.z) ** (2 / 3)


# Le texel de 20 cm dit la taille ; un concept fin la relève jusqu'à tenir ses TEXELS_PAR_FACE_MIN, et n'est écarté que si le plafond n'y suffit plus.
def taille_de(surface, faces):
    pour_faces = math.sqrt(faces * TEXELS_PAR_FACE_MIN)
    voulue = 2 ** math.ceil(math.log2(max(math.sqrt(surface) / TEXEL, pour_faces, 1)))
    return min(max(voulue, TAILLE[0]), TAILLE[1])


def retenus(fusionnes):
    for ident, obj in sorted(fusionnes.items()):
        surface = aire(obj)
        taille = taille_de(surface, obj["faces_sans_chanfrein"])
        if ident in EXCLUS or surface < AIRE_MIN:
            continue
        # Compté sans chanfrein : il multiplie les faces sans rendre l'objet plus fin.
        if taille * taille / obj["faces_sans_chanfrein"] < TEXELS_PAR_FACE_MIN:
            print(f"  écarté    {ident:26s} {obj['faces_sans_chanfrein']} faces pour {taille} px", flush=True)
            continue
        yield ident, obj, taille


def points_temoins(triangle):
    centre = sum(triangle, triangle[0] * 0) / 3
    a, b, c = (centre.lerp(coin, RETRAIT) for coin in triangle)
    pas = min(PAS_MAX, max(1, math.ceil(max((b - a).length, (c - a).length) / PAS_TEMOIN)))
    for i in range(pas + 1):
        for j in range(pas + 1 - i):
            yield a + (b - a) * (i / pas) + (c - a) * (j / pas)


# Seules les faces tournées du même côté se disputent la profondeur ; dos à dos, chacune est dans le volume de l'autre.
class Collees:
    def __init__(self, objets):
        self.faces, self.face_de, self.origines, sommets, triangles = [], [], [], [], []
        for obj in objets:
            maillage = obj.data
            maillage.calc_loop_triangles()
            base, premiere = len(sommets), len(self.faces)
            sommets += [obj.matrix_world @ v.co for v in maillage.vertices]
            self.faces += [([], geometry.normal([sommets[base + i] for i in poly.vertices])) for poly in maillage.polygons]
            self.origines += [(obj, poly.index) for poly in maillage.polygons]
            for tri in maillage.loop_triangles:
                triangles.append([base + i for i in tri.vertices])
                self.face_de.append(premiere + tri.polygon_index)
                self.faces[premiere + tri.polygon_index][0].append([sommets[i] for i in triangles[-1]])
        self.aires = [sum(geometry.area_tri(*t) for t in triangles_) for triangles_, _ in self.faces]
        self.arbre = BVHTree.FromPolygons(sommets, triangles)
        self.retirees = set()

    def temoins(self, k):
        return (point for triangle in self.faces[k][0] for point in points_temoins(triangle))

    def couverte(self, k):
        return self.faces[k][1].length > 0 and all(self.couvrante(point, k) is not None for point in self.temoins(k))

    # Recouverte en partie seulement, elle reste ; la plus petite des deux recule derrière l'autre.
    def a_reculer(self, k):
        return self.faces[k][1].length > 0 and not self.mince(k) and any(
            (g := self.couvrante(point, k)) is not None and g[1] <= TOLERANCE and (self.aires[g[0]], -g[0]) > (self.aires[k], -k)
            for point in self.temoins(k))

    def mince(self, k):
        triangle, normale = self.faces[k][0][0], self.faces[k][1]
        centre = sum(triangle, triangle[0] * 0) / 3
        return self.arbre.ray_cast(centre - normale * TOLERANCE, -normale, 2 * COLLEE)[0] is not None

    def couvrante(self, point, k):
        normale = self.faces[k][1]
        for position, _, t, _ in self.arbre.find_nearest_range(point, COLLEE):
            g = self.face_de[t]
            if g == k or g in self.retirees or normale.dot(self.faces[g][1]) < PARALLELE:
                continue
            ecart = position - point
            devant = ecart.dot(normale)
            if -TOLERANCE <= devant <= COLLEE and (ecart - normale * devant).length <= TOLERANCE:
                return g, abs(devant)
        return None


def reculer(objets, collees, reculees):
    for obj in objets:
        vers_local = obj.matrix_world.inverted_safe().to_3x3()
        deplacements = {}
        for k in reculees:
            o, i = collees.origines[k]
            if o is obj:
                for sommet in obj.data.polygons[i].vertices:
                    deplacements[sommet] = deplacements.get(sommet, Vector()) - collees.faces[k][1] * COLLEE
        for sommet, deplacement in deplacements.items():
            obj.data.vertices[sommet].co += vers_local @ deplacement


def retirer(objets, collees):
    for obj in objets:
        indices = {i for k, (o, i) in enumerate(collees.origines) if o is obj and k in collees.retirees}
        maillage = bmesh.new()
        maillage.from_mesh(obj.data)
        maillage.faces.ensure_lookup_table()
        bmesh.ops.delete(maillage, geom=[maillage.faces[i] for i in indices], context="FACES_ONLY")
        maillage.to_mesh(obj.data)
        maillage.free()


def separer_collees(objets):
    collees = Collees(objets)
    for k in range(len(collees.faces)):
        if collees.couverte(k):
            collees.retirees.add(k)
    reculees = [k for k in range(len(collees.faces)) if k not in collees.retirees and collees.a_reculer(k)]
    reculer(objets, collees, reculees)
    retirer(objets, collees)
    print(f"  faces collées sur {len(collees.faces)} : {len(collees.retirees)} retirées, {len(reculees)} reculées de {COLLEE * 100:.0f} cm")


def preparer_cycles():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for appareil in prefs.devices:
        appareil.use = True
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = ECHANTILLONS
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Occlusion")


def lineaire(hexa):
    srgb = np.array([(hexa >> decalage & 0xFF) / 255 for decalage in (16, 8, 0)])
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def radiance_du_ciel(directions):
    hauteur = directions[:, 2:3]
    haut, bas, sol = (lineaire(CIEL[teinte]) for teinte in ("haut", "bas", "sol"))
    dessus = bas + (haut - bas) * np.clip(hauteur, 0.0, 1.0) ** 0.55
    dessous = bas + (sol - bas) * np.minimum(-hauteur * CIEL["horizon"], 1.0)
    vers_soleil = np.maximum(directions @ np.array(SOLEIL), 0.0)[:, None]
    halo = np.array([1.0, 0.84, 0.58]) * (0.10 * vers_soleil ** 4 + 0.45 * vers_soleil ** 160)
    radiance = np.where(hauteur > 0.0, dessus, dessous) + halo
    gris = (radiance @ [0.2126, 0.7152, 0.0722])[:, None]
    return gris + (radiance - gris) * SATURATION_CIEL


def poser_ciel(scene, largeur=1024):
    """Le ciel en image équirectangulaire, ramené à DIFFUS."""
    hauteur = largeur // 2
    azimut = (0.5 - (np.arange(largeur) + 0.5) / largeur) * 2 * np.pi
    elevation = ((np.arange(hauteur) + 0.5) / hauteur - 0.5) * np.pi
    az, el = np.meshgrid(azimut, elevation)
    directions = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], axis=-1).reshape(-1, 3)
    radiance = radiance_du_ciel(directions)
    angle_solide = (np.cos(el).ravel() * (2 * np.pi / largeur) * (np.pi / hauteur))[:, None]
    au_sol = (radiance * np.maximum(directions[:, 2:3], 0.0) * angle_solide).sum(axis=0) @ [0.2126, 0.7152, 0.0722]
    force = DIFFUS * SOLEIL_FORCE * SOLEIL.z / au_sol

    image = bpy.data.images.new("Ciel", largeur, hauteur, float_buffer=True, is_data=True)
    image.pixels.foreach_set(np.concatenate([radiance, np.ones((len(radiance), 1))], axis=1).astype(np.float32).ravel())
    monde = bpy.data.worlds.new("Ciel")
    monde.use_nodes = True
    arbre = monde.node_tree
    texture = arbre.nodes.new("ShaderNodeTexEnvironment")
    texture.image = image
    fond = arbre.nodes["Background"]
    fond.inputs["Strength"].default_value = force
    arbre.links.new(texture.outputs["Color"], fond.inputs["Color"])
    scene.world = monde
    print(f"  ciel à {force:.2f} fois le dôme vu : {au_sol * force:.2f} au sol contre {SOLEIL_FORCE * SOLEIL.z:.2f} de soleil")


def poser_soleil(scene):
    lampe = bpy.data.lights.new("Soleil", "SUN")
    lampe.energy = SOLEIL_FORCE
    lampe.color = tuple(lineaire(SOLEIL_COULEUR))
    lampe.angle = DIAMETRE_SOLEIL
    soleil = bpy.data.objects.new("Soleil", lampe)
    soleil.rotation_euler = SOLEIL.to_track_quat("Z", "Y").to_euler()
    scene.collection.objects.link(soleil)
    return soleil


# Une lampe ponctuelle de Cycles de P watts a l'intensité P / 4π : c'est ainsi qu'elle rend les candela de la visite.
def poser_lampes(scene, points):
    sources = []
    for nature, positions in points.items():
        if not positions:
            continue
        reglage = LAMPES[nature]
        x, y, z = np.mean(positions, axis=0)
        lampe = bpy.data.lights.new(nature, "POINT")
        lampe.energy = 4 * math.pi * reglage["intensite"]
        lampe.color = tuple(lineaire(reglage["couleur"]))
        lampe.shadow_soft_size = 0.0
        lampe.use_soft_falloff = False
        source = bpy.data.objects.new(nature, lampe)
        source.location = (x, -z, y + reglage["hauteur"])
        scene.collection.objects.link(source)
        sources.append(source)
    return sources


def accorder_matieres():
    """L'albédo de la visite, et aucune émission : les lampes de la visite sont posées à part, en lampes."""
    for mat in bpy.data.materials:
        if mat.node_tree is None:
            continue
        for noeud in mat.node_tree.nodes:
            if noeud.bl_idname == "ShaderNodeBsdfPrincipled":
                noeud.inputs["Emission Strength"].default_value = 0.0
            elif noeud.bl_idname == "ShaderNodeEmission":
                noeud.inputs["Strength"].default_value = 0.0
        facteur = ALBEDO_VISITE.get(mat.name)
        bsdf = next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if facteur is None or bsdf is None:
            continue
        entree = bsdf.inputs["Base Color"]
        produit = mat.node_tree.nodes.new("ShaderNodeMixRGB")
        produit.blend_type = "MULTIPLY"
        produit.inputs["Factor"].default_value = 1.0
        produit.inputs["Color2"].default_value = (*facteur, 1.0)
        if entree.links:
            mat.node_tree.links.new(entree.links[0].from_socket, produit.inputs["Color1"])
        else:
            produit.inputs["Color1"].default_value = entree.default_value
        mat.node_tree.links.new(produit.outputs["Color"], entree)


def eclairer(scene, points):
    """Ciel, soleil, lampes et matières de la cuisson de lumière ; renvoie les sources, éteintes."""
    poser_ciel(scene)
    sources = [poser_soleil(scene), *poser_lampes(scene, points)]
    for source in sources:
        source.hide_render = True
    accorder_matieres()
    scene.cycles.sample_clamp_indirect = BORNE_INDIRECTE
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    return sources


def deplier(obj, taille):
    obj.data.uv_layers.active = obj.data.uv_layers.new(name=COUCHE)
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=2.0 / taille, area_weight=0.0)
    bpy.ops.uv.pack_islands(margin=2.0 / taille, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return len(obj.data.uv_layers) - 1


def cuire(obj, image, **passe):
    noeuds = []
    for fente in obj.material_slots:
        if fente.material is None or fente.material.node_tree is None:
            continue
        arbre = fente.material.node_tree
        noeud = arbre.nodes.new("ShaderNodeTexImage")
        noeud.image = image
        arbre.nodes.active = noeud
        noeuds.append((arbre, noeud))
    bpy.ops.object.bake(margin=4, margin_type="EXTEND", use_clear=True, uv_layer=COUCHE, **passe)
    for arbre, noeud in noeuds:
        arbre.nodes.remove(noeud)
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(image.size[1], image.size[0], 4)


def cuire_occlusion_de(obj, taille, portee):
    bpy.context.scene.world.light_settings.distance = portee
    image = bpy.data.images.new(obj.name, taille, taille, float_buffer=True, is_data=True)
    pixels = cuire(obj, image, type="AO")
    bpy.data.images.remove(image)
    return pixels


# La passe Diffuse sans couleur rend E/π, et la lightMap de three attend l'irradiance E.
def cuire_lumiere_de(obj, taille, sources):
    """Le ciel qui arrive sans rebond, et tout ce qui rebondit, sources comprises ; leur lumière directe reste à la visite."""
    scene = bpy.context.scene
    seuil_scene = scene.cycles.adaptive_threshold
    scene.cycles.samples = ECHANTILLONS_REBONDS
    scene.cycles.adaptive_threshold = SEUIL_REBONDS
    image = bpy.data.images.new(obj.name, taille, taille, float_buffer=True, is_data=True)
    for source in sources:
        source.hide_render = False
    rebonds = cuire(obj, image, type="DIFFUSE", pass_filter={"INDIRECT"})[..., :3].copy()
    for source in sources:
        source.hide_render = True
    # Le ciel direct, échantillonné par importance, ne bouge plus au-delà de 256.
    scene.cycles.samples = ECHANTILLONS
    scene.cycles.adaptive_threshold = seuil_scene
    ciel = cuire(obj, image, type="DIFFUSE", pass_filter={"DIRECT"})[..., :3]
    bpy.data.images.remove(image)
    return math.pi * (rebonds + ciel)


# Cuite au double puis réduite : la réduction efface le bruit de Cycles, qui doublait le poids du WebP.
def ecrire_png(pixels, png):
    hauteur, largeur = pixels.shape[:2]
    sortie = bpy.data.images.new(png.stem, largeur, hauteur, is_data=True)
    sortie.pixels.foreach_set(np.clip(pixels, 0.0, 1.0).astype(np.float32).ravel())
    sortie.filepath_raw = str(png)
    sortie.file_format = "PNG"
    sortie.save()
    bpy.data.images.remove(sortie)


def ecrire(pixels, chemin, taille, brut):
    pixels = pixels.copy()
    pixels[..., 1:3] = pixels[..., :1]
    pixels[..., 3] = 1.0
    png = brut / f"{chemin.stem}.png"
    ecrire_png(pixels, png)
    subprocess.run(["cwebp", "-quiet", "-noalpha", "-resize", str(taille), str(taille), "-q", "85",
                    str(png), "-o", str(chemin)], check=True)


# Réduite en linéaire, avant l'encodage : moyenné après, le bruit de Cycles assombrirait la carte. Renvoie l'échelle à rendre à la visite.
def ecrire_lumiere(irradiance, chemin, brut):
    hauteur, largeur = irradiance.shape[:2]
    reduite = irradiance.reshape(hauteur // 2, 2, largeur // 2, 2, 3).mean(axis=(1, 3))
    echelle = max(math.ceil(np.percentile(reduite, 99.9) * 4) / 4, 0.25)
    relative = np.clip(reduite / echelle, 0.0, 1.0)
    srgb = np.where(relative <= 0.0031308, relative * 12.92, 1.055 * relative ** (1 / 2.4) - 0.055)
    png = brut / f"{chemin.stem}.png"
    ecrire_png(np.concatenate([srgb, np.ones((*srgb.shape[:2], 1))], axis=-1), png)
    subprocess.run(["cwebp", "-quiet", "-noalpha", "-sharp_yuv", "-q", "90", str(png), "-o", str(chemin)], check=True)
    return echelle


def garder_occlusions(gardees, ident):
    """La carte déjà cuite d'un concept ; valable tant que sa géométrie, donc son dépliage, n'a pas changé."""
    carte = gardees.get(ident)
    if carte is None or not (VISITE / carte["carte"]).exists():
        raise ValueError(f"{ident} n'a pas de carte d'occlusion à garder : relancer la cuisson complète")
    return carte


def cuire_occlusion(fusionnes, chantier, eclaires=frozenset(), gardees=None, lampes=None):
    """Cuit les concepts retenus dans `chantier`, en lumière indirecte ceux d'`eclaires` (TOUS pour tous) et en occlusion les autres.

    `gardees` (l'`occlusion` d'un reperes.json) garde ces cartes-là au lieu de les recuire : seule la lumière cuit.
    `lampes` : {"flammes": [...], "braises": [...]}, positions en repère three, dont le rebond se cuit aussi.
    Renvoie ({concept: {"carte", "canal"}}, {concept: {"carte", "canal", "echelle"}}) pour reperes.json."""
    choisis = list(retenus(fusionnes))
    if TOUS in eclaires:
        eclaires = {ident for ident, _, _ in choisis}
    inconnus = set(eclaires) - {ident for ident, _, _ in choisis}
    if inconnus:
        raise ValueError(f"lumière demandée sur des concepts qui ne se cuisent pas : {sorted(inconnus)}")
    occlusions, lumieres = {}, {}
    if gardees is not None:
        occlusions = {ident: garder_occlusions(gardees, ident) for ident, _, _ in choisis if ident not in eclaires}
    sortie, sortie_lumiere = chantier / "occlusion", chantier / "lumiere"
    sortie.mkdir(parents=True, exist_ok=True)
    sortie_lumiere.mkdir(parents=True, exist_ok=True)
    separer_collees([obj for _, obj, _ in choisis])
    preparer_cycles()
    sources = eclairer(bpy.context.scene, lampes or {}) if eclaires else []
    debut = time.time()
    with tempfile.TemporaryDirectory() as brut:
        for ident, obj, taille in choisis:
            canal = deplier(obj, 2 * taille)
            depart = time.time()
            if ident in eclaires:
                chemin = sortie_lumiere / f"{ident}.webp"
                echelle = ecrire_lumiere(cuire_lumiere_de(obj, 2 * taille, sources), chemin, pathlib.Path(brut))
                lumieres[ident] = {"carte": f"lumiere/{ident}.webp", "canal": canal, "echelle": echelle}
                print(f"  lumière   {ident:26s} {taille:5d} px  ×{echelle:.2f}  {chemin.stat().st_size / 1e3:5.0f} ko  {time.time() - depart:4.0f} s", flush=True)
            elif gardees is not None:
                if occlusions[ident]["canal"] != canal:
                    raise ValueError(f"{ident} : le dépliage a changé de canal, relancer la cuisson complète")
            else:
                portee = PORTEE_SOUS_SONDE if ident in SOUS_SONDE else PORTEE
                chemin = sortie / f"{ident}.webp"
                ecrire(cuire_occlusion_de(obj, 2 * taille, portee), chemin, taille, pathlib.Path(brut))
                occlusions[ident] = {"carte": f"occlusion/{ident}.webp", "canal": canal}
                print(f"  occlusion {ident:26s} {taille:5d} px  {portee:.0f} m  {chemin.stat().st_size / 1e3:5.0f} ko  {time.time() - depart:4.0f} s", flush=True)
    poids = sum(f.stat().st_size for dossier in (sortie, sortie_lumiere) for f in dossier.glob("*.webp")) / 1e6
    print(f"  {len(occlusions)} cartes d'occlusion, {len(lumieres)} de lumière, {poids:.1f} Mo, {time.time() - debut:.0f} s")
    return occlusions, lumieres
