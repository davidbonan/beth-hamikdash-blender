#!/usr/bin/env python3
"""parcourir.py <dossier> [--requete 'qualite=basse'] [--vues a,b,c] [--attente 2.5] [--port 8791]

Ouvre la visite sondée dans Safari du simulateur démarré, attend qu'elle soit prête, puis pour chaque vue :
s'y rend, attend, capture l'écran du simulateur (<dossier>/<vue>.jpg) et relève le rythme et la mémoire
(<dossier>/mesures.json). Sans --vues : toutes les entrées et vues de reperes.json.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

arguments = argparse.ArgumentParser()
arguments.add_argument("dossier")
arguments.add_argument("--requete", default="")
arguments.add_argument("--vues")
arguments.add_argument("--attente", type=float, default=2.5)
arguments.add_argument("--port", type=int, default=8791)
options = arguments.parse_args()
dossier = Path(options.dossier)
dossier.mkdir(parents=True, exist_ok=True)
base = f"http://127.0.0.1:{options.port}"


page = None


def ordonner(code, delai=120):
    requete = urllib.request.Request(f"{base}/__ordonner", data=json.dumps({"code": code, "delai": delai, "client": page}).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        reponse = json.load(urllib.request.urlopen(requete, timeout=delai + 5))
    except urllib.error.HTTPError as e:
        reponse = json.load(e)
    if reponse.get("erreur"):
        raise RuntimeError(reponse["erreur"])
    return reponse.get("resultat")


def clients():
    return json.load(urllib.request.urlopen(f"{base}/__clients"))


def capturer(nom):
    subprocess.run(["xcrun", "simctl", "io", "booted", "screenshot", "--type=jpeg", str(dossier / f"{nom}.jpg")],
                   check=True, capture_output=True)


avant = set(clients())
url = f"http://localhost:{options.port}/visite/?{options.requete}&t={int(time.time())}"
subprocess.Popen(["xcrun", "simctl", "openurl", "booted", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(120):
    nouvelles = set(clients()) - avant
    if nouvelles:
        page = nouvelles.pop()
        break
    time.sleep(0.5)
else:
    sys.exit("la page ne s'est pas annoncée")
debut = ordonner("""
  const t0 = performance.now();
  while (!window.__pret) {
    if (performance.now() - t0 > 180000) throw new Error("jamais prête");
    await new Promise((r) => setTimeout(r, 250));
  }
  for (const b of document.querySelectorAll("button"))
    if (b.offsetParent && /^(Entrer|Passer)$/.test(b.textContent.trim())) b.click();
  await new Promise((r) => setTimeout(r, 1500));
  for (const b of document.querySelectorAll("button"))
    if (b.offsetParent && /^Passer$/.test(b.textContent.trim())) b.click();
  return { pret_s: +(performance.now() / 1000).toFixed(1), vues: __vues() };
""", delai=200)
vues = options.vues.split(",") if options.vues else debut["vues"]
mesures = {"pret_s": debut["pret_s"], "requete": options.requete, "vues": {}}
for vue in vues:
    mesure = ordonner(f"""
      __vue({json.dumps(vue)});
      await new Promise((r) => setTimeout(r, {options.attente * 1000}));
      return {{ ...__rythme.at(-1), ...__etat() }};
    """)
    capturer(vue)
    mesures["vues"][vue] = mesure
    print(vue, {k: mesure.get(k) for k in ("ips", "p95", "appels", "triangles", "totalMo", "echelle", "perdu")}, flush=True)
(dossier / "mesures.json").write_text(json.dumps(mesures, ensure_ascii=False, indent=1))
