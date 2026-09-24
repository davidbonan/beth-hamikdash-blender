#!/usr/bin/env python3
"""promenade.py <dossier> [--requete 'qualite=basse'] [--parcours tamid,yom_kippour] [--stations 99] [--port 8791]

Ce qu'un visiteur fait vraiment : ouvre la visite dans Safari du simulateur, suit chaque parcours guidé station
par station en marchant à l'allure réelle, et capture l'écran à chaque arrivée (<dossier>/<parcours>_<n>.jpg).
Le rythme, la mémoire GPU et l'exposition sont relevés toutes les deux secondes pendant la marche
(<dossier>/promenade.json) : c'est la mesure qui voit une perte de contexte, une fuite, une saccade.
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
arguments.add_argument("--parcours")
arguments.add_argument("--stations", type=int, default=99)
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


def capturer(nom):
    subprocess.run(["xcrun", "simctl", "io", "booted", "screenshot", "--type=jpeg", str(dossier / f"{nom}.jpg")],
                   check=True, capture_output=True)


avant = set(json.load(urllib.request.urlopen(f"{base}/__clients")))
url = f"http://localhost:{options.port}/visite/?{options.requete}&t={int(time.time())}"
subprocess.Popen(["xcrun", "simctl", "openurl", "booted", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(120):
    nouvelles = set(json.load(urllib.request.urlopen(f"{base}/__clients"))) - avant
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
  const cliquer = (motif) => { for (const b of document.querySelectorAll("button")) if (b.offsetParent && motif.test(b.textContent.trim())) b.click(); };
  cliquer(/^Entrer$/);
  await new Promise((r) => setTimeout(r, 1500));
  cliquer(/^Passer$/);
  window.__releve = [];
  setInterval(() => window.__releve.push({ ...__rythme.at(-1), ...__etat(), station: __parcours.ouvert() ? __parcours.station() : null }), 2000);
  return { pret_s: +(performance.now() / 1000).toFixed(1), parcours: __parcours.liste() };
""", delai=200)
print("prête en", debut["pret_s"], "s", flush=True)
capturer("depart")
choisis = options.parcours.split(",") if options.parcours else debut["parcours"]
arrivees = []
for id_ in choisis:
    nombre = ordonner(f"__parcours.ouvrir({json.dumps(id_)}); await new Promise((r) => setTimeout(r, 2500)); return __parcours.nombre();")
    capturer(f"{id_}_00")
    for n in range(1, min(nombre, options.stations + 1)):
        arrivee = ordonner("""
          document.querySelector("#parcours .suivant").click();
          const t0 = performance.now();
          await new Promise((r) => setTimeout(r, 300));
          while (__parcours.trajet() && performance.now() - t0 < 90000) await new Promise((r) => setTimeout(r, 200));
          await new Promise((r) => setTimeout(r, 1500));
          return { marche_s: +((performance.now() - t0) / 1000).toFixed(1), ...__rythme.at(-1), ...__etat() };
        """)
        capturer(f"{id_}_{n:02d}")
        arrivees.append({"parcours": id_, "station": n, **arrivee})
        print(id_, n, {k: arrivee.get(k) for k in ("marche_s", "ips", "p95", "max", "totalMo", "echelle", "exposition", "perdu")}, flush=True)
    ordonner("__parcours.fermer(); await new Promise((r) => setTimeout(r, 1000)); return 1")
releve = ordonner("return window.__releve")
(dossier / "promenade.json").write_text(json.dumps({"pret_s": debut["pret_s"], "arrivees": arrivees, "releve": releve},
                                                   ensure_ascii=False, indent=1))
