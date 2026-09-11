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
import subprocess
import sys
import bpy

RACINE = pathlib.Path(__file__).resolve().parent
DOSSIER = RACINE / "visite"
AMA = 0.48

# Le peuple, la fumée et les accessoires de plan sont une mise en scène, pas le
# bâtiment ; le pays et les caméras ne se visitent pas.
COLLECTIONS = ("00_HarHabayit", "10_EzratNashim", "20_Azara", "30_Mizbeach", "40_Ulam",
               "50_Heikhal", "60_KodeshHakodashim", "65_Aron", "70_Kelim", "80_Lishkot")

# Les collections qui gardent leur chanfrein. Ce sont celles qu'on longe à bout de bras :
# une arête vive n'accroche aucune lumière, et c'est ce qui trahit le plus sûrement une
# maquette. Ailleurs — l'enceinte, les cours, la ville — on ne s'approche jamais assez
# pour que 3 cm se voient, et le chanfrein n'y serait qu'un tiers de fichier en plus.
CHANFREIN = ("30_Mizbeach", "40_Ulam", "50_Heikhal", "60_KodeshHakodashim",
             "65_Aron", "70_Kelim")

# En amot. `cadre` : concepts à montrer entiers ; sans `position`, le navigateur recule le long du `cap` (0 = est, 90 = nord).
Z_HAR, Z_EZN, Z_AZ, Z_BAT = -16.0, -10.0, 0.0, 6.0

REPERES = [
    dict(id="har_habayit", nom="Har HaBayit, sur l'axe est",
         position=(185.0, 0.0, Z_HAR), cadre=["oulam"]),
    dict(id="face_porte_est", nom="Face à la porte orientale",
         position=(165.0, 0.0, Z_HAR), cadre=["porte_est_ezrat_nashim"]),
    dict(id="ezrat_nashim", nom="Ezrat Nashim",
         position=(137.0, 0.0, Z_EZN), cadre=["oulam"]),
    dict(id="quinze_marches", nom="Pied des quinze marches",
         cadre=["quinze_marches", "shaar_nikanor"], cap=180, sol=Z_EZN, recul_max=40.0),
    dict(id="azara", nom="Ezrat Israël",
         position=(-14.0, 0.0, Z_AZ), cadre=["oulam"]),
    # Plein est, le recul bute sur les lishkot qui flanquent Nikanor ; seul, l'autel se lit comme un mur : avec son kevesh, depuis le sud-est.
    dict(id="mizbeach", nom="Devant le Mizbea'h",
         cadre=["mizbeach", "kevesh"], cap=135, sol=Z_AZ, recul_max=60.0),
    dict(id="kiyor", nom="Au Kiyor",
         cadre=["kiyor"], cap=135, sol=Z_AZ, recul_max=8.0),
    dict(id="oulam", nom="Sous l'Oulam",
         cadre=["portes_heikhal"], cap=180, sol=Z_BAT, recul_max=17.0),
    dict(id="heikhal", nom="Dans le Heikhal",
         cadre=["menora", "shulchan", "mizbeach_hazahav"], cap=180, sol=Z_BAT, recul_max=24.0),
    # Les badim touchent la parokhet (Yoma 54a) : l'Aron ne se voit entier que de flanc, depuis le mur sud.
    dict(id="kodesh_hakodashim", nom="Kodesh HaKodashim",
         cadre=["aron", "kaporet", "even_hashetiya"], cap=90, sol=Z_BAT, recul_max=9.0),
]

# Ce que « Un élément… » montre de `<id>` quand le recul automatique n'y suffit pas ; une cour ne tient entière qu'en vol.
VUES = [
    dict(id="vue_azara", cadre=["azara"], cap=180, sol=90.0, recul_max=300.0, vol=True),
    dict(id="vue_ezrat_nashim",
         cadre=["porte_est_ezrat_nashim", "lishkat_haetzim", "lishkat_hanezirim",
                "lishkat_hametzoraim", "lishkat_beit_shemanya", "quinze_marches"],
         cap=180, sol=60.0, recul_max=300.0, vol=True),
    dict(id="vue_heikhal", position=(-99.0, 0.0, Z_BAT), cadre=["parokhet"]),
    dict(id="vue_kiyor", cadre=["kiyor"], cap=135, sol=Z_AZ, recul_max=8.0),
    dict(id="vue_kodesh_hakodashim", cadre=["aron", "kaporet", "even_hashetiya"], cap=90, sol=Z_BAT,
         recul_max=9.0),
    dict(id="vue_mizbeach", cadre=["mizbeach", "kevesh"], cap=135, sol=Z_AZ, recul_max=60.0),
    dict(id="vue_oulam", position=(-10.0, 17.0, Z_AZ), cadre=["oulam"]),
    dict(id="vue_quinze_marches", cadre=["quinze_marches", "shaar_nikanor"], cap=180,
         sol=Z_EZN, recul_max=40.0),
    dict(id="vue_mesiba_bira", position=(-18.25, 70.0, -15.5), cap=270),
    dict(id="vue_beit_hatevila", position=(-162.0, 38.0, -12.0), cap=146),
    dict(id="vue_shit", position=(-48.0, -19.0, -9.0), cap=225, tangage=10),
]


def comprimer(glb):
    """Recompresse le .glb en place avec meshopt.

    C'est la seule optimisation qui compte sur un téléphone en 4G, et l'export glTF de
    Blender ne sait pas la faire. `-kn` garde les noms de nœuds, qui sont le lien
    géométrie ↔ encyclopédie ; la quantification est portée à 16 bits parce que le
    placage d'or ne se tient qu'à 4,8 cm de la pierre qu'il couvre.

    `-cc` plutôt que `-c` : l'hébergeur sert le .glb sans compression de transport —
    `curl -I https://davidbonan.io/visite/temple.glb` ne renvoie aucun `content-encoding`
    —, donc ce sont les octets du fichier qui voyagent, et un cinquième de moins vaut
    l'encodage plus lent. Le décodeur, lui, est le même.
    """
    sortie = glb.with_suffix(".pack.glb")
    commande = ["npx", "-y", "gltfpack", "-i", str(glb), "-o", str(sortie),
                "-cc", "-kn", "-km", "-ke", "-vp", "16", "-vn", "12"]
    try:
        subprocess.run(commande, check=True, capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as erreur:
        sortie.unlink(missing_ok=True)
        print(f"\n  gltfpack indisponible, .glb laissé non compressé : {erreur}")
        return
    sortie.replace(glb)


def chanfreiner(gardes):
    """Cuit les chanfreins de près, jette les autres. À faire AVANT la fusion.

    `object.join` ne garde que les modificateurs de l'objet actif : un chanfrein encore
    en attente au moment de la fusion est perdu sans bruit. Et l'export ne peut pas s'en
    charger non plus, puisqu'il vient après. Le maillage est donc remplacé ici par son
    évaluation — ce que fait `modifier_apply`, sans son contexte ni sa lenteur.

    Un seul segment : une pierre de taille a un ARÊTIER, pas un congé. Le blockout en
    pose deux pour les passes Normal de l'i2i, ce qui arrondit — et double la facture.
    """
    proches = {o for nom in CHANFREIN if (c := bpy.data.collections.get(nom))
               for o in c.objects if o in gardes}
    deps = bpy.context.evaluated_depsgraph_get()
    cuits = 0
    for objet in gardes:
        if not objet.modifiers:
            continue
        if objet not in proches:
            objet.modifiers.clear()
            continue
        for modificateur in objet.modifiers:
            if modificateur.type == "BEVEL":
                modificateur.segments = 1
        objet.data = bpy.data.meshes.new_from_object(objet.evaluated_get(deps))
        objet.modifiers.clear()
        cuits += 1
    print(f"  {cuits} volumes chanfreinés, {len(gardes) - cuits} laissés vifs")


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


def en_metres(vue, emprises):
    inconnus = [c for c in vue.get("cadre", []) if c not in emprises]
    if inconnus:
        raise ValueError(f"{vue['id']} : cadre sans géométrie {inconnus}")
    sortie = {clef: valeur for clef, valeur in vue.items()
              if clef in ("id", "nom", "cadre", "cap", "tangage", "vol")}
    if "position" in vue:
        x, y, z = vue["position"]
        sortie["position"] = [x * AMA, z * AMA, -y * AMA]
    if "sol" in vue:
        sortie["sol"] = vue["sol"] * AMA
    if "recul_max" in vue:
        sortie["recul_max"] = vue["recul_max"] * AMA
    return sortie


# À lire avant le tri des objets : ce sont des lampes, pas des maillages.
def flammes():
    return [[o.matrix_world.translation.x, o.matrix_world.translation.z, -o.matrix_world.translation.y]
            for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith("Menora_flamme")]


def main():
    DOSSIER.mkdir(exist_ok=True)
    regles = concepts()
    connus = {ident for _, ident in regles}
    lampes = flammes()

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

    chanfreiner(gardes)

    for mat in bpy.data.materials:
        aplatir(mat)

    emprises = {}
    for ident in sorted(groupes):
        objets = sorted(groupes[ident], key=lambda o: o.name)
        fusionne = fusionner(ident, objets)
        emprises[ident] = bornes(fusionne)
        print(f"  {ident:26s} {len(objets):5d} volumes")
    entrees = [en_metres(v, emprises) for v in REPERES]
    vues = [en_metres(v, emprises) for v in VUES]

    bpy.ops.export_scene.gltf(
        filepath=str(DOSSIER / "temple.glb"),
        export_format="GLB",
        export_extras=True,
        export_yup=True,
        # `chanfreiner` a déjà cuit ce qui devait l'être et jeté le reste : il ne
        # subsiste aucun modificateur à appliquer.
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

    comprimer(DOSSIER / "temple.glb")

    (DOSSIER / "reperes.json").write_text(json.dumps({
        "ama": AMA,
        "emprises": emprises,
        "entrees": entrees,
        "vues": vues,
        "flammes": lampes,
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
