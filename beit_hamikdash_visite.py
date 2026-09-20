"""Exporte la scène sauvegardée vers la visite interactive du dossier `visite/`.

    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
        -P beit_hamikdash_visite.py

Comme `beit_hamikdash_inspect.py`, ce script **lit** le .blend et ne le réécrit
jamais : il détruit sa copie en mémoire (fusion des volumes, aplatissement des
matières) puis quitte. Ne jamais y appeler `wm.save_mainfile`.

Il produit deux fichiers :
    visite/temple.glb    la géométrie, un maillage par concept
    visite/reperes.json  l'emprise de chaque concept, les points d'entrée et les cartes d'occlusion
    visite/occlusion/    l'occlusion du ciel cuite par Cycles (`beit_hamikdash_occlusion.py`)
    visite/lumiere/      la lumière indirecte cuite par Cycles, pour les concepts de `--lumiere`

`-- --sans-occlusion` saute la cuisson (quelques minutes) : le .glb sort alors sans couche
d'occlusion, et reperes.json sans cartes, ce qui reste cohérent.
`-- --lumiere azara,oulam` cuit ces concepts en lumière indirecte plutôt qu'en occlusion, `-- --lumiere tout` tous.
`-- --pays` n'exporte que `visite/pays.glb` : la ville et le relief de `01_Pays`, que la visite charge après le Temple.
`-- --recuire [azara,oulam]` ne recuit en lumière que ces concepts, ceux dont la carte ne correspond
plus à la scène, et leurs voisins (`beit_hamikdash_recuisson.py`) ; les autres cartes restent.
`-- --simuler`, avec `--recuire`, dit ce qui serait recuit et combien de temps, sans rien cuire.
Une seule cuisson à la fois sur la machine, worktrees compris.

Le lien géométrie ↔ encyclopédie passe par `visite/concepts.json` : chaque concept y
déclare les préfixes de noms d'objets qui lui appartiennent, le préfixe le plus long
gagnant. Les volumes d'un même concept sont fusionnés en un seul maillage — 7 000
objets deviennent une soixantaine —, ce qui donne au navigateur autant de dessins
qu'il y a de choses à nommer, et fait du clic un concept plutôt qu'une des cinq
boîtes d'un mur percé.
"""
import contextlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import bpy

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
from beit_hamikdash_occlusion import cuire_occlusion, reglages_de_la_lumiere, retenus, separer_collees  # noqa: E402
from beit_hamikdash_recuisson import Recuisson, empreinte, verrou  # noqa: E402

DOSSIER = RACINE / "visite"
AMA = 0.48

# Le peuple, la fumée et les accessoires de plan sont une mise en scène, pas le
# bâtiment ; le pays et les caméras ne se visitent pas.
COLLECTIONS = ("00_HarHabayit", "10_EzratNashim", "20_Azara", "30_Mizbeach", "40_Ulam",
               "50_Heikhal", "60_KodeshHakodashim", "65_Aron", "70_Kelim", "80_Lishkot")

# En mètres. Le blockout chanfreine à 0.06 ama pour le film ; à hauteur d'homme, ce liseré-là se lit en congé.
LARGEUR_CHANFREIN = 0.03 * AMA

# En amot. `cadre` : concepts à montrer entiers ; sans `position`, le navigateur recule le long du `cap` (0 = est, 90 = nord).
Z_HAR, Z_EZN, Z_AZ, Z_BAT = -16.0, -10.0, 0.0, 6.0
Z_PLACE_KOTEL = -51.58

REPERES = [
    dict(id="har_habayit", nom="Har HaBayit, sur l'axe est",
         position=(185.0, 0.0, Z_HAR), cadre=["oulam"]),
    dict(id="face_porte_est", nom="Face à la porte orientale",
         position=(176.0, 0.0, Z_HAR), cap=180, tangage=16),
    dict(id="ezrat_nashim", nom="Ezrat Nashim",
         position=(137.0, 0.0, Z_EZN), cadre=["oulam"]),
    dict(id="quinze_marches", nom="Pied des quinze marches",
         cadre=["quinze_marches", "shaar_nikanor"], cap=180, sol=Z_EZN, recul_max=40.0),
    # Sur l'axe, le Mizbea'h cache l'Oulam : un pas au nord de Nikanor, le long des Léviim.
    dict(id="azara", nom="Ezrat Israël",
         position=(-11.5, 31.25, Z_AZ), cap=190, tangage=12),
    # Seul, l'autel se lit comme un mur : avec son kevesh, depuis le sud-est, sans reculer jusqu'aux marches de l'Ezrat Israël.
    dict(id="mizbeach", nom="Devant le Mizbea'h",
         position=(-16.0, -35.4, Z_AZ), cap=130, tangage=3),
    dict(id="kiyor", nom="Au Kiyor",
         cadre=["kiyor"], cap=135, sol=Z_AZ, recul_max=8.0),
    dict(id="oulam", nom="Sous l'Oulam",
         cadre=["portes_heikhal"], cap=180, sol=Z_BAT, recul_max=17.0),
    dict(id="heikhal", nom="Dans le Heikhal",
         cadre=["menora", "shulchan", "mizbeach_hazahav"], cap=180, sol=Z_BAT, recul_max=24.0),
    # Les badim touchent la parokhet (Yoma 54a) : l'Aron ne se voit entier que de flanc, depuis le mur sud.
    dict(id="kodesh_hakodashim", nom="Kodesh HaKodashim",
         cadre=["aron", "kaporet", "even_hashetiya"], cap=90, sol=Z_BAT, recul_max=9.0),
    # Au sud-ouest de la place : ailleurs, le Kotel et le nord cachent le Heikhal. La place est à
    # Z_PLACE_KOTEL du blockout : le dallage d'Hérode moins les dix-neuf mètres du mur.
    dict(id="place_kotel", nom="Place du Kotel",
         position=(-482.1, -399.9, Z_PLACE_KOTEL), cap=47, tangage=10),
]

# Ce que « Un élément… » et le plan montrent de `<id>` quand le recul automatique n'y suffit pas ; une cour ne tient entière qu'en vol.
# Tout lieu du plan en a une : reculé depuis l'est, l'œil finissait dans un mur ou devant une façade aveugle.
VUES = [
    dict(id="vue_azara", cadre=["azara"], cap=180, sol=90.0, recul_max=300.0, vol=True),
    dict(id="vue_ezrat_nashim",
         cadre=["porte_est_ezrat_nashim", "lishkat_haetzim", "lishkat_hanezirim",
                "lishkat_hametzoraim", "lishkat_beit_shemanya", "quinze_marches"],
         cap=180, sol=60.0, recul_max=300.0, vol=True),
    dict(id="vue_sol_har_habayit", position=(187.5, -291.7, 163.4), cap=131, tangage=-23.5, vol=True),
    dict(id="vue_place_kotel", position=(-482.1, -399.9, Z_PLACE_KOTEL), cap=47, tangage=10),
    dict(id="vue_arche_wilson", position=(-382.1, -281.2, Z_PLACE_KOTEL), cap=83, tangage=8),
    dict(id="vue_heikhal", cadre=["menora", "shulchan", "mizbeach_hazahav"], cap=180, sol=Z_BAT,
         recul_max=24.0),
    dict(id="vue_kiyor", cadre=["kiyor"], cap=135, sol=Z_AZ, recul_max=8.0),
    dict(id="vue_kodesh_hakodashim", cadre=["aron", "kaporet", "even_hashetiya"], cap=90, sol=Z_BAT,
         recul_max=9.0),
    dict(id="vue_mizbeach", position=(-16.0, -35.4, Z_AZ), cap=130, tangage=3),
    dict(id="vue_oulam", position=(-45.8, 25.0, Z_AZ), cap=205, tangage=20),
    dict(id="vue_douze_marches_oulam", position=(-45.8, 18.75, Z_AZ), cap=219, tangage=2),
    dict(id="vue_quinze_marches", cadre=["quinze_marches", "shaar_nikanor"], cap=180,
         sol=Z_EZN, recul_max=40.0),
    # Les lishkot de l'Ezrat Nashim sont à ciel ouvert : depuis leur seuil, on voit ce qu'elles gardent.
    dict(id="vue_lishkat_haetzim", position=(120.0, 30.8, Z_EZN), cap=90, tangage=-6),
    dict(id="vue_lishkat_hanezirim", position=(120.0, -30.8, Z_EZN), cap=270, tangage=-6),
    dict(id="vue_lishkat_hametzoraim", position=(25.0, 30.8, Z_EZN), cap=90, tangage=-6),
    dict(id="vue_lishkat_beit_shemanya", position=(25.0, -30.8, Z_EZN), cap=270, tangage=-6),
    dict(id="vue_taim", position=(-116.0, 19.0, Z_BAT), cap=180),
    dict(id="vue_mesiba", position=(-101.0, 28.5, Z_BAT), cap=180, tangage=5),
    dict(id="vue_aliyah", position=(-162.5, 0.0, 46.0), cap=0),
    dict(id="vue_lishkat_hagazit", position=(-147.9, 59.0, Z_AZ), cap=90),
    dict(id="vue_lishkat_hagola", position=(-179.2, 77.5, Z_AZ), cap=0, tangage=-5),
    dict(id="vue_lishkat_haetz", position=(-178.3, 94.6, Z_EZN), cap=0, tangage=3),
    dict(id="vue_lishkat_hamelach", position=(-42.7, -63.3, Z_AZ), cap=0),
    dict(id="vue_lishkat_haparva", position=(-83.1, -57.5, Z_AZ), cap=270, tangage=-10),
    dict(id="vue_lishkat_hamedichin", position=(-104.4, -57.5, Z_AZ), cap=270, tangage=-10),
    dict(id="vue_lishkat_parhedrin", position=(-33.5, -75.0, Z_EZN), cap=270),
    dict(id="vue_lishkat_osei_chavitin", position=(-20.8, -12.5, Z_AZ), cap=0, tangage=12),
    dict(id="vue_beit_hamoked", position=(-12.1, 58.75, Z_AZ), cap=90),
    dict(id="vue_shaar_hamayim", position=(-12.1, -61.5, Z_AZ), cap=270, tangage=-8),
    dict(id="vue_shaar_hanitzotz", position=(-121.5, 65.6, Z_AZ), cap=90, tangage=-8),
    # Le Beit Avtinas et le Beit HaNitzotz sont à l'étage de leur porte : ils se montrent depuis la cour.
    dict(id="vue_beit_avtinas", position=(-12.1, -33.3, Z_AZ), cap=270, tangage=20),
    dict(id="vue_beit_hanitzotz", position=(-114.6, 41.7, Z_AZ), cap=97, tangage=20),
    dict(id="vue_shaar_tadi", position=(-100.0, 158.3, Z_HAR), cap=90, tangage=8),
    dict(id="vue_mesiba_bira", position=(-18.25, 70.0, -15.5), cap=270),
    dict(id="vue_beit_hatevila", position=(-162.0, 38.0, -12.0), cap=146),
    dict(id="vue_shit", position=(-48.0, -19.0, -9.0), cap=225, tangage=10),
]


def comprimer(glb, options=()):
    """Recompresse le .glb en place avec meshopt.

    C'est la seule optimisation qui compte sur un téléphone en 4G, et l'export glTF de
    Blender ne sait pas la faire. `-kn` garde les noms de nœuds, qui sont le lien
    géométrie ↔ encyclopédie ; la quantification est portée à 16 bits parce que le
    placage d'or ne se tient qu'à 4,8 cm de la pierre qu'il couvre.

    `-cc` plutôt que `-c` : l'hébergeur sert le .glb sans compression de transport —
    `curl -I https://bethhamikdach.com/visite/temple.glb` ne renvoie aucun `content-encoding`
    —, donc ce sont les octets du fichier qui voyagent, et un cinquième de moins vaut
    l'encodage plus lent. Le décodeur, lui, est le même.
    """
    sortie = glb.with_suffix(".pack.glb")
    # `-kv` : les UV des plaques gravées ne servent à aucune texture glTF — c'est
    # matieres.js qui les lit — et gltfpack les jetait comme inutilisées. `-vtf` : quantifiées,
    # il les recadre sur leur boîte englobante et compense par une KHR_texture_transform
    # sur la texture de la matière, qu'aucune matière n'a ici — à 16 bits l'écart
    # restait, un dixième de figure en haut de l'atlas, et le modelé glissait sous sa
    # plaque. En flottants, il les laisse telles quelles.
    commande = ["npx", "-y", "gltfpack", "-i", str(glb), "-o", str(sortie),
                "-cc", "-kn", "-km", "-ke", "-kv", "-vp", "16", "-vn", "12", "-vtf", *options]
    try:
        subprocess.run(commande, check=True, capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as erreur:
        sortie.unlink(missing_ok=True)
        print(f"\n  gltfpack indisponible, .glb laissé non compressé : {erreur}")
        return
    sortie.replace(glb)


def chanfreiner(gardes):
    """Cuit les chanfreins. À faire AVANT la fusion.

    Une arête vive n'accroche aucune lumière, et c'est ce qui trahit le plus sûrement une
    maquette : à hauteur d'homme, le long des murs des cours comme au pied du Mizbea'h.

    `object.join` ne garde que les modificateurs de l'objet actif : un chanfrein encore
    en attente au moment de la fusion est perdu sans bruit. Et l'export ne peut pas s'en
    charger non plus, puisqu'il vient après. Le maillage est donc remplacé ici par son
    évaluation — ce que fait `modifier_apply`, sans son contexte ni sa lenteur.

    Un seul segment : une pierre de taille a un ARÊTIER, pas un congé. Le blockout en
    pose deux pour les passes Normal de l'i2i, ce qui arrondit — et double la facture.
    """
    for objet in gardes:
        objet["faces_sans_chanfrein"] = len(objet.data.polygons)
    biseautes = [o for o in gardes if o.modifiers]
    for objet in biseautes:
        for modificateur in objet.modifiers:
            if modificateur.type == "BEVEL":
                modificateur.segments = 1
                modificateur.width = min(modificateur.width, LARGEUR_CHANFREIN)
    # Lu après le passage à un segment : pris avant, il rendait encore les deux du blockout.
    deps = bpy.context.evaluated_depsgraph_get()
    for objet in biseautes:
        objet.data = bpy.data.meshes.new_from_object(objet.evaluated_get(deps))
        objet.modifiers.clear()
    print(f"  {len(biseautes)} volumes chanfreinés, {len(gardes) - len(biseautes)} sans chanfrein")


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
    # `object.join` ne garde que les propriétés de l'objet actif.
    faces_sans_chanfrein = sum(o["faces_sans_chanfrein"] for o in objets)
    if len(objets) > 1:
        with bpy.context.temp_override(active_object=tete, selected_editable_objects=objets):
            bpy.ops.object.join()
    tete.name = nom
    tete.data.name = nom
    tete["concept"] = nom
    tete["faces_sans_chanfrein"] = faces_sans_chanfrein
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
def lampes(prefixe):
    return [[o.matrix_world.translation.x, o.matrix_world.translation.z, -o.matrix_world.translation.y]
            for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith(prefixe)]


def livrer(chantier):
    """Remplace l'export servi par celui du chantier, cartes d'abord, reperes.json en dernier : la visite reste servie pendant la cuisson."""
    reperes = json.loads((chantier / "reperes.json").read_text(encoding="utf-8"))
    cartes = {c["carte"] for nature in ("occlusion", "lumiere") for c in reperes[nature].values()}
    for carte in chantier.glob("*/*.webp"):
        destination = DOSSIER / carte.relative_to(chantier)
        destination.parent.mkdir(exist_ok=True)
        shutil.move(carte, destination)
    shutil.move(chantier / "temple.glb", DOSSIER / "temple.glb")
    shutil.move(chantier / "reperes.json", DOSSIER / "reperes.json")
    # Une nature que la cuisson n'a pas ouverte n'a rien recuit — `--sans-occlusion` garde donc ses cartes.
    for nature in ("occlusion", "lumiere"):
        if not (chantier / nature).is_dir():
            continue
        for ancienne in (DOSSIER / nature).glob("*.webp"):
            if f"{nature}/{ancienne.name}" not in cartes:
                ancienne.unlink()


def option(nom):
    return sys.argv[sys.argv.index(nom) + 1] if nom in sys.argv else None


def recuisson_demandee():
    """None sans `--recuire`, sinon les concepts nommés après lui, peut-être aucun."""
    if "--recuire" not in sys.argv:
        return None
    suite = sys.argv[sys.argv.index("--recuire") + 1:]
    return frozenset(suite[0].split(",")) if suite and not suite[0].startswith("--") else frozenset()


def cuire(fusionnes, chantier, lampes):
    """(occlusion, lumière, empreintes) pour reperes.json ; None quand `--simuler` s'arrête au plan de recuisson."""
    choisis = list(retenus(fusionnes))
    eclaires = frozenset(filter(None, (option("--lumiere") or "").split(",")))
    demandes, recuisson, gardees = recuisson_demandee(), None, None
    if demandes is not None:
        if eclaires:
            raise ValueError("--recuire choisit lui-même ce qui cuit en lumière : ne pas y joindre --lumiere")
        precedent = json.loads((DOSSIER / "reperes.json").read_text(encoding="utf-8"))
        recuisson = Recuisson(precedent, demandes, {ident for ident, _, _ in choisis})
    separer_collees([obj for _, obj, _ in choisis])
    reglages = reglages_de_la_lumiere(lampes)
    tailles = {ident: taille for ident, _, taille in choisis}
    empreintes = {ident: empreinte(obj, tailles.get(ident, 0), reglages) for ident, obj in fusionnes.items()}
    if recuisson is not None:
        eclaires = recuisson.cibles(fusionnes, empreintes)
        if "--simuler" in sys.argv:
            return None
        gardees = recuisson.gardees(eclaires)
    return (*cuire_occlusion(choisis, chantier, eclaires, lampes, gardees), empreintes)


def exporter(chantier):
    regles = concepts()
    connus = {ident for _, ident in regles}
    flammes, arche, braises = lampes("Menora_flamme"), lampes("Aron_lumiere"), lampes("Machta_braise")

    gardes = {o for nom in COLLECTIONS if (c := bpy.data.collections.get(nom))
              for o in c.objects if o.type == "MESH"}
    # Avant le tri : les outils des tailles (99_Outils) ne sont pas gardés, et leurs booléens les lisent.
    chanfreiner(gardes)
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

    emprises, fusionnes = {}, {}
    for ident in sorted(groupes):
        objets = sorted(groupes[ident], key=lambda o: o.name)
        fusionnes[ident] = fusionner(ident, objets)
        emprises[ident] = bornes(fusionnes[ident])
        print(f"  {ident:26s} {len(objets):5d} volumes")

    # Avant l'aplatissement : la cuisson voit encore les matières du blockout.
    cartes = ({}, {}, {}) if "--sans-occlusion" in sys.argv else cuire(
        fusionnes, chantier, {"flammes": flammes, "arche": arche, "braises": braises})
    if cartes is None:
        return False
    occlusion, lumiere, empreintes = cartes

    for mat in bpy.data.materials:
        aplatir(mat)
    entrees = [en_metres(v, emprises) for v in REPERES]
    vues = [en_metres(v, emprises) for v in VUES]

    bpy.ops.export_scene.gltf(
        filepath=str(chantier / "temple.glb"),
        export_format="GLB",
        export_extras=True,
        export_yup=True,
        # `chanfreiner` a déjà cuit les chanfreins : il ne subsiste aucun modificateur à appliquer.
        export_apply=False,
        export_cameras=False,
        export_lights=False,
        export_materials="EXPORT",
        # Les normales pèsent, mais `shadow.normalBias` n'a rien pour décaler sans
        # elles : la carte d'ombre se mord alors elle-même, et l'intérieur du Heikhal
        # se couvre d'un damier clair/sombre à l'échelle du texel.
        export_normals=True,
        # Seules les plaques gravées portent des UV — celles de `beit_hamikdash_gravures.py`,
        # que le blockout écrit lui-même : aucun dépliage à la main, rien à repeindre.
        # Un maillage sans couche UV ne sort aucune coordonnée ; les concepts qui
        # mêlent plaques et volumes nus en portent pour tous, à zéro sur les nus.
        export_texcoords=True,
        export_skins=False,
        export_animations=False,
    )

    comprimer(chantier / "temple.glb")

    (chantier / "reperes.json").write_text(json.dumps({
        "ama": AMA,
        "emprises": emprises,
        "entrees": entrees,
        "vues": vues,
        "flammes": flammes,
        "arche": arche,
        "braises": braises,
        "occlusion": occlusion,
        "lumiere": lumiere,
        "empreintes": empreintes,
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
    taille = (chantier / "temple.glb").stat().st_size / 1e6
    print(f"\n{len(groupes)} maillages · temple.glb {taille:.1f} Mo")
    return True


PAYS = "01_Pays"


def exporter_pays():
    """`visite/pays.glb` : Jérusalem autour du Temple, chargée après lui. Pas de concept,
    pas de chanfrein, pas de cuisson : c'est un décor, qu'on voit de loin. Les oliviers,
    deux objets chacun, sont fondus en un seul maillage."""
    gardes = [o for o in bpy.data.collections[PAYS].objects if o.type == "MESH"]
    for o in list(bpy.data.objects):
        if o not in gardes:
            bpy.data.objects.remove(o, do_unlink=True)
    oliviers = [o for o in gardes if o.name.startswith("Olivier_")]
    if oliviers:
        with bpy.context.temp_override(active_object=oliviers[0], selected_editable_objects=oliviers):
            bpy.ops.object.join()
        oliviers[0].name = "Oliviers"
    for mat in bpy.data.materials:
        aplatir(mat)
    glb = DOSSIER / "pays.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_yup=True,
                              export_apply=False, export_cameras=False, export_lights=False,
                              export_materials="EXPORT", export_normals=True,
                              export_texcoords=False, export_skins=False, export_animations=False)
    comprimer(glb)
    print(f"\n{len(bpy.data.objects)} maillages · pays.glb {glb.stat().st_size / 1e6:.1f} Mo")


def main():
    DOSSIER.mkdir(exist_ok=True)
    if "--pays" in sys.argv:
        return exporter_pays()
    sans_cuisson = "--sans-occlusion" in sys.argv or "--simuler" in sys.argv
    with contextlib.nullcontext() if sans_cuisson else verrou(), \
            tempfile.TemporaryDirectory(prefix="visite_") as chantier:
        if exporter(pathlib.Path(chantier)):
            livrer(pathlib.Path(chantier))


if __name__ == "__main__":
    main()
