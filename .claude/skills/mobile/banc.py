#!/usr/bin/env python3
"""banc.py [--port 8791] — recapture visite/banc.json, le programme que `qualite.js` lie au premier passage pour jauger la machine.

Ouvre la visite sondée au profil léger dans Safari du simulateur, attend qu'elle soit prête, et écrit les sources
sommet + fragment du programme de `Pierre_claire` telles que three les a compilées. À refaire quand `matieres.js`
ou three changent ce nuanceur : le banc doit lier ce que la visite liera.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

arguments = argparse.ArgumentParser()
arguments.add_argument("--port", type=int, default=8791)
options = arguments.parse_args()
base = f"http://127.0.0.1:{options.port}"
cible = Path(__file__).resolve().parents[3] / "visite" / "banc.json"


def clients():
    return json.load(urllib.request.urlopen(f"{base}/__clients"))


def ordonner(page, code, delai=240):
    requete = urllib.request.Request(f"{base}/__ordonner", data=json.dumps({"code": code, "delai": delai, "client": page}).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        reponse = json.load(urllib.request.urlopen(requete, timeout=delai + 5))
    except urllib.error.HTTPError as e:
        reponse = json.load(e)
    if reponse.get("erreur"):
        raise RuntimeError(reponse["erreur"])
    return reponse.get("resultat")


avant = set(clients())
url = f"http://localhost:{options.port}/visite/?qualite=basse&autopsie&t={int(time.time())}"
subprocess.Popen(["xcrun", "simctl", "openurl", "booted", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(120):
    nouvelles = set(clients()) - avant
    if nouvelles:
        page = nouvelles.pop()
        break
    time.sleep(0.5)
else:
    sys.exit("la page ne s'est pas annoncée")
programme = ordonner(page, """
  const t0 = performance.now();
  while (!window.__pret) {
    if (performance.now() - t0 > 200000) throw new Error("jamais prête");
    await new Promise((r) => setTimeout(r, 250));
  }
  return __programmes.find((p) => p.fragment.includes("SHADER_NAME Pierre_claire"));
""")
if not programme:
    sys.exit("Pierre_claire n'a pas été liée")
cible.write_text(json.dumps({"sommet": programme["sommet"], "fragment": programme["fragment"]}, ensure_ascii=False, separators=(",", ":")))
print(f"{cible} : sommet {len(programme['sommet'])} o, fragment {len(programme['fragment'])} o")
