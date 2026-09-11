---
name: publier
description: Met la visite 3D en ligne sur davidbonan.io/visite — recopie visite/ dans public/visite du dépôt davidbonan.com, commit des deux côtés, push, puis vérifie la page déployée. À utiliser dès qu'une modification de la visite doit se voir en ligne — « publie la visite », « mets la visite en ligne », « déploie la visite », « pousse ça sur le site », « la visite en prod est-elle à jour », « le site montre encore l'ancienne version ». Pour regénérer temple.glb avant de publier, c'est le skill blender.
---

# Publier la visite sur le site perso

Deux dépôts, deux commits. La visite **vit ici** ; le site n'en héberge qu'une copie.

| Dépôt | Rôle |
|---|---|
| `beth-hamikdash-blender` (celui-ci) | la source : `visite/` |
| `davidbonan.com` (voisin, `../davidbonan.com`) | l'hôte : `public/visite/`, déployé par Netlify sur `davidbonan.io` |

Si le voisin manque : `git clone https://github.com/davidbonan/davidbonan.com ..`

## La séquence

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_visite.py   # si le .blend a bougé
python3 beit_hamikdash_traductions.py                          # doit répondre « traductions à jour »
./publier_visite.sh                                            # recopie dans ../davidbonan.com
git add -u visite && git commit && git push                    # la source
git -C ../davidbonan.com add public/visite
git -C ../davidbonan.com commit && git -C ../davidbonan.com push origin master
```

**Commiter la source d'abord.** `publier_visite.sh` recopie l'arbre de travail, pas
le HEAD : publier sans commiter met en ligne une version qui n'existe dans aucun
dépôt, et plus personne ne sait ce que le site montre.

La branche du site est `master`, pas `main`. Netlify déploie au push, ~3 minutes.

## Ce que le script fait, et pourquoi la balise `<base>`

`publier_visite.sh [chemin-du-site]` rsync `index.html`, les `.js`, les `.json`,
`temple.glb` et `apercu.jpg` vers `public/visite/`, en `--delete` — un fichier
supprimé ici disparaît là-bas. Puis il insère `<base href="/visite/">` dans la copie.

Cette balise est le seul écart entre la source et le déployé, et il est nécessaire :
servie à `/visite` **sans slash final**, la page résoudrait ses `./visite.js` à la
racine du site et resterait bloquée sur « chargement de la scène… ». La source, elle,
n'en veut pas : elle est servie depuis `visite/` (`python3 -m http.server 8777`), où
les chemins relatifs tombent juste. Ne pas porter la balise dans `visite/index.html`.

Netlify redirige `/visite` → `/visite/` ; `next start` en local fait l'inverse. La
balise étant absolue, les deux marchent — et la règle `rewrites()` de
`next.config.js` ne sert qu'au local.

## Vérifier que c'est en ligne

Le 200 ne suffit pas : la page peut se servir et rester noire sur une erreur WebGL ou
un asset manquant. Deux niveaux.

```bash
curl -sIL https://davidbonan.io/visite | grep -i "^HTTP\|^location"
for f in visite.js temple.glb concepts.json reperes.json textes.json; do
  curl -s -o /dev/null -w "$f %{http_code}\n" "https://davidbonan.io/visite/$f"
done
```

Puis la scène elle-même, qui expose ses points d'accroche (`window.__etat`) une fois
chargée :

```bash
visite=$PWD/.claude/skills/publier/verifier.mjs
cd "$TMPDIR" && npm i playwright-core          # une fois par dossier jetable
node "$visite" https://davidbonan.io/visite [capture.png]
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

## Ce qui a déjà mordu

- **Le cache Netlify** ne joue pas ici : les fichiers sont statiques et servis tels
  quels. Une vieille version en ligne veut dire un `publier_visite.sh` non relancé,
  pas un cache à purger.
- **`.contentlayer/` est versionné** dans le dépôt du site : un `npm run build` local
  le régénère et pollue le diff. `git checkout -- .contentlayer` avant de commiter.
- **`temple.glb` fait 2,8 Mo** — pas de LFS dans le dépôt du site, c'est voulu ;
  le garder sous ~10 Mo.
- **Les domaines sont mélangés** dans le dépôt du site : `rss.js` dit `davidbonan.io`,
  `sitemap.xml/route.js` et `robots.txt` disent `davidbonan.com`. Les métadonnées de
  la visite (canonical, `og:url`, `og:image`) suivent `.io`, qui est le domaine servi.
