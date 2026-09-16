---
name: publier
description: Met la visite 3D et le site en ligne sur bethhamikdach.com — vérifie que la source est à jour, commit, push, puis vérifie la page déployée. À utiliser dès qu'une modification de la visite ou du site doit se voir en ligne — « publie la visite », « mets la visite en ligne », « déploie le site », « pousse ça sur le site », « la visite en prod est-elle à jour », « le site montre encore l'ancienne version ». Pour regénérer temple.glb avant de publier, c'est le skill blender.
---

# Publier sur bethhamikdach.com

Un seul dépôt : Netlify déploie `main` à chaque push, en ~3 minutes.

| Chemin | Rôle |
|---|---|
| `site/` | l'accueil (fr, en, he), robots, sitemap, favicon, feuille de style, `accueil.js`. Les trois `index.html` sont **générés** par `python3 site/accueil.py` depuis ses textes : modifier le script, pas les pages |
| `site/images/` | l'affiche (`affiche_*.webp`), l'image de partage (`partage.jpg`) et les huit images des degrés (`<degré>_1000` et `_2000.webp`), voir « L'accueil, une montée en images » |
| `visite/` | la visite, servie à `/visite/` ; `?cinema` la fait marcher seule (plus utilisé par l'accueil) |
| `construire_site.sh` | assemble `dist/` = `site/` + `visite/` filtrée ; c'est la commande de build Netlify |
| `netlify.toml` | dossier publié, redirection `www`, cache des assets |

Le domaine est chez OVH (A `75.2.60.5` sur `@`, CNAME `www` → `bethhamikdach.netlify.app.`) ;
Netlify porte le certificat. `davidbonan.io/visite` redirige en 301 vers ici.

## La séquence

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_visite.py   # si le .blend a bougé — sans --sans-occlusion
python3 beit_hamikdash_traductions.py                          # doit répondre « traductions à jour »
./construire_site.sh && (cd dist && python3 -m http.server 8790)   # relecture locale, facultative
git add -u site visite && git commit && git push origin main
```

**Ne pas commiter `dist/`** : il est ignoré et Netlify le reconstruit. Ce que le site
montre est toujours le HEAD de `main`, jamais l'arbre de travail.

## Ce que `construire_site.sh` filtre, et pourquoi pas de `<base>`

Le script rsync `index.html`, les `.js`, les `.json`, `temple.glb`, `figures.glb`,
`apercu.jpg`, `mini_*.png`, `matieres/*.webp`, `plans/*.webp` et `occlusion/*.webp` vers `dist/visite/`, en
`--delete`. Le reste de `visite/` (scans, profils de navigateur) ne part pas.

Servie à `/visite/` à la racine du domaine, la page résout ses chemins relatifs sans
balise `<base>`. Netlify redirige `/visite` → `/visite/` de lui-même.

## Les empreintes, et pourquoi le déployé n'est pas la source

`empreintes.py`, lancé par `construire_site.sh` sur `dist/`, appose sur chaque URL
d'asset l'empreinte de son contenu : `visite.js?v=03a1168a`, `temple.glb?v=7823c773`.
C'est la seule différence entre l'arbre de travail et ce que Netlify sert, et elle est
la raison pour laquelle une modification se voit sans vider le cache — le contenu
change, l'URL change, et rien de vieux ne peut plus être servi sous ce nom. Les pages
gardent leur URL nue et se revalident à chaque visite (`netlify.toml`) ; tout le reste
est `immutable`.

Deux régimes : les médias portent chacun leur propre empreinte, le code et les données
portent un cachet commun calculé sur tout le site. Les chemins que la visite construit à
l'exécution (`contenu_${f}.${code}.json`) échappent à la réécriture : `json()` dans
`visite.js` relit le cachet dans son `import.meta.url` et l'ajoute lui-même. D'où la
règle — un nouveau média se cite par un littéral entier (`"matieres/pierre_c_1024.webp"`,
pas `` `${nom}_c_1024.webp` ``), sinon `empreintes.py` ne le voit pas.

En local, servir `visite/` directement marche comme avant : sans build il n'y a pas
d'empreinte, `import.meta.url` n'a pas de query, et `json()` ajoute une chaîne vide.

## L'accueil, une montée en images

L'accueil ne montre que des images : l'affiche en seuil (`affiche_*.webp`, c'est l'image
du Har HaBayit), puis les degrés de sainteté (Kelim 1:8-9) un à un, chacun par l'image
stylisée du film prise de ce point (`site/images/<degré>_1000` et `_2000.webp`, sources
dans `renders/style/` : ACC_01 à 05 pour les cinq premières, CAM_08, CAM_09A et CAM_11
pour l'Oulam, le Heikhal et le Kodesh HaKodashim), et le Kodesh HaKodashim en finale
plein écran. L'ordre des degrés et la vue de la visite prise du même point sont `DEGRES`
dans `site/accueil.py` ; chaque image mène à `/visite/?vue=<vue>`. Une échelle fixe sur le
côté suit la lecture (`accueil.js`, un `IntersectionObserver`), et « Entrer » ouvre la
visite à son début.

Le mode `?cinema` de la visite (`visite/cinema.js`, parcours dans `visite/cinema.json`)
fait marcher la scène seule le long des mêmes degrés ; l'accueil ne l'encadre plus, il
reste pour capter des images ou un film depuis la scène.

L'affiche et l'image de partage sont des **captures de cette scène**, à refaire si la
scène change et que l'affiche doit la suivre :

```bash
cd "$TMPDIR" && npm i playwright-core                     # une fois par dossier jetable
(cd <dépôt> && python3 -m http.server 8766 --bind 127.0.0.1 &)   # la scène de l'arbre de travail
cinema=<dépôt>/.claude/skills/publier/cinema.mjs
node "$cinema" "http://127.0.0.1:8766/visite/?cinema" affiches/paysage 2000x1125 1 --affiche 1.5
node "$cinema" "http://127.0.0.1:8766/visite/?cinema" affiches/portrait 720x1280 1 --affiche 1.5
node "$cinema" "http://127.0.0.1:8766/visite/?cinema" affiches/partage 1200x630 1 --affiche 48
```

Puis `cwebp -q 82` vers `affiche_2000.webp` (et `-resize 1000 0` → `affiche_1000.webp`),
`affiche_portrait_720.webp`, `ffmpeg -q:v 4` vers `partage.jpg`.

`--affiche t` marche jusqu'au temps `t` puis capte ; `--film` rend chaque image à 24/s.
Le script rend sous Metal (`--use-angle=metal`, Chromium du cache playwright), fige la
boucle de la page (`window.__cinema.figer()`) et avance lui-même (`__cinema.avancer`) :
sous SwiftShader la scène met des secondes par image, et une boucle laissée libre
dérive le temps du parcours pendant la capture. Le temps 1.5 est la première image
après le fondu d'ouverture ; 48, les quinze marches devant Nikanor.

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

Sur l'accueil, `node "$visite" https://bethhamikdach.com/` ne trouve pas de scène et le
dit ; la capture montre l'affiche. Les huit images se vérifient en 200 sur
`/images/<degré>_2000.webp`.

## Ce qui a déjà mordu

- **Le cache** : seules les pages HTML se revalident ; tout le reste est `immutable` sous
  son empreinte. Une vieille scène après un push veut dire un `temple.glb` non
  regénéré ou non commité, pas un cache à purger — vérifier `git log -1 -- visite/temple.glb`.
- **Le build Netlify clone le dépôt**, .blend compris : c'est lent mais ça passe. Si un
  jour ça ne passe plus, `netlify deploy --prod --dir=dist` depuis la machine.
- **Un profil Chrome dans `visite/`** (Playwright) a déjà fini stagé : `visite/profil/`
  est ignoré, et le filtre du script ne l'emporterait pas de toute façon.
