"""
BEIT HAMIKDASH — BLOCKOUT GÉNÉRATIF (Second Temple, selon Mishna Middot)
=========================================================================
Usage : en headless, chaîné avec les scripts qui l'exploitent (voir README) ; dans
l'onglet Scripting, ouvrir ce fichier depuis le disque — le paquet `blockout/` est
à côté de lui — puis Run Script (Alt+P).

Le script crée une scène complète en volumes gris, à l'échelle : le bâtiment, ses
ustensiles, le pays autour et la foule du jour. Il ne pose aucune caméra — elles
sont déclarées dans cameras.json et bâties par beit_hamikdash_cameras.py.

Chaque section de `SECTIONS` est un module de `blockout/` qui bâtit sa zone à
l'import, dans l'ordre où elles sont listées ; `blockout/primitives/` porte ce
qu'elles ont en commun — paramètres, matières, volumes, gravures, ouvrages.

Conventions
- 1 ama = AMA mètres (0.48 par défaut, Rav 'Haïm Naeh). Changer la constante suffit.
- +X = EST, -X = OUEST, +Y = NORD, -Y = SUD, +Z = haut.
- Origine : angle du mur EST de l'Azara (x=0) sur l'axe central du Heikhal (y=0),
  au niveau du sol de l'Azara (z=0). Le bâtiment est à l'ouest (x négatif).
- Toutes les cotes ci-dessous sont en amot ; la conversion se fait dans les helpers.

Sources : Middot 1–5, Yoma 3–5, Rambam Hilkhot Beit HaBe'hira 1–4.
Les choix entre avis divergents sont signalés par "# CHOIX".
"""

import importlib
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
# Blender garde les modules importés d'une exécution à l'autre : sans cette purge, un second Run Script ne bâtirait rien.
for _module in [nom for nom in sys.modules if nom.split(".")[0] == "blockout"]:
    del sys.modules[_module]

SECTIONS = (
    "nettoyage",
    "har_habayit",
    "ezrat_nashim",
    "azara",
    "lishkot",
    "heil",
    "modenature_azara",
    "mizbeach",
    "sous_l_azara",
    "bayit.oulam",
    "bayit.heikhal",
    "bayit.kelim",
    "bayit.parokhot",
    "bayit.parois_d_or",
    "bayit.kodesh_hakodashim",
    "pays.jerusalem",
    "foule",
    "finitions",
    "eclairage",
)

for section in SECTIONS:
    importlib.import_module(f"blockout.{section}")

print(f"Blockout terminé : {len(bpy.data.objects)} objets, "
      f"{len(bpy.data.collections)} collections.")
print("Aucune caméra : elles se posent avec beit_hamikdash_cameras.py, depuis cameras.json.")
