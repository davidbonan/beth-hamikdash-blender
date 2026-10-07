#!/usr/bin/env python3
"""comparer.py [--profils basse,minimale] [--echelles 0.75,0.55] [--vues a,b] [--tours 3] [--images 60] [--port 8791]

Ce que coûte une image d'un profil à l'autre : chaque tour recharge la visite sous chaque profil, en alternance,
et relève à chaque vue, définition épinglée (`__echelle`), le temps par image GPU compris (`__chrono`), les appels
et les triangles. Imprime la médiane des tours ; les triangles et les appels, eux, sont exacts.
"""
import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request

arguments = argparse.ArgumentParser()
arguments.add_argument("--profils", default="basse,minimale")
arguments.add_argument("--echelles", default="0.75,0.55")
arguments.add_argument("--vues", default="face_porte_est,azara,heikhal,kodesh_hakodashim")
arguments.add_argument("--tours", type=int, default=3)
arguments.add_argument("--images", type=int, default=60)
arguments.add_argument("--port", type=int, default=8791)
options = arguments.parse_args()
base = f"http://127.0.0.1:{options.port}"
profils, vues = options.profils.split(","), options.vues.split(",")
echelles = [float(e) for e in options.echelles.split(",")]


def ordonner(code, page, delai=200):
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


def ouvrir(profil):
    avant = set(clients())
    url = f"http://localhost:{options.port}/visite/?qualite={profil}&t={int(time.time())}"
    subprocess.Popen(["xcrun", "simctl", "openurl", "booted", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        nouvelles = set(clients()) - avant
        if nouvelles:
            return nouvelles.pop()
        time.sleep(0.5)
    sys.exit("la page ne s'est pas annoncée")


def mesurer(profil):
    page = ouvrir(profil)
    return ordonner(f"""
      const t0 = performance.now();
      while (!window.__pret) {{
        if (performance.now() - t0 > 180000) throw new Error("jamais prête");
        await new Promise((r) => setTimeout(r, 250));
      }}
      // Les niveaux de détail arrivent après l'ouverture : on attend que le compte de triangles ne bouge plus.
      for (let avant = -1, stable = 0; stable < 3;) {{
        await new Promise((r) => setTimeout(r, 2000));
        const {{ triangles }} = __compter(__rendre);
        stable = triangles === avant ? stable + 1 : 0;
        avant = triangles;
      }}
      const mesures = {{}};
      for (const vue of {json.dumps(vues)}) {{
        __vue(vue);
        await new Promise((r) => setTimeout(r, 2500));
        for (const echelle of {json.dumps(echelles)}) {{
          __echelle(echelle);
          mesures[vue + " @" + echelle] = {{ ms: __chrono({options.images}), ...__compter(__rendre) }};
        }}
      }}
      return mesures;
    """, page)


tours = {profil: [] for profil in profils}
for tour in range(options.tours):
    for profil in profils:
        tours[profil].append(mesurer(profil))
        print(f"tour {tour + 1} {profil}", file=sys.stderr, flush=True)

print(f"{'vue @échelle':34}" + "".join(f"{p + ' ms':>14}{'triangles':>11}{'appels':>8}" for p in profils))
for cle in tours[profils[0]][0]:
    ligne = f"{cle:34}"
    for profil in profils:
        releves = [t[cle] for t in tours[profil]]
        ligne += f"{statistics.median(r['ms'] for r in releves):14.2f}{releves[0]['triangles']:11d}{releves[0]['appels']:8d}"
    print(ligne)
