---
name: publier
description: Met la visite 3D et le site en ligne sur bethhamikdach.com — vérifie que la source est à jour, commit, push, puis vérifie la page déployée. À utiliser dès qu'une modification de la visite ou du site doit se voir en ligne — « publie la visite », « mets la visite en ligne », « déploie le site », « pousse ça sur le site », « la visite en prod est-elle à jour », « le site montre encore l'ancienne version ». Pour regénérer temple.glb avant de publier, c'est le skill blender.
---

# Publier sur bethhamikdach.com

Un seul dépôt : Netlify déploie `main` à chaque push, en ~3 minutes.

| Chemin | Rôle |
|---|---|
| `site/` | l'accueil (fr, en, he), robots, sitemap, feuille de style. Les trois `index.html` sont **générés** par `python3 site/accueil.py` depuis ses textes : modifier le script, pas les pages |
| `visite/` | la visite, servie à `/visite/` |
| `construire_site.sh` | assemble `dist/` = `site/` + `visite/` filtrée ; c'est la commande de build Netlify |
| `netlify.toml` | dossier publié, redirection `www`, cache des assets |

Le domaine est chez OVH (A `75.2.60.5` sur `@`, CNAME `www` → `bethhamikdach.netlify.app.`) ;
Netlify porte le certificat. `davidbonan.io/visite` redirige en 301 vers ici.

## La séquence

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_visite.py   # si le .blend a bougé
python3 beit_hamikdash_traductions.py                          # doit répondre « traductions à jour »
./construire_site.sh && (cd dist && python3 -m http.server 8790)   # relecture locale, facultative
git add -u site visite && git commit && git push origin main
```

**Ne pas commiter `dist/`** : il est ignoré et Netlify le reconstruit. Ce que le site
montre est toujours le HEAD de `main`, jamais l'arbre de travail.

## Ce que `construire_site.sh` filtre, et pourquoi pas de `<base>`

Le script rsync `index.html`, les `.js`, les `.json`, `temple.glb`, `figures.glb`,
`apercu.jpg`, `mini_*.png`, `matieres/*.webp` et `plans/*.webp` vers `dist/visite/`, en
`--delete`. Le reste de `visite/` (scans, profils de navigateur) ne part pas.

Servie à `/visite/` à la racine du domaine, la page résout ses chemins relatifs sans
balise `<base>` : la source et le déployé sont identiques. Netlify redirige `/visite`
→ `/visite/` de lui-même.

## Vérifier que c'est en ligne

Le 200 ne suffit pas : la page peut se servir et rester noire sur une erreur WebGL ou
un asset manquant. Deux niveaux.

```bash
curl -sIL https://bethhamikdach.com/visite | grep -i "^HTTP\|^location"
for f in visite.js temple.glb figures.glb figures.json concepts.json reperes.json textes.json; do
  curl -s -o /dev/null -w "$f %{http_code}\n" "https://bethhamikdach.com/visite/$f"
done
```

Puis la scène elle-même, qui expose ses points d'accroche (`window.__etat`) une fois
chargée :

```bash
visite=$PWD/.claude/skills/publier/verifier.mjs
cd "$TMPDIR" && npm i playwright-core          # une fois par dossier jetable
node "$visite" https://bethhamikdach.com/visite/ [capture.png]
```

`--mobile` passe en 390 × 844 tactile. `--planche <dossier>` capture en plus chaque
entrée et chaque vue de `reperes.json` puis assemble `planche.html` et `planche.jpg` :
c'est la vérification des cadrages après toute retouche de `beit_hamikdash_visite.py`
(`--seulement id,id` pour n'en refaire que quelques-unes).

Il répond `scene prete` et la pose de la caméra (code 0), ou `BLOQUE :` précédé de ce
qui a manqué — 404 d'asset, erreur de module (code 1). Une capture atterrit dans le
dossier courant dans les deux cas. `playwright-core` se résout depuis le dossier
courant, jamais depuis le dépôt ; le Chromium est celui du cache playwright, sinon
`CHROME=<binaire>`.

Le même script sert pour l'accueil : `node "$visite" https://bethhamikdach.com/` ne
trouve pas de scène et le dit, mais la capture montre la page.

## Ce qui a déjà mordu

- **Le cache** : HTML et JSON sont servis en `must-revalidate`, les `.glb` et les textures
  avec un jour de cache. Une vieille scène après un push veut dire un `temple.glb` non
  regénéré ou non commité, pas un cache à purger — vérifier `git log -1 -- visite/temple.glb`.
- **Le build Netlify clone le dépôt**, .blend compris : c'est lent mais ça passe. Si un
  jour ça ne passe plus, `netlify deploy --prod --dir=dist` depuis la machine.
- **Un profil Chrome dans `visite/`** (Playwright) a déjà fini stagé : `visite/profil/`
  est ignoré, et le filtre du script ne l'emporterait pas de toute façon.
