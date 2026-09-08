"""Exporte la scène sauvegardée vers la visite interactive du dossier `visite/`.

    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
        -P beit_hamikdash_visite.py

Comme `beit_hamikdash_inspect.py`, ce script **lit** le .blend et ne le réécrit
jamais : il détruit sa copie en mémoire (fusion des volumes, aplatissement des
matières) puis quitte. Ne jamais y appeler `wm.save_mainfile`.

Il produit deux fichiers :
    visite/temple.glb    la géométrie, un maillage par concept
    visite/reperes.json  l'emprise de chaque concept et les points d'entrée

Le lien géométrie ↔ encyclopédie passe par `visite/concepts.json` : chaque concept y
déclare les préfixes de noms d'objets qui lui appartiennent, le préfixe le plus long
gagnant. Les volumes d'un même concept sont fusionnés en un seul maillage — 7 000
objets deviennent une soixantaine —, ce qui donne au navigateur autant de dessins
qu'il y a de choses à nommer, et fait du clic un concept plutôt qu'une des cinq
boîtes d'un mur percé.
"""
import json
import pathlib
import re
import sys
import bpy

RACINE = pathlib.Path(__file__).resolve().parent
DOSSIER = RACINE / "visite"
AMA = 0.48

# Le peuple, la fumée et les accessoires de plan sont une mise en scène, pas le
# bâtiment ; le pays et les caméras ne se visitent pas.
COLLECTIONS = ("00_HarHabayit", "10_EzratNashim", "20_Azara", "30_Mizbeach", "40_Ulam",
               "50_Heikhal", "60_KodeshHakodashim", "65_Aron", "70_Kelim", "80_Lishkot")

# Points d'entrée, en amot, au niveau du sol — la hauteur d'œil est ajoutée par le
# navigateur. `vers` est le cap en degrés, 180 = plein ouest, l'axe du parcours.
REPERES = [
    ("har_habayit",       "Har HaBayit, sur l'axe est",   250.0,   0.0, -13.5, 180),
    ("ezrat_nashim",      "Ezrat Nashim",                  90.0,   0.0,  -7.5, 180),
    ("quinze_marches",    "Pied des quinze marches",       26.0,   0.0,  -7.5, 180),
    ("azara",             "Ezrat Israël",                 -14.0,   0.0,   0.0, 180),
    ("mizbeach",          "Devant le Mizbea'h",           -17.0,  -9.0,   0.0, 180),
    ("kiyor",             "Au Kiyor",                     -55.0,  -8.0,   0.0, 180),
    ("oulam",             "Sous l'Oulam",                 -86.0,   0.0,   6.0, 180),
    ("heikhal",           "Dans le Heikhal",             -112.0,   0.0,   6.0, 180),
    ("kodesh_hakodashim", "Kodesh HaKodashim",           -143.0,   0.0,   6.0, 180),
]


def concepts():
    """(préfixe, id) du plus long au plus court : le préfixe le plus précis gagne."""
    fiche = json.loads((DOSSIER / "concepts.json").read_text(encoding="utf-8"))
    regles = [(p, c["id"]) for c in fiche["concepts"] for p in c["prefixes"]]
    return sorted(regles, key=lambda r: -len(r[0]))


def concept_de(nom, regles):
    for prefixe, ident in regles:
        if nom.startswith(prefixe):
            return ident
    return None


def aplatir(mat):
    """Remplace l'arbre procédural par la seule couleur qu'il tire du Principled.

    Les matières du blockout sont lues en coordonnées de monde et se recalculent à
    chaque point ; glTF n'a pas de nœuds. La couleur de base, le métal et la rugosité
    restent lisibles dans les valeurs par défaut des entrées, même quand un lien les
    recouvre — c'est ce qui reste ici, et c'est exactement le gris de blockout.
    """
    if not mat or not mat.use_nodes:
        return
    bsdf = next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        return
    valeurs = {clef: tuple(bsdf.inputs[clef].default_value) if clef == "Base Color"
               else bsdf.inputs[clef].default_value
               for clef in ("Base Color", "Metallic", "Roughness")}
    arbre = mat.node_tree
    arbre.nodes.clear()
    sortie = arbre.nodes.new("ShaderNodeOutputMaterial")
    neuf = arbre.nodes.new("ShaderNodeBsdfPrincipled")
    arbre.links.new(neuf.outputs["BSDF"], sortie.inputs["Surface"])
    for clef, valeur in valeurs.items():
        neuf.inputs[clef].default_value = valeur
    mat.diffuse_color = valeurs["Base Color"]


def fusionner(nom, objets):
    """Un seul maillage pour tout un concept, portant son identifiant en propriété."""
    tete = objets[0]
    if len(objets) > 1:
        with bpy.context.temp_override(active_object=tete, selected_editable_objects=objets):
            bpy.ops.object.join()
    tete.name = nom
    tete.data.name = nom
    tete["concept"] = nom
    return tete


def bornes(obj):
    """Emprise du maillage en repère glTF (Y vers le haut), en mètres."""
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not points:
        return None
    bas = [min(p[k] for p in points) for k in range(3)]
    haut = [max(p[k] for p in points) for k in range(3)]
    return {"min": [bas[0], bas[2], -haut[1]], "max": [haut[0], haut[2], -bas[1]]}


def main():
    DOSSIER.mkdir(exist_ok=True)
    regles = concepts()
    connus = {ident for _, ident in regles}

    gardes = {o for nom in COLLECTIONS if (c := bpy.data.collections.get(nom))
              for o in c.objects if o.type == "MESH"}
    for o in list(bpy.data.objects):
        if o not in gardes:
            bpy.data.objects.remove(o, do_unlink=True)

    groupes, orphelins = {}, []
    for o in gardes:
        ident = concept_de(o.name, regles)
        if ident is None:
            orphelins.append(o.name)
            ident = "_non_classe"
        groupes.setdefault(ident, []).append(o)

    for mat in bpy.data.materials:
        aplatir(mat)

    emprises = {}
    for ident in sorted(groupes):
        objets = sorted(groupes[ident], key=lambda o: o.name)
        fusionne = fusionner(ident, objets)
        emprises[ident] = bornes(fusionne)
        print(f"  {ident:26s} {len(objets):5d} volumes")

    bpy.ops.export_scene.gltf(
        filepath=str(DOSSIER / "temple.glb"),
        export_format="GLB",
        export_extras=True,
        export_yup=True,
        # Les 5 960 modificateurs Bevel du blockout adoucissent les arêtes pour les
        # passes Normal de l'i2i ; les appliquer ici fait passer la scène de 132 000
        # à 743 000 faces et le fichier de 5 à 76 Mo, pour un chanfrein de 3 cm
        # invisible à hauteur d'homme. La visite prend donc la géométrie nue.
        export_apply=False,
        export_cameras=False,
        export_lights=False,
        export_materials="EXPORT",
        # Les normales pèsent, mais `shadow.normalBias` n'a rien pour décaler sans
        # elles : la carte d'ombre se mord alors elle-même, et l'intérieur du Heikhal
        # se couvre d'un damier clair/sombre à l'échelle du texel.
        export_normals=True,
        export_texcoords=False,
        export_skins=False,
        export_animations=False,
    )

    (DOSSIER / "reperes.json").write_text(json.dumps({
        "ama": AMA,
        "emprises": emprises,
        "entrees": [{"id": i, "nom": n, "position": [x * AMA, z * AMA, -y * AMA], "cap": cap}
                    for i, n, x, y, z, cap in REPERES],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    absents = sorted(connus - set(groupes))
    if orphelins:
        # Le blockout grossit : ce relevé est la liste de ce qu'il reste à déclarer
        # dans concepts.json, et la seule chose qui empêche un ajout de disparaître
        # silencieusement dans un maillage anonyme.
        racines = {}
        for nom in orphelins:
            racines["_".join(re.sub(r"\d+", "#", nom).split("_")[:3])] = \
                racines.get("_".join(re.sub(r"\d+", "#", nom).split("_")[:3]), 0) + 1
        print(f"\n{len(orphelins)} volumes sans concept, versés dans _non_classe :")
        for racine, combien in sorted(racines.items(), key=lambda r: -r[1]):
            print(f"    {racine:44s} {combien:5d}")
    if absents:
        print(f"\n{len(absents)} concepts déclarés sans géométrie : {', '.join(absents)}")
    taille = (DOSSIER / "temple.glb").stat().st_size / 1e6
    print(f"\n{len(groupes)} maillages · temple.glb {taille:.1f} Mo")


main()
