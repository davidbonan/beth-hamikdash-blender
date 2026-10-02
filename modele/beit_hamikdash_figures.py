"""Blender -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_figures.py [-- [--troupe figures_shoeva] rôle …] — écrit visite/<troupe>.glb et .json."""
import json
import pathlib
import sys
from typing import NamedTuple

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
# Blender garde les modules importés d'une exécution à l'autre : sans cette purge, un second Run Script garderait l'ancien code.
for _module in [nom for nom in sys.modules if nom.split(".")[0] == "figurants"]:
    del sys.modules[_module]

from beit_hamikdash_visite import AMA, DOSSIER, comprimer, en_metres  # noqa: E402
from figurants.animation import animer_en_danse, animer_en_marche, animer_sur_place, emprise, unir  # noqa: E402
from figurants.danse import Hora  # noqa: E402
from figurants.mise_en_scene import IMAGES, Terrain, _rayon_sol  # noqa: E402
from figurants.troupes.figures import roles_de_la_visite  # noqa: E402
from figurants.troupes.figures_bikkourim import roles_bikkourim  # noqa: E402
from figurants.troupes.figures_hakhel import roles_hakhel  # noqa: E402
from figurants.troupes.figures_kippour import roles_kippour  # noqa: E402
from figurants.troupes.figures_nazir import roles_nazir  # noqa: E402
from figurants.troupes.figures_pessah import roles_pessah  # noqa: E402
from figurants.troupes.figures_shoeva import roles_shoeva  # noqa: E402
from figurants.troupes.figures_souccot import roles_souccot  # noqa: E402
from figurants.troupes.figures_tamid import VUES, roles_du_tamid  # noqa: E402


class Troupe(NamedTuple):
    roles: object
    vues: list


TROUPES = {"figures": Troupe(roles_de_la_visite, VUES), "figures_tamid": Troupe(roles_du_tamid, VUES),
           "figures_kippour": Troupe(roles_kippour, []), "figures_shoeva": Troupe(roles_shoeva, []),
           "figures_pessah": Troupe(roles_pessah, []),
           "figures_bikkourim": Troupe(roles_bikkourim, []), "figures_souccot": Troupe(roles_souccot, []),
           "figures_hakhel": Troupe(roles_hakhel, []),
           "figures_nazir": Troupe(roles_nazir, [])}


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    nom_troupe = "figures"
    if "--troupe" in arguments:
        k = arguments.index("--troupe")
        nom_troupe = arguments[k + 1]
        del arguments[k:k + 2]
    troupe = TROUPES[nom_troupe]
    bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = IMAGES, 1.0
    lot = [r for r in troupe.roles() if not arguments or r.nom in arguments]
    terrains, sols, releves = {}, {}, {}
    for role in lot:
        if role.trajet:
            # Les danseurs d'une même ronde foulent le même sol : un relevé pour tous.
            cle = (*role.trajet.bornes(0.8), role.sol_haut * AMA)
            releves[cle] = releves.get(cle) or Terrain(*cle)
            terrains[role.nom] = releves[cle]
        else:
            sols[role.nom] = role.ou[2] * AMA if role.sol_porte else _rayon_sol(role.ou[0] * AMA, role.ou[1] * AMA, role.ou[2] * AMA)

    boites, figures = {}, []
    for role in lot:
        h = role.batir()
        if isinstance(role.trajet, Hora):
            places = animer_en_danse(h, role, terrains[role.nom])
        elif role.trajet:
            places = animer_en_marche(h, role, terrains[role.nom])
        else:
            places = animer_sur_place(h, role, sols[role.nom])
        # Les cohanim ont aussi leur emprise commune : « Un élément… » y mène. Les Léviim sont déjà un concept.
        for concept in {role.concept, role.famille} - {None}:
            boites.setdefault(concept, []).append(emprise(h, places))
        figures.append(h)
        print(f"  {role.nom:12s} {len(places):4d} places")

    bpy.ops.object.select_all(action="DESELECT")
    for h in figures:
        h.rig.select_set(True)
        for enfant in h.rig.children:
            enfant.select_set(True)
    glb = DOSSIER / f"{nom_troupe}.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb), export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
        export_cameras=False, export_lights=False, export_extras=False, export_materials="EXPORT",
        export_normals=True, export_texcoords=True, export_vertex_color="MATERIAL", export_image_format="WEBP",
        export_image_quality=82, export_skins=True, export_influence_nb=4, export_animations=True,
        export_animation_mode="ACTIONS", export_force_sampling=True, export_optimize_animation_size=True,
        export_def_bones=False)
    comprimer(glb, ("-af", str(IMAGES), "-si", "0.5"))

    emprises = {concept: unir(liste) for concept, liste in boites.items()}
    (DOSSIER / f"{nom_troupe}.json").write_text(json.dumps({
        "emprises": emprises,
        "vues": [en_metres(v, emprises) for v in troupe.vues if v["id"].removeprefix("vue_") in emprises],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(figures)} figures · {glb.name} {glb.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
